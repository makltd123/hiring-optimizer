"""
Управление организацией, департаментами и пользователями.
Только для ролей admin и org_admin.
"""
import os
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from deps import get_current_user
from middleware.rbac import require_permission
from models.base import get_db
from models.models import Department, Organization, User, WebhookLog
from schemas.schemas import BrandingUpdate, WebhookSettings, NotificationSettings, SAMLConfig
from services.audit import AuditAction, log_action

router = APIRouter(prefix="/org", tags=["organization"])


def _get_org(user: User, db: Session) -> Organization:
    if not user.org_id:
        raise HTTPException(status_code=404, detail="Организация не настроена")
    org = db.query(Organization).filter(Organization.id == user.org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Организация не найдена")
    return org


@router.get("/profile")
def get_org_profile(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    org = _get_org(user, db)
    return {
        "id": org.id,
        "name": org.name,
        "domain": org.domain,
        "created_at": org.created_at,
        "settings": org.settings_json,
    }


@router.put("/profile")
def update_org_profile(
    body: dict,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("users:manage")),
):
    org = _get_org(user, db)
    if "name" in body:
        org.name = body["name"]
    if "domain" in body:
        org.domain = body["domain"]
    if "settings" in body:
        org.settings_json = body["settings"]
    db.commit()
    return {"ok": True}


@router.get("/departments")
def list_departments(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not user.org_id:
        return []
    depts = db.query(Department).filter(Department.org_id == user.org_id).all()
    return [{"id": d.id, "name": d.name, "parent_id": d.parent_id} for d in depts]


@router.post("/departments", status_code=201)
def create_department(
    body: dict,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("users:manage")),
):
    if not user.org_id:
        raise HTTPException(status_code=400, detail="Сначала создайте организацию")
    dept = Department(
        org_id=user.org_id,
        name=body["name"],
        parent_id=body.get("parent_id"),
    )
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return {"id": dept.id, "name": dept.name}


@router.get("/users")
def list_users(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("users:manage")),
):
    if not user.org_id:
        return []
    users = db.query(User).filter(User.org_id == user.org_id).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "role": u.role,
            "dept_id": u.dept_id,
            "last_login": u.last_login,
            "created_at": u.created_at,
        }
        for u in users
    ]


@router.post("/users", status_code=201)
def create_user(
    body: dict,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("users:manage")),
):
    import secrets as _secrets
    from routers.auth import hash_password

    if db.query(User).filter(User.email == body["email"]).first():
        raise HTTPException(status_code=400, detail="Email уже зарегистрирован")

    # Генерируем случайный временный пароль; клиент должен сменить его
    temp_password = body.get("password") or _secrets.token_urlsafe(12)

    new_user = User(
        email=body["email"],
        password_hash=hash_password(temp_password),
        plan="start",
        role=body.get("role", "hr_manager"),
        org_id=user.org_id,
        dept_id=body.get("dept_id"),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    log_action(user.id, AuditAction.USER_CREATED, db,
               entity_type="user", entity_id=new_user.id,
               details={"created_by": user.id, "email": new_user.email})
    # Возвращаем temp_password только если он был сгенерирован (не передан клиентом)
    resp = {"id": new_user.id, "email": new_user.email, "role": new_user.role}
    if not body.get("password"):
        resp["temp_password"] = temp_password
    return resp


@router.put("/users/{user_id}/role")
def change_user_role(
    user_id: int,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users:manage")),
):
    target = db.query(User).filter(User.id == user_id, User.org_id == current_user.org_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    old_role = target.role
    target.role = body["role"]
    db.commit()
    log_action(current_user.id, AuditAction.USER_ROLE_CHANGED, db,
               entity_type="user", entity_id=user_id,
               details={"old_role": old_role, "new_role": body["role"]})
    return {"ok": True, "role": target.role}


@router.delete("/users/{user_id}", status_code=204)
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users:manage")),
):
    target = db.query(User).filter(User.id == user_id, User.org_id == current_user.org_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    if target.id == current_user.id:
        raise HTTPException(status_code=400, detail="Нельзя деактивировать себя")
    # Деактивируем через смену роли, не удаляем (сохраняем данные)
    target.role = "viewer"
    db.commit()


# ── Брендинг ──────────────────────────────────────────────────────────────────

@router.put("/branding")
def update_branding(
    body: BrandingUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("users:manage")),
):
    org = _get_org(user, db)
    if body.brand_color is not None:
        org.brand_color = body.brand_color
    if body.report_footer is not None:
        org.report_footer = body.report_footer
    db.commit()
    return {"ok": True}


_ALLOWED_LOGO_MIME = {"image/png", "image/jpeg", "image/webp", "image/gif"}
_LOGO_MAGIC = {
    b"\x89PNG": "image/png",
    b"\xff\xd8\xff": "image/jpeg",
    b"RIFF": "image/webp",
    b"GIF8": "image/gif",
}


def _check_logo_magic(data: bytes) -> bool:
    for magic in _LOGO_MAGIC:
        if data[:len(magic)] == magic:
            return True
    return False


@router.post("/branding/logo")
def upload_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("users:manage")),
):
    content_type = (file.content_type or "").lower()
    if content_type not in _ALLOWED_LOGO_MIME:
        raise HTTPException(status_code=400, detail="Разрешены только изображения PNG, JPEG, WebP, GIF")

    file_bytes = file.file.read()
    if len(file_bytes) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Размер логотипа не должен превышать 2 МБ")
    if not _check_logo_magic(file_bytes):
        raise HTTPException(status_code=400, detail="Файл не является изображением")

    org = _get_org(user, db)
    uploads_dir = Path("uploads/logos")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    dest = uploads_dir / f"{org.id}.png"
    dest.write_bytes(file_bytes)
    org.logo_url = f"/uploads/logos/{org.id}.png"
    db.commit()
    return {"ok": True, "logo_url": org.logo_url}


