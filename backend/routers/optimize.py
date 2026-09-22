import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
from models.base import get_db
from models.models import User, Project, Vacancy, Candidate, OptimizationResult
from schemas.schemas import OptimizationResultOut, OptimizeRequest, OptimizationWeights
from deps import get_current_user
from services.matcher import build_match_matrix
from services.optimizer import run_optimization
from services.skill_gap import compute_skill_gap
from services.reserve import compute_reserve_list
from services.pdf_export import generate_report_pdf

try:
    from celery.result import AsyncResult
    from services.task_queue import celery_app, optimize_large_project
    _CELERY_AVAILABLE = True
except Exception:
    _CELERY_AVAILABLE = False

router = APIRouter()


def _get_project(project_id: int, user: User, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/projects/{project_id}/optimize", response_model=OptimizationResultOut, status_code=201)
def optimize(
    project_id: int,
    body: OptimizeRequest = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = _get_project(project_id, user, db)
    vacancies = db.query(Vacancy).filter(Vacancy.project_id == project_id).all()
    candidates = db.query(Candidate).filter(
        Candidate.project_id == project_id,
        Candidate.parse_status == "ready",
    ).all()

    if not vacancies:
        raise HTTPException(status_code=400, detail="Нет вакансий в проекте")
    if not candidates:
        raise HTTPException(status_code=400, detail="Нет готовых кандидатов (дождитесь завершения парсинга)")

    weights = None
    if body and body.weights:
        weights = body.weights
        project.optimization_weights = {
            "skill_match": weights.skill_match,
            "salary_fit": weights.salary_fit,
            "experience": weights.experience,
        }
        db.commit()
    elif project.optimization_weights:
        try:
            w = project.optimization_weights
            weights = OptimizationWeights(
                skill_match=w.get("skill_match", 0.6),
                salary_fit=w.get("salary_fit", 0.3),
                experience=w.get("experience", 0.1),
            )
        except Exception:
            weights = None

    matrix = build_match_matrix(candidates, vacancies, weights=weights)

    try:
        result_data = run_optimization(matrix, candidates, vacancies, project.fot_limit)
    except ValueError as e:
        logger.warning("Optimization failed for project %s: %s", project_id, e)
        raise HTTPException(status_code=400, detail="Ошибка оптимизации. Проверьте данные проекта.")

    n_vacancies = len(vacancies)
    covered = sum(1 for v in result_data["assignment"].values() if v is not None)
    coverage = covered / n_vacancies if n_vacancies > 0 else 0.0

    result = OptimizationResult(
        project_id=project_id,
        assignment=result_data["assignment"],
        total_cost=result_data["total_cost"],
        match_scores=result_data["match_scores"],
        explanation=result_data["explanation"],
        coverage=round(coverage, 3),
        weights_used=project.optimization_weights,
    )
    db.add(result)
    db.commit()
    db.refresh(result)

    # Асинхронные уведомления (fire-and-forget)
    try:
        import asyncio
        from services.notifications import send_optimization_complete
        asyncio.create_task(send_optimization_complete(project, result, db))
    except Exception:
        pass

    out = OptimizationResultOut.model_validate(result)
    out.reserve = result_data["reserve"]
    out.uncovered_vacancies = result_data["uncovered_vacancies"]
    return out


@router.get("/projects/{project_id}/results", response_model=OptimizationResultOut)
def get_results(
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
        raise HTTPException(status_code=404, detail="Результатов пока нет")
    return result


@router.get("/projects/{project_id}/export/pdf")
def export_pdf(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = _get_project(project_id, user, db)

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
    project.candidates = candidates
    project.vacancies = vacancies

    skill_gap_data = compute_skill_gap(candidates, vacancies, result.assignment)

    reserve_data: dict = {"reserve": []}
    ready_candidates = [c for c in candidates if c.parse_status == "ready"]
    if ready_candidates and vacancies:
        from services.matcher import build_match_matrix as _bmm
        matrix = _bmm(ready_candidates, vacancies)
        vac_id_to_idx = {v.id: idx for idx, v in enumerate(vacancies)}
        cand_id_to_idx = {c.id: idx for idx, c in enumerate(ready_candidates)}
        assignment_by_idx: dict = {}
        for vac_id_str, cand_id in result.assignment.items():
            vac_idx = vac_id_to_idx.get(int(vac_id_str))
            cand_idx = cand_id_to_idx.get(cand_id) if cand_id is not None else None
            if vac_idx is not None:
                assignment_by_idx[vac_idx] = cand_idx
        reserve_data = compute_reserve_list(ready_candidates, vacancies, matrix, assignment_by_idx)

    # Собираем org_info для корпоративной шапки + брендинг
    org_info = {"prepared_by": user.email}
    branding = {}
    if user.org_id:
        from models.models import Organization, Department
        org = db.query(Organization).filter(Organization.id == user.org_id).first()
        if org:
            org_info["org_name"] = org.name
            branding = {
                "logo_url": org.logo_url,
                "brand_color": org.brand_color,
                "report_footer": org.report_footer,
            }
        if user.dept_id:
            dept = db.query(Department).filter(Department.id == user.dept_id).first()
            if dept:
                org_info["dept_name"] = dept.name

    pdf_bytes = generate_report_pdf(
        project, result, skill_gap_data, reserve_data,
        org_info=org_info, branding=branding
    )

    filename = f"hiring-report-{project_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/projects/{project_id}/optimize/async")
def optimize_async(
    project_id: int,
    body: OptimizeRequest = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Запустить оптимизацию асинхронно через Celery (для больших проектов)."""
    if not _CELERY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Celery недоступен. Установите Redis и celery.")
    _get_project(project_id, user, db)

    weights = None
    if body and body.weights:
        weights = {
            "skill_match": body.weights.skill_match,
            "salary_fit": body.weights.salary_fit,
            "experience": body.weights.experience,
        }

    task = optimize_large_project.delay(project_id, weights)
    return {"task_id": task.id, "status": "queued"}


@router.get("/projects/{project_id}/optimize/status/{task_id}")
def optimize_status(
    project_id: int,
    task_id: str,
    user: User = Depends(get_current_user),
):
    """Получить статус асинхронной задачи оптимизации."""
    if not _CELERY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Celery недоступен")

    result = AsyncResult(task_id, app=celery_app)
    if result.state == "PENDING":
        return {"state": "queued", "progress": 0}
    elif result.state == "PROGRESS":
        meta = result.info or {}
        return {"state": "running", "progress": meta.get("progress", 0), "stage": meta.get("stage", "")}
    elif result.state == "SUCCESS":
        return {"state": "done", "progress": 100, "result": result.result}
    elif result.state == "FAILURE":
        meta = result.info or {}
        return {"state": "error", "error": str(meta.get("error", result.result))}
    return {"state": result.state.lower()}
