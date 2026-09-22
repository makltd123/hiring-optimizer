from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.base import get_db
from models.models import User, Project, Vacancy, Candidate, OptimizationResult
from schemas.schemas import BudgetAnalysisResponse
from deps import get_current_user
from services.matcher import build_match_matrix
from services.budget_analysis import analyze_budget_scenarios

router = APIRouter()


def _get_project(project_id: int, user: User, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/projects/{project_id}/budget-analysis", response_model=BudgetAnalysisResponse)
def get_budget_analysis(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = _get_project(project_id, user, db)

    candidates = db.query(Candidate).filter(
        Candidate.project_id == project_id,
        Candidate.parse_status == "ready",
    ).all()
    vacancies = db.query(Vacancy).filter(Vacancy.project_id == project_id).all()

    if not candidates or not vacancies:
        raise HTTPException(status_code=400, detail="Нет кандидатов или вакансий")

    matrix = build_match_matrix(candidates, vacancies)
    scenarios = analyze_budget_scenarios(candidates, vacancies, matrix)

    if not scenarios:
        raise HTTPException(status_code=400, detail="Невозможно построить анализ бюджета")

    last_result = (
        db.query(OptimizationResult)
        .filter(OptimizationResult.project_id == project_id)
        .order_by(OptimizationResult.created_at.desc())
        .first()
    )
    current_fot = last_result.total_cost if last_result else project.fot_limit

    full_coverage_fot = None
    n_vacancies = len(vacancies)
    for s in scenarios:
        if s["assigned_count"] >= n_vacancies:
            full_coverage_fot = s["fot_limit"]
            break

    delta_to_full = (
        round(full_coverage_fot - current_fot)
        if full_coverage_fot is not None and current_fot is not None
        else None
    )

    return BudgetAnalysisResponse(
        scenarios=scenarios,
        current_fot=current_fot,
        full_coverage_fot=full_coverage_fot,
        delta_to_full=delta_to_full,
    )
