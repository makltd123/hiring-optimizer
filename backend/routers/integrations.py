"""
Настройка и запуск интеграций: Email IMAP, Авито Работа API.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from deps import get_current_user
from models.base import get_db
from models.models import IntegrationConfig, User
from schemas.schemas import EmailIntegrationConfig, AvitoIntegrationConfig
from services.audit import AuditAction, log_action
from services.crypto import encrypt_json, decrypt_json

router = APIRouter(prefix="/integrations", tags=["integrations"])


def _get_config(user: User, type_: str, db: Session) -> IntegrationConfig | None:
    return db.query(IntegrationConfig).filter(
        IntegrationConfig.user_id == user.id,
        IntegrationConfig.type == type_,
    ).first()


@router.get("/status")
def integrations_status(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    email_cfg = _get_config(user, "email", db)
    avito_cfg = _get_config(user, "avito", db)
    return {
        "email": "configured" if email_cfg else "not_configured",
        "avito": "configured" if avito_cfg else "not_configured",
    }


@router.post("/email/configure")
def configure_email(
    body: EmailIntegrationConfig,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Сохранить настройки IMAP и проверить подключение."""
    body_dict = body.model_dump()

    # Тест подключения
    try:
        from services.email_import import EmailResumeImporter
        importer = EmailResumeImporter(
            host=body_dict["host"],
            port=body_dict["port"],
            user=body_dict["user"],
            password=body_dict["password"],
        )
        ok = importer.test_connection()
        importer.close()
        if not ok:
            raise HTTPException(status_code=400, detail="Не удалось подключиться к почтовому серверу")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail="Ошибка подключения к почтовому серверу")

    cfg = _get_config(user, "email", db)
    if cfg:
        cfg.config_json = encrypt_json(body_dict)
    else:
        cfg = IntegrationConfig(user_id=user.id, type="email", config_json=encrypt_json(body_dict))
        db.add(cfg)
    db.commit()
    log_action(user.id, AuditAction.INTEGRATION_CONFIGURED, db,
               entity_type="integration", details={"type": "email", "host": body_dict["host"]})
    return {"ok": True, "status": "connected"}


@router.post("/avito/connect")
def connect_avito(
    body: AvitoIntegrationConfig,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Сохранить Авито OAuth2 credentials и проверить аутентификацию."""
    body_dict = body.model_dump()
    from services.avito_integration import AvitoWorkClient
    client = AvitoWorkClient(body.client_id, body.client_secret)
    if not client.authenticate():
        raise HTTPException(status_code=400, detail="Не удалось аутентифицироваться в Авито API")

    cfg = _get_config(user, "avito", db)
    if cfg:
        cfg.config_json = encrypt_json(body_dict)
    else:
        cfg = IntegrationConfig(user_id=user.id, type="avito", config_json=encrypt_json(body_dict))
        db.add(cfg)
    db.commit()
    log_action(user.id, AuditAction.INTEGRATION_CONFIGURED, db,
               entity_type="integration", details={"type": "avito"})
    return {"ok": True, "status": "connected"}


@router.post("/projects/{project_id}/import/email")
def import_email(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Импортировать резюме из настроенного почтового ящика в проект."""
    from models.models import Project
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Проект не найден")

    cfg = _get_config(user, "email", db)
    if not cfg:
        raise HTTPException(status_code=400, detail="Сначала настройте Email интеграцию")

    from services.email_import import import_from_email
    try:
        count = import_from_email(project_id, decrypt_json(cfg.config_json), db)
    except Exception as e:
        import logging as _log; _log.getLogger(__name__).error("Email import error: %s", e)
        raise HTTPException(status_code=500, detail="Ошибка импорта резюме с почты")

    log_action(user.id, AuditAction.IMPORT_STARTED, db,
               entity_type="project", entity_id=project_id,
               details={"source": "email", "imported": count})
    return {"imported_count": count}


@router.post("/projects/{project_id}/import/avito")
def import_avito(
    project_id: int,
    body: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Импортировать отклики с Авито по ID вакансии."""
    from models.models import Project
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Проект не найден")

    cfg = _get_config(user, "avito", db)
    if not cfg:
        raise HTTPException(status_code=400, detail="Сначала подключите Авито API")

    vacancy_id = body.get("vacancy_id")
    if not vacancy_id:
        raise HTTPException(status_code=400, detail="Обязательное поле: vacancy_id")

    from services.avito_integration import import_from_avito
    try:
        count = import_from_avito(project_id, str(vacancy_id), decrypt_json(cfg.config_json), db)
    except ValueError as e:
        import logging as _log; _log.getLogger(__name__).warning("Avito import error: %s", e)
        raise HTTPException(status_code=400, detail="Ошибка импорта с Авито. Проверьте vacancy_id.")
    except Exception as e:
        import logging as _log; _log.getLogger(__name__).error("Avito import error: %s", e)
        raise HTTPException(status_code=500, detail="Ошибка импорта откликов с Авито")

    log_action(user.id, AuditAction.IMPORT_STARTED, db,
               entity_type="project", entity_id=project_id,
               details={"source": "avito", "vacancy_id": vacancy_id, "imported": count})
    return {"imported_count": count}
