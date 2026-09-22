from datetime import datetime
from enum import Enum

from fastapi import Request
from sqlalchemy.orm import Session

from models.models import AuditLog


class AuditAction(str, Enum):
    PROJECT_CREATED = "project.created"
    PROJECT_DELETED = "project.deleted"
    CANDIDATE_ADDED = "candidate.added"
    OPTIMIZATION_RUN = "optimization.run"
    RESULT_VIEWED = "result.viewed"
    REPORT_EXPORTED = "report.exported"
    USER_LOGIN = "user.login"
    USER_CREATED = "user.created"
    USER_ROLE_CHANGED = "user.role_changed"
    INTEGRATION_CONFIGURED = "integration.configured"
    IMPORT_STARTED = "import.started"
    # v4
    LOGIN_FAILED = "auth.login_failed"
    LOGOUT = "auth.logout"
    MFA_ENABLED = "mfa.enabled"
    MFA_DISABLED = "mfa.disabled"
    MFA_FAILED = "mfa.failed"
    DATA_ERASURE_REQUEST = "data.erasure_request"
    DATA_EXPORT = "data.export"
    CANDIDATE_STATUS_CHANGED = "candidate.status_changed"
    APPROVAL_SUBMITTED = "approval.submitted"
    APPROVAL_DECIDED = "approval.decided"


def log_action(
    user_id: int,
    action: AuditAction,
    db: Session,
    entity_type: str | None = None,
    entity_id: int | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
) -> None:
    entry = AuditLog(
        user_id=user_id,
        action=action.value,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details or {},
        ip_address=ip_address,
        created_at=datetime.utcnow(),
    )
    db.add(entry)
    db.commit()


def get_ip(request: Request) -> str | None:
    if request.client:
        return request.client.host
    return None
