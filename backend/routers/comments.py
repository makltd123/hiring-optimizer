from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from deps import get_current_user
from models.base import get_db
from models.models import User, Candidate, Project, CandidateComment
from schemas.schemas import CommentCreate, CommentUpdate, CommentOut

router = APIRouter(tags=["comments"])


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


@router.get("/candidates/{candidate_id}/comments", response_model=list[CommentOut])
def list_comments(
    candidate_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _get_candidate(candidate_id, user, db)
    query = db.query(CandidateComment).filter(
        CandidateComment.candidate_id == candidate_id,
        CandidateComment.deleted_at.is_(None),
    )
    # Приватные комментарии видит только автор
    query = query.filter(
        (CandidateComment.is_private == False) | (CandidateComment.user_id == user.id)
    )
    return query.order_by(CandidateComment.created_at).all()


@router.post("/candidates/{candidate_id}/comments", response_model=CommentOut, status_code=201)
def create_comment(
    candidate_id: int,
    body: CommentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _get_candidate(candidate_id, user, db)
    comment = CandidateComment(
        candidate_id=candidate_id,
        user_id=user.id,
        text=body.text,
        is_private=body.is_private,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


@router.put("/candidates/{candidate_id}/comments/{comment_id}", response_model=CommentOut)
def update_comment(
    candidate_id: int,
    comment_id: int,
    body: CommentUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    comment = db.query(CandidateComment).filter(
        CandidateComment.id == comment_id,
        CandidateComment.candidate_id == candidate_id,
        CandidateComment.user_id == user.id,
        CandidateComment.deleted_at.is_(None),
    ).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Комментарий не найден")
    comment.text = body.text
    comment.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(comment)
    return comment


@router.delete("/candidates/{candidate_id}/comments/{comment_id}")
def delete_comment(
    candidate_id: int,
    comment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    comment = db.query(CandidateComment).filter(
        CandidateComment.id == comment_id,
        CandidateComment.candidate_id == candidate_id,
        CandidateComment.user_id == user.id,
        CandidateComment.deleted_at.is_(None),
    ).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Комментарий не найден")
    comment.deleted_at = datetime.utcnow()
    db.commit()
    return {"status": "deleted"}
