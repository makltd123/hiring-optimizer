"""
Celery-очередь для асинхронной оптимизации больших проектов (>200 кандидатов).
Требует Redis: redis://redis:6379/0 (docker) или локальный Redis.
"""
import numpy as np
from celery import Celery

celery_app = Celery(
    "hiring_optimizer",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1",
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    result_expires=3600,
)

CHUNK_SIZE = 200


def _chunk_list(lst: list, size: int) -> list[list]:
    return [lst[i:i + size] for i in range(0, len(lst), size)]


@celery_app.task(bind=True)
def optimize_large_project(self, project_id: int, weights: dict | None = None):
    """
    Асинхронная оптимизация. Используется при >200 кандидатах или явном запросе.
    Декомпозирует задачу на чанки по CHUNK_SIZE кандидатов.
    """
    from models.base import SessionLocal
    from models.models import Project, Vacancy, Candidate, OptimizationResult
    from services.matcher import build_match_matrix
    from services.optimizer import run_optimization
    from schemas.schemas import OptimizationWeights

    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project {project_id} not found")

        vacancies = db.query(Vacancy).filter(Vacancy.project_id == project_id).all()
        candidates = db.query(Candidate).filter(
            Candidate.project_id == project_id,
            Candidate.parse_status == "ready",
        ).all()

        if not vacancies or not candidates:
            raise ValueError("Нет вакансий или кандидатов для оптимизации")

        w_obj = None
        if weights:
            try:
                w_obj = OptimizationWeights(**weights)
            except Exception:
                pass

        self.update_state(state="PROGRESS", meta={"progress": 5, "stage": "Построение матрицы соответствия"})

        if len(candidates) > CHUNK_SIZE:
            chunks = _chunk_list(candidates, CHUNK_SIZE)
            all_matrices = []
            all_candidates_ordered = []

            for i, chunk in enumerate(chunks):
                progress = 5 + int((i / len(chunks)) * 70)
                self.update_state(
                    state="PROGRESS",
                    meta={"progress": progress, "stage": f"Обработка группы {i + 1}/{len(chunks)}"},
                )
                matrix = build_match_matrix(chunk, vacancies, weights=w_obj)
                all_matrices.append(matrix)
                all_candidates_ordered.extend(chunk)

            full_matrix = np.vstack(all_matrices)
            final_candidates = all_candidates_ordered
        else:
            full_matrix = build_match_matrix(candidates, vacancies, weights=w_obj)
            final_candidates = candidates

        self.update_state(state="PROGRESS", meta={"progress": 80, "stage": "Венгерский алгоритм"})

        result_data = run_optimization(full_matrix, final_candidates, vacancies, project.fot_limit)

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
            weights_used=weights or project.optimization_weights,
        )
        db.add(result)
        db.commit()
        db.refresh(result)

        self.update_state(state="PROGRESS", meta={"progress": 95, "stage": "Сохранение результата"})

        # Уведомления (синхронно через asyncio)
        try:
            import asyncio
            from services.notifications import send_optimization_complete
            asyncio.run(send_optimization_complete(project, result, db))
        except Exception:
            pass

        self.update_state(state="PROGRESS", meta={"progress": 100, "stage": "Готово"})
        return {"status": "done", "project_id": project_id, "result_id": result.id}

    except Exception as exc:
        self.update_state(state="FAILURE", meta={"error": str(exc)})
        raise
    finally:
        db.close()


@celery_app.task
def run_data_retention_cleanup():
    """Ночная очистка данных по политике хранения ФЗ-152 (запускается в 3:00)."""
    from models.base import SessionLocal
    from services.pdp_compliance import pdp_service
    db = SessionLocal()
    try:
        count = pdp_service.run_retention_cleanup(db)
        return {"status": "done", "erased_count": count}
    finally:
        db.close()


# Celery beat расписание
celery_app.conf.beat_schedule = {
    "data-retention-cleanup": {
        "task": "services.task_queue.run_data_retention_cleanup",
        "schedule": 86400,  # каждые 24 часа (3:00 достигается через crontab в production)
    },
}