@router.get("/branding")
def get_branding(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    org = _get_org(user, db)
    return {
        "brand_color": org.brand_color,
        "report_footer": org.report_footer,
        "logo_url": org.logo_url,
    }


# ── Вебхуки ───────────────────────────────────────────────────────────────────

_SSRF_BLOCKED = (
    "10.", "172.16.", "172.17.", "172.18.", "172.19.", "172.20.",
    "172.21.", "172.22.", "172.23.", "172.24.", "172.25.", "172.26.",
    "172.27.", "172.28.", "172.29.", "172.30.", "172.31.",
    "192.168.", "127.", "0.", "169.254.", "::1", "fc", "fd",
)


def _validate_webhook_url(url: str) -> None:
    import socket
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="webhook_url должен использовать http или https")
    hostname = parsed.hostname or ""
    try:
        ip = socket.gethostbyname(hostname)
    except socket.gaierror:
        raise HTTPException(status_code=400, detail="Не удалось разрешить hostname webhook_url")
    for prefix in _SSRF_BLOCKED:
        if ip.startswith(prefix):
            raise HTTPException(status_code=400, detail="webhook_url указывает на приватную сеть")


@router.put("/webhooks")
def configure_webhook(
    body: WebhookSettings,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("users:manage")),
):
    org = _get_org(user, db)
    if body.webhook_url is not None:
        _validate_webhook_url(body.webhook_url)
        org.webhook_url = body.webhook_url
    if body.webhook_secret is not None:
        org.webhook_secret = body.webhook_secret
    db.commit()
    return {"ok": True}


@router.get("/webhooks/logs")
def webhook_logs(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("users:manage")),
):
    org = _get_org(user, db)
    logs = db.query(WebhookLog).filter(
        WebhookLog.org_id == org.id
    ).order_by(WebhookLog.sent_at.desc()).limit(100).all()
    return [
        {
            "id": l.id,
            "event": l.event,
            "status_code": l.status_code,
            "sent_at": l.sent_at,
            "retry_count": l.retry_count,
        }
        for l in logs
    ]


@router.post("/webhooks/test")
async def test_webhook(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("users:manage")),
):
    org = _get_org(user, db)
    if not org.webhook_url:
        raise HTTPException(status_code=400, detail="Webhook URL не настроен")
    from services.notifications import _send_webhook
    await _send_webhook(
        url=org.webhook_url,
        payload={"event": "test", "message": "HiringOptimizer webhook test"},
        secret=org.webhook_secret,
        db=db,
        org_id=org.id,
    )
    return {"ok": True}


# ── SAML настройки ────────────────────────────────────────────────────────────

@router.put("/saml")
def configure_saml(
    body: SAMLConfig,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("users:manage")),
):
    org = _get_org(user, db)
    org.saml_enabled = True
    org.saml_entity_id = body.saml_entity_id
    org.saml_sso_url = body.saml_sso_url
    org.saml_certificate = body.saml_certificate
    db.commit()
    return {"ok": True, "saml_enabled": True}


# ── Настройки уведомлений пользователя ───────────────────────────────────────

@router.put("/me/notifications")
def update_notifications(
    body: NotificationSettings,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    user.notify_email = body.notify_email
    if body.telegram_chat_id is not None:
        user.telegram_chat_id = body.telegram_chat_id
    db.commit()
    return {"ok": True}
