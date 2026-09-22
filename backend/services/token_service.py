import hashlib
import secrets
from datetime import datetime, timedelta

from fastapi import Request
from jose import jwt
from sqlalchemy.orm import Session

from config import settings
from models.models import RefreshToken, User


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _get_ua(request: Request | None) -> str | None:
    if request:
        return request.headers.get("user-agent")
    return None


def _get_ip(request: Request | None) -> str | None:
    if request and request.client:
        return request.client.host
    return None


def create_access_token(user: User) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_access_expire_minutes)
    payload = {
        "sub": str(user.id),
        "org_id": user.org_id,
        "role": user.role,
        "type": "access",
        "ver": user.token_version,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(user: User, db: Session, request: Request | None = None) -> str:
    token = secrets.token_urlsafe(64)
    expire = datetime.utcnow() + timedelta(days=settings.jwt_refresh_expire_days)
    rt = RefreshToken(
        user_id=user.id,
        token_hash=_hash_token(token),
        expires_at=expire,
        user_agent=_get_ua(request),
        ip_address=_get_ip(request),
    )
    db.add(rt)
    db.commit()
    return token


def create_token_pair(user: User, db: Session, request: Request | None = None) -> dict:
    return {
        "access_token": create_access_token(user),
        "refresh_token": create_refresh_token(user, db, request),
        "token_type": "bearer",
        "expires_in": settings.jwt_access_expire_minutes * 60,
    }


def refresh_access_token(refresh_token: str, db: Session, request: Request | None = None) -> dict:
    from fastapi import HTTPException, status
    from sqlalchemy import update as sa_update

    token_hash = _hash_token(refresh_token)
    now = datetime.utcnow()

    # Атомарный UPDATE: помечаем revoked=True только если ещё не revoked и не истёк
    result = db.execute(
        sa_update(RefreshToken)
        .where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked == False,
            RefreshToken.expires_at > now,
        )
        .values(revoked=True, revoked_at=now)
        .returning(RefreshToken.user_id)
    )
    db.commit()
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token недействителен")

    user = db.query(User).filter(User.id == row[0]).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Пользователь не найден")
    return create_token_pair(user, db, request)


def revoke_token(refresh_token: str, db: Session) -> bool:
    token_hash = _hash_token(refresh_token)
    stored = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash,
        RefreshToken.revoked == False,
    ).first()
    if not stored:
        return False
    stored.revoked = True
    stored.revoked_at = datetime.utcnow()
    db.commit()
    return True


def revoke_all_tokens(user_id: int, db: Session):
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked == False,
    ).update({"revoked": True, "revoked_at": datetime.utcnow()})
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.token_version = (user.token_version or 0) + 1
    db.commit()


def get_active_sessions(user_id: int, db: Session) -> list[dict]:
    tokens = db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked == False,
        RefreshToken.expires_at > datetime.utcnow(),
    ).order_by(RefreshToken.created_at.desc()).all()
    return [
        {
            "id": t.id,
            "created_at": t.created_at.isoformat(),
            "expires_at": t.expires_at.isoformat(),
            "ip_address": t.ip_address,
            "user_agent": t.user_agent,
        }
        for t in tokens
    ]


def revoke_session(session_id: int, user_id: int, db: Session) -> bool:
    stored = db.query(RefreshToken).filter(
        RefreshToken.id == session_id,
        RefreshToken.user_id == user_id,
        RefreshToken.revoked == False,
    ).first()
    if not stored:
        return False
    stored.revoked = True
    stored.revoked_at = datetime.utcnow()
    db.commit()
    return True
