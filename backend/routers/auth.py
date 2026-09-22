from datetime import datetime, timedelta

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from config import settings
from deps import get_current_user
from models.base import get_db
from models.models import User

try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    _limiter = Limiter(key_func=get_remote_address)
    _RATE_LIMIT = True
except ImportError:
    _limiter = None
    _RATE_LIMIT = False


def _rate_limit(limit: str):
    """Декоратор-заглушка когда slowapi не установлен."""
    def decorator(func):
        if _RATE_LIMIT and _limiter:
            return _limiter.limit(limit)(func)
        return func
    return decorator
from schemas.schemas import (
    UserCreate, Token, TokenPair, MFALoginResponse, MFAVerifyRequest,
    MFASetupResponse, MFAConfirmRequest, MFADisableRequest, MFABackupRequest,
    RefreshRequest,
)
from services.audit import AuditAction, log_action, get_ip
from services.ldap_auth import authenticate_ldap, get_or_create_user_from_ldap
from services.mfa import mfa_service
from services.token_service import (
    create_token_pair, create_access_token,
    refresh_access_token, revoke_token, revoke_all_tokens,
    get_active_sessions, revoke_session,
)

router = APIRouter()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    if not hashed:
        return False
    return bcrypt.checkpw(password.encode(), hashed.encode())


