from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.base import get_db
from models.models import User, Project, Vacancy, Candidate, OptimizationResult
from schemas.schemas import SkillGapResponse
from deps import get_current_user
from services.skill_gap import compute_skill_gap

router = APIRouter()


def _get_project(project_id: int, user: User, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/projects/{project_id}/skill-gap", response_model=SkillGapResponse)
def get_skill_gap(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _get_project(project_id, user, db)

    result = (
        db.query(OptimizationResult)
        .filter(OptimizationResult.project_id == project_id)
        .order_by(OptimizationResult.created_at.desc())
        .first()
    )
    if not result:
        raise HTTPException(status_code=404, detail="Сначала запустите оптимизацию")

    candidates = db.query(Candidate).filter(Candidate.project_id == project_id).all()
    vacancies = db.query(Vacancy).filter(Vacancy.project_id == project_id).all()

    return compute_skill_gap(candidates, vacancies, result.assignment)
