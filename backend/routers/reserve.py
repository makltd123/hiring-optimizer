from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.base import get_db
from models.models import User, Project, Vacancy, Candidate, OptimizationResult
from schemas.schemas import ReserveResponse
from deps import get_current_user
from services.matcher import build_match_matrix
from services.reserve import compute_reserve_list

router = APIRouter()


def _get_project(project_id: int, user: User, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/projects/{project_id}/reserve", response_model=ReserveResponse)
def get_reserve(
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

    candidates = db.query(Candidate).filter(
        Candidate.project_id == project_id,
        Candidate.parse_status == "ready",
    ).all()
    vacancies = db.query(Vacancy).filter(Vacancy.project_id == project_id).all()

    if not candidates or not vacancies:
        return ReserveResponse(reserve=[])

    matrix = build_match_matrix(candidates, vacancies)

    # Convert {str(vac_id): cand_id} -> {vac_idx: cand_idx}
    vac_id_to_idx = {v.id: idx for idx, v in enumerate(vacancies)}
    cand_id_to_idx = {c.id: idx for idx, c in enumerate(candidates)}

    assignment_by_idx: dict = {}
    for vac_id_str, cand_id in result.assignment.items():
        vac_idx = vac_id_to_idx.get(int(vac_id_str))
        cand_idx = cand_id_to_idx.get(cand_id) if cand_id is not None else None
        if vac_idx is not None:
            assignment_by_idx[vac_idx] = cand_idx

    return compute_reserve_list(candidates, vacancies, matrix, assignment_by_idx)
