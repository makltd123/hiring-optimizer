import asyncio
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from deps import get_current_user
from models.base import get_db
from models.models import User, Project, OptimizationResult, HiringApproval
from schemas.schemas import ApprovalSubmitRequest, ApprovalDecisionRequest, ApprovalOut
from services.audit import AuditAction, log_action

router = APIRouter(tags=["approvals"])


@router.post("/projects/{project_id}/results/{result_id}/submit-for-approval", response_model=ApprovalOut)
def submit_for_approval(
    project_id: int,
    result_id: int,
    body: ApprovalSubmitRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(
        Project.id == project_id, Project.user_id == user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Проект не найден")

    result = db.query(OptimizationResult).filter(
        OptimizationResult.id == result_id,
        OptimizationResult.project_id == project_id,
    ).first()
    if not result:
        raise HTTPException(status_code=404, detail="Результат не найден")

    approver = db.query(User).filter(
        User.id == body.approver_id,
        User.org_id == user.org_id,
    ).first()
    if not approver:
        raise HTTPException(status_code=404, detail="Согласующий не найден")

    approval = HiringApproval(
        project_id=project_id,
        result_id=result_id,
        requested_by=user.id,
        approver_id=body.approver_id,
        status="pending",
    )
    db.add(approval)
    db.commit()
    db.refresh(approval)

    log_action(user.id, AuditAction.APPROVAL_SUBMITTED, db,
               entity_type="hiring_approval", entity_id=approval.id,
               details={"project_id": project_id, "approver_id": body.approver_id})

    # Асинхронное уведомление
    try:
        from services.notifications import send_approval_notification
        asyncio.create_task(
            send_approval_notification(body.approver_id, project.title, "approval_requested", None, db)
        )
    except Exception:
        pass

    return approval


@router.get("/approvals", response_model=list[ApprovalOut])
def list_approvals(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return db.query(HiringApproval).filter(
        (HiringApproval.approver_id == user.id) | (HiringApproval.requested_by == user.id)
    ).order_by(HiringApproval.created_at.desc()).all()


@router.post("/approvals/{approval_id}/approve", response_model=ApprovalOut)
def approve(
    approval_id: int,
    body: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _decide(approval_id, "approved", body.comment, user, db)


@router.post("/approvals/{approval_id}/reject", response_model=ApprovalOut)
def reject(
    approval_id: int,
    body: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _decide(approval_id, "rejected", body.comment, user, db)


@router.post("/approvals/{approval_id}/revision", response_model=ApprovalOut)
def revision(
    approval_id: int,
    body: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _decide(approval_id, "revision", body.comment, user, db)


def _decide(approval_id: int, status: str, comment: str | None, user: User, db: Session):
    approval = db.query(HiringApproval).filter(
        HiringApproval.id == approval_id,
        HiringApproval.approver_id == user.id,
        HiringApproval.status == "pending",
    ).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Согласование не найдено или уже решено")

    approval.status = status
    approval.comment = comment
    approval.decided_at = datetime.utcnow()
    db.commit()
    db.refresh(approval)

    log_action(user.id, AuditAction.APPROVAL_DECIDED, db,
               entity_type="hiring_approval", entity_id=approval_id,
               details={"status": status})

    project = db.query(Project).filter(Project.id == approval.project_id).first()
    try:
        from services.notifications import send_approval_notification
        import asyncio
        asyncio.create_task(
            send_approval_notification(
                approval.requested_by,
                project.title if project else "—",
                status,
                comment,
                db,
            )
        )
    except Exception:
        pass

    return approval
