from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.base import get_db
from models.models import User, Project, Vacancy
from schemas.schemas import VacancyCreate, VacancyOut
from deps import get_current_user
from services.limits import check_limit

router = APIRouter()


def _get_project(project_id: int, user: User, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/projects/{project_id}/vacancies", response_model=VacancyOut, status_code=201)
def create_vacancy(
    project_id: int,
    body: VacancyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = _get_project(project_id, user, db)
    count = db.query(Vacancy).filter(Vacancy.project_id == project.id).count()
    check_limit(user.plan, "max_vacancies_per_project", count)
    vacancy = Vacancy(
        project_id=project.id,
        title=body.title,
        required_skills=body.required_skills,
        salary_max=body.salary_max,
    )
    db.add(vacancy)
    db.commit()
    db.refresh(vacancy)
    return vacancy


@router.delete("/projects/{project_id}/vacancies/{vacancy_id}", status_code=204)
def delete_vacancy(
    project_id: int,
    vacancy_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = _get_project(project_id, user, db)
    vacancy = db.query(Vacancy).filter(Vacancy.id == vacancy_id, Vacancy.project_id == project.id).first()
    if not vacancy:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    db.delete(vacancy)
    db.commit()
