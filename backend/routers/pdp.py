from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from deps import get_current_user
from middleware.rbac import require_permission
from models.base import get_db
from models.models import User, Candidate, Project, BreachNotification
from schemas.schemas import ConsentRequest
from services.audit import AuditAction, log_action, get_ip
from services.pdp_compliance import pdp_service

router = APIRouter(tags=["pdp"])


def _get_candidate(candidate_id: int, user: User, db: Session) -> Candidate:
    c = (
        db.query(Candidate)
        .join(Project, Project.id == Candidate.project_id)
        .filter(
            Candidate.id == candidate_id,
            Project.user_id == user.id,
        )
        .first()
    )
    if not c:
        raise HTTPException(status_code=404, detail="Кандидат не найден")
    return c


@router.post("/candidates/{candidate_id}/consent")
def record_consent(
    candidate_id: int,
    body: ConsentRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _get_candidate(candidate_id, user, db)
    ua = request.headers.get("user-agent")
    ip = body.ip_address or get_ip(request)
    consent = pdp_service.record_consent(candidate_id, body.consent_type, ip, ua, db)
    return {"status": "recorded", "consent_id": consent.id}


@router.delete("/candidates/{candidate_id}/data")
def erase_candidate_data(
    candidate_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _get_candidate(candidate_id, user, db)
    result = pdp_service.process_erasure_request(candidate_id, user.id, db)
    return result


@router.get("/candidates/{candidate_id}/data-export")
def export_candidate_data(
    candidate_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _get_candidate(candidate_id, user, db)
    log_action(user.id, AuditAction.DATA_EXPORT, db,
               entity_type="candidate", entity_id=candidate_id,
               ip_address=get_ip(request))
    return pdp_service.get_data_export(candidate_id, db)


@router.get("/admin/pdp/report")
def pdp_report(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("audit:read")),
):
    from models.models import ErasureRequest, ConsentRecord
    from datetime import datetime
    erasures = db.query(ErasureRequest).count()
    consents = db.query(ConsentRecord).count()
    breaches = db.query(BreachNotification).filter(BreachNotification.status == "open").count()
    return {
        "total_erasure_requests": erasures,
        "total_consents_recorded": consents,
        "open_breach_notifications": breaches,
        "report_generated_at": datetime.utcnow().isoformat(),
    }


@router.post("/admin/pdp/breach-notification")
def create_breach_notification(
    detected_at: str,
    affected_records: int,
    description: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("audit:read")),
):
    from datetime import datetime as dt
    breach = BreachNotification(
        detected_at=dt.fromisoformat(detected_at),
        affected_records=affected_records,
        description=description,
        status="open",
        created_by=user.id,
    )
    db.add(breach)
    db.commit()
    db.refresh(breach)
    return {"id": breach.id, "status": "created"}
