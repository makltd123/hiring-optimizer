"""
Административные endpoints: аудит-лог, экспорт.
Только для ролей admin и org_admin.
"""
import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from middleware.rbac import require_permission
from models.base import get_db
from models.models import AuditLog, User

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/audit-log")
def get_audit_log(
    user_id: int | None = Query(None),
    action: str | None = Query(None),
    from_dt: datetime | None = Query(None, alias="from"),
    to_dt: datetime | None = Query(None, alias="to"),
    limit: int = Query(100, le=1000),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("audit:read")),
):
    q = db.query(AuditLog)

    # org_admin видит только свою организацию
    if current_user.role == "org_admin" and current_user.org_id:
        org_user_ids = [
            u.id for u in db.query(User).filter(User.org_id == current_user.org_id).all()
        ]
        q = q.filter(AuditLog.user_id.in_(org_user_ids))

    if user_id is not None:
        q = q.filter(AuditLog.user_id == user_id)
    if action:
        q = q.filter(AuditLog.action == action)
    if from_dt:
        q = q.filter(AuditLog.created_at >= from_dt)
    if to_dt:
        q = q.filter(AuditLog.created_at <= to_dt)

    total = q.count()
    logs = q.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "items": [
            {
                "id": log.id,
                "user_id": log.user_id,
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "details": log.details,
                "ip_address": log.ip_address,
                "created_at": log.created_at,
            }
            for log in logs
        ],
    }


@router.get("/audit-log/export")
def export_audit_log(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("audit:read")),
):
    """Скачать весь аудит-лог в CSV."""
    q = db.query(AuditLog)
    if current_user.role == "org_admin" and current_user.org_id:
        org_user_ids = [
            u.id for u in db.query(User).filter(User.org_id == current_user.org_id).all()
        ]
        q = q.filter(AuditLog.user_id.in_(org_user_ids))

    logs = q.order_by(AuditLog.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "user_id", "action", "entity_type", "entity_id", "ip_address", "created_at", "details"])
    for log in logs:
        writer.writerow([
            log.id, log.user_id, log.action, log.entity_type, log.entity_id,
            log.ip_address, log.created_at.isoformat() if log.created_at else "",
            str(log.details),
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit-log.csv"},
    )
