from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.base import get_db
from models.models import User, Project, Vacancy, Candidate, OptimizationResult
from schemas.schemas import SimulateRequest, SimulateResponse, SimulateDiff
from deps import get_current_user
from services.matcher import build_match_matrix
from services.optimizer import hungarian_assignment

router = APIRouter()


def _get_project(project_id: int, user: User, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _compute_coverage(assignment: dict, n_vacancies: int) -> float:
    if n_vacancies == 0:
        return 0.0
    covered = sum(1 for v in assignment.values() if v is not None)
    return covered / n_vacancies


@router.post("/projects/{project_id}/simulate", response_model=SimulateResponse)
def simulate(
    project_id: int,
    body: SimulateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _get_project(project_id, user, db)

    all_candidates = db.query(Candidate).filter(
        Candidate.project_id == project_id,
        Candidate.parse_status == "ready",
    ).all()
    all_vacancies = db.query(Vacancy).filter(Vacancy.project_id == project_id).all()

    candidates = [c for c in all_candidates if c.id not in body.excluded_candidate_ids]
    vacancies = [v for v in all_vacancies if v.id not in body.excluded_vacancy_ids]

    if not candidates or not vacancies:
        raise HTTPException(status_code=400, detail="Недостаточно данных после фильтрации")

    matrix = build_match_matrix(candidates, vacancies)
    row_ind, col_ind = hungarian_assignment(matrix)

    assignment_by_id: dict = {}
    for k in range(len(row_ind)):
        vac_id = str(vacancies[col_ind[k]].id)
        assignment_by_id[vac_id] = candidates[row_ind[k]].id

    for v in vacancies:
        if str(v.id) not in assignment_by_id:
            assignment_by_id[str(v.id)] = None

    total_cost = sum(
        candidates[row_ind[k]].salary_expectation or 0
        for k in range(len(row_ind))
    )
    coverage = _compute_coverage(assignment_by_id, len(vacancies))

    match_scores = {
        str(vacancies[j].id): {
            str(candidates[i].id): round(float(matrix[i][j]), 3)
            for i in range(len(candidates))
        }
        for j in range(len(vacancies))
    }

    # Diff vs last saved result
    last_result = (
        db.query(OptimizationResult)
        .filter(OptimizationResult.project_id == project_id)
        .order_by(OptimizationResult.created_at.desc())
        .first()
    )
    if last_result:
        base_coverage = _compute_coverage(last_result.assignment, len(all_vacancies))
        base_cost = last_result.total_cost or 0.0
    else:
        base_coverage = coverage
        base_cost = total_cost

    diff = SimulateDiff(
        coverage_delta=round(coverage - base_coverage, 3),
        cost_delta=round(total_cost - base_cost),
    )

    return SimulateResponse(
        assignment=assignment_by_id,
        total_cost=total_cost,
        coverage=coverage,
        match_scores=match_scores,
        diff=diff,
    )