def _create_temp_token(user_id: int) -> str:
    """Короткоживущий токен для прохождения MFA-шага (90 секунд)."""
    expire = datetime.utcnow() + timedelta(seconds=90)
    return jwt.encode(
        {"sub": str(user_id), "type": "mfa_pending", "exp": expire},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def _decode_temp_token(temp_token: str) -> int:
    try:
        payload = jwt.decode(temp_token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != "mfa_pending":
            raise ValueError
        return int(payload["sub"])
    except (JWTError, ValueError, KeyError):
        raise HTTPException(status_code=401, detail="Недействительный временный токен MFA")


@router.post("/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
@_rate_limit("10/minute")
def register(body: UserCreate, request: Request, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=body.email, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    log_action(user.id, AuditAction.USER_CREATED, db,
               entity_type="user", entity_id=user.id,
               ip_address=get_ip(request))
    return create_token_pair(user, db, request)


@router.post("/login", response_model=MFALoginResponse)
@_rate_limit("5/minute")
def login(body: UserCreate, request: Request, db: Session = Depends(get_db)):
    # LDAP fallback
    if settings.ldap_enabled:
        ldap_data = authenticate_ldap(body.email, body.password)
        if ldap_data:
            user = get_or_create_user_from_ldap(ldap_data, db)
            user.last_login = datetime.utcnow()
            db.commit()
            log_action(user.id, AuditAction.USER_LOGIN, db,
                       entity_type="user", entity_id=user.id,
                       details={"method": "ldap"}, ip_address=get_ip(request))
            pair = create_token_pair(user, db, request)
            return MFALoginResponse(mfa_required=False, **pair)

    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        log_action(None, AuditAction.LOGIN_FAILED, db,
                   details={"email": body.email}, ip_address=get_ip(request))
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user.last_login = datetime.utcnow()
    db.commit()

    # MFA требуется — возвращаем временный токен
    if user.mfa_enabled and user.mfa_secret:
        temp_token = _create_temp_token(user.id)
        log_action(user.id, AuditAction.USER_LOGIN, db,
                   entity_type="user", entity_id=user.id,
                   details={"method": "local", "mfa_pending": True},
                   ip_address=get_ip(request))
        return MFALoginResponse(mfa_required=True, temp_token=temp_token)

    log_action(user.id, AuditAction.USER_LOGIN, db,
               entity_type="user", entity_id=user.id,
               details={"method": "local"}, ip_address=get_ip(request))
    pair = create_token_pair(user, db, request)
    return MFALoginResponse(mfa_required=False, **pair)


# ── MFA endpoints ─────────────────────────────────────────────────────────────

@router.post("/mfa/verify", response_model=TokenPair)
@_rate_limit("5/minute")
def mfa_verify(body: MFAVerifyRequest, request: Request, db: Session = Depends(get_db)):
    user_id = _decode_temp_token(body.temp_token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.mfa_secret:
        raise HTTPException(status_code=401, detail="MFA не настроен")
    if not mfa_service.verify_code(user.mfa_secret, body.code, user.mfa_last_totp_counter):
        log_action(user_id, AuditAction.MFA_FAILED, db, ip_address=get_ip(request))
        raise HTTPException(status_code=401, detail="Неверный код MFA")
    user.mfa_last_totp_counter = mfa_service.current_totp_counter()
    db.commit()
    return create_token_pair(user, db, request)


@router.post("/mfa/backup", response_model=TokenPair)
def mfa_backup(body: MFABackupRequest, request: Request, db: Session = Depends(get_db)):
    """Вход через резервный код (temp_token + backup_code)."""
    # Разбираем composite body: temp_token передаётся в Authorization (Bearer) — здесь используем как query
    raise HTTPException(status_code=501, detail="Используйте /auth/mfa/backup-login")


@router.post("/mfa/backup-login", response_model=TokenPair)
@_rate_limit("3/5minutes")
def mfa_backup_login(
    body: MFABackupRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """temp_token передаётся в теле запроса через MFABackupRequest.temp_token."""
    user_id = _decode_temp_token(body.temp_token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Пользователь не найден")
    codes = user.mfa_backup_codes or []
    ok, remaining = mfa_service.verify_backup_code(body.backup_code, codes)
    if not ok:
        raise HTTPException(status_code=401, detail="Неверный резервный код")
    user.mfa_backup_codes = remaining
    db.commit()
    return create_token_pair(user, db, request)


@router.post("/mfa/setup", response_model=MFASetupResponse)
def mfa_setup(user: User = Depends(get_current_user)):
    if user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA уже включён")
    return mfa_service.generate_secret(user.email)


@router.post("/mfa/confirm")
def mfa_confirm(
    body: MFAConfirmRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    setup = mfa_service.generate_secret(user.email)
    # Секрет должен был быть передан из /mfa/setup; используем тот что сгенерили (stateless)
    # Клиент вызывает /mfa/setup → получает secret → сохраняет → вводит code → вызывает /mfa/confirm с secret+code
    raise HTTPException(
        status_code=400,
        detail="Передайте secret и code вместе через /mfa/confirm-with-secret"
    )


@router.post("/mfa/confirm-with-secret")
def mfa_confirm_with_secret(
    body: MFAConfirmRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """secret и code передаются в JSON body."""
    secret = body.secret
    if not secret:
        raise HTTPException(status_code=400, detail="Поле secret обязательно")
    if not mfa_service.verify_code(secret, body.code):
        raise HTTPException(status_code=400, detail="Неверный код")
    backup_codes = mfa_service.generate_backup_codes()
    user.mfa_secret = secret
    user.mfa_enabled = True
    user.mfa_verified_at = datetime.utcnow()
    user.mfa_backup_codes = backup_codes
    db.commit()
    log_action(user.id, AuditAction.MFA_ENABLED, db,
               entity_type="user", entity_id=user.id,
               ip_address=get_ip(request))
    return {"status": "enabled", "backup_codes": backup_codes}


@router.post("/mfa/disable")
def mfa_disable(
    body: MFADisableRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA не включён")
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Неверный пароль")
    if not mfa_service.verify_code(user.mfa_secret, body.code):
        raise HTTPException(status_code=401, detail="Неверный код MFA")
    user.mfa_enabled = False
    user.mfa_secret = None
    user.mfa_backup_codes = []
    user.mfa_verified_at = None
    db.commit()
    log_action(user.id, AuditAction.MFA_DISABLED, db,
               entity_type="user", entity_id=user.id,
               ip_address=get_ip(request))
    return {"status": "disabled"}


# ── Refresh token endpoints ───────────────────────────────────────────────────

@router.post("/refresh", response_model=TokenPair)
@_rate_limit("20/minute")
def refresh(body: RefreshRequest, request: Request, db: Session = Depends(get_db)):
    return refresh_access_token(body.refresh_token, db, request)


@router.post("/logout")
def logout(
    body: RefreshRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    revoke_token(body.refresh_token, db)
    log_action(user.id, AuditAction.LOGOUT, db,
               entity_type="user", entity_id=user.id,
               ip_address=get_ip(request))
    return {"status": "logged_out"}


@router.post("/logout-all")
def logout_all(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    revoke_all_tokens(user.id, db)
    log_action(user.id, AuditAction.LOGOUT, db,
               entity_type="user", entity_id=user.id,
               details={"all_devices": True},
               ip_address=get_ip(request))
    return {"status": "all_sessions_revoked"}


@router.get("/sessions")
def sessions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_active_sessions(user.id, db)


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not revoke_session(session_id, user.id, db):
        raise HTTPException(status_code=404, detail="Сессия не найдена")
    return {"status": "revoked"}


# ── SAML / OIDC endpoints ─────────────────────────────────────────────────────

@router.get("/saml/login/{org_id}")
def saml_login(org_id: int, db: Session = Depends(get_db)):
    from models.models import Organization
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org or not org.saml_enabled:
        raise HTTPException(status_code=404, detail="SAML не настроен для этой организации")
    try:
        from services.saml_auth import SAMLService
        svc = SAMLService({
            "org_id": org.id,
            "saml_entity_id": org.saml_entity_id,
            "saml_sso_url": org.saml_sso_url,
            "saml_certificate": org.saml_certificate,
        })
        return {"login_url": svc.get_login_url()}
    except ImportError:
        raise HTTPException(status_code=503, detail="python3-saml не установлен")


@router.post("/saml/callback")
def saml_callback(request: Request, db: Session = Depends(get_db)):
    raise HTTPException(status_code=501, detail="SAML callback требует настройки IdP")


@router.get("/saml/metadata/{org_id}")
def saml_metadata(org_id: int, db: Session = Depends(get_db)):
    from models.models import Organization
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org or not org.saml_enabled:
        raise HTTPException(status_code=404, detail="SAML не настроен")
    return {
        "sp_entity_id": f"https://app.hiringoptimizer.ru/saml/{org_id}",
        "acs_url": "https://app.hiringoptimizer.ru/auth/saml/callback",
    }
