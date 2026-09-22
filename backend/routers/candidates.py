import threading
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from PyPDF2 import PdfReader
from io import BytesIO

from deps import get_current_user
from models.base import get_db, SessionLocal
from models.models import User, Project, Candidate
from schemas.schemas import CandidateOut, CandidateStatusUpdate
from services.anonymizer import anonymize
from services.audit import AuditAction, log_action
from services.deduplication import deduplicator
from services.limits import check_limit
from services.llm_client import get_llm_client

router = APIRouter()

VALID_STATUSES = {"new", "in_review", "interview", "offer", "hired", "rejected", "archived"}


def _get_project(project_id: int, user: User, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _extract_text(file_bytes: bytes, filename: str) -> str:
    if filename.lower().endswith(".pdf"):
        try:
            reader = PdfReader(BytesIO(file_bytes))
            pages = [p.extract_text() or "" for p in reader.pages]
            text = "\n".join(pages).strip()
            if not text:
                raise HTTPException(
                    status_code=422,
                    detail="PDF не содержит извлекаемого текста (возможно, скан). Загрузите TXT-версию.",
                )
            return text
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=422, detail="Не удалось прочитать PDF. Загрузите TXT-версию.")
    return file_bytes.decode("utf-8", errors="replace")


def _parse_in_background(candidate_id: int):
    db = SessionLocal()
    try:
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if not candidate:
            return
        parsed = get_llm_client().parse_resume(candidate.raw_text_anonymized)
        candidate.parsed_skills = parsed
        if parsed.get("salary_expectation"):
            candidate.salary_expectation = float(parsed["salary_expectation"])
        candidate.parse_status = "ready"
        db.commit()

        # Дедупликация после успешного парсинга
        existing = db.query(Candidate).filter(
            Candidate.project_id == candidate.project_id,
            Candidate.id != candidate.id,
            Candidate.parse_status == "ready",
        ).all()
        duplicates = deduplicator.find_duplicates(candidate, existing)
        if duplicates:
            # Сохраняем информацию о дубликатах в parsed_skills метаданных
            skills_data = dict(candidate.parsed_skills or {})
            skills_data["_possible_duplicates"] = duplicates
            candidate.parsed_skills = skills_data
            db.commit()
    except Exception:
        db_candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if db_candidate:
            db_candidate.parse_status = "error"
            db.commit()
    finally:
        db.close()


@router.post("/projects/{project_id}/candidates/upload", response_model=CandidateOut, status_code=201)
def upload_candidate(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = _get_project(project_id, user, db)
    count = db.query(Candidate).filter(Candidate.project_id == project.id).count()
    check_limit(user.plan, "max_candidates_per_project", count)

    file_bytes = file.file.read()
    raw_text = _extract_text(file_bytes, file.filename or "resume.txt")
    anonymized = anonymize(raw_text)
    display_name = f"Кандидат {count + 1}"

    candidate = Candidate(
        project_id=project.id,
        display_name=display_name,
        raw_text_anonymized=anonymized,
        parsed_skills={},
        parse_status="parsing",
        workflow_status="new",
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)

    log_action(user.id, AuditAction.CANDIDATE_ADDED, db,
               entity_type="candidate", entity_id=candidate.id)

    thread = threading.Thread(target=_parse_in_background, args=(candidate.id,), daemon=True)
    thread.start()

    return candidate


@router.get("/projects/{project_id}/candidates", response_model=list[CandidateOut])
def list_candidates(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _get_project(project_id, user, db)
    return db.query(Candidate).filter(Candidate.project_id == project_id).all()


def _get_candidate_for_user(candidate_id: int, user: User, db: Session) -> Candidate:
    """Получить кандидата с проверкой что он принадлежит org/user."""
    candidate = (
        db.query(Candidate)
        .join(Project, Project.id == Candidate.project_id)
        .filter(
            Candidate.id == candidate_id,
            Project.user_id == user.id,
        )
        .first()
    )
    if not candidate:
        raise HTTPException(status_code=404, detail="Кандидат не найден")
    return candidate


@router.patch("/candidates/{candidate_id}/status", response_model=CandidateOut)
def update_status(
    candidate_id: int,
    body: CandidateStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    candidate = _get_candidate_for_user(candidate_id, user, db)
    if body.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Недопустимый статус. Допустимые: {VALID_STATUSES}")

    old_status = candidate.workflow_status
    candidate.workflow_status = body.status
    candidate.status_changed_at = datetime.utcnow()
    candidate.status_changed_by = user.id
    if body.rejection_reason:
        candidate.rejection_reason = body.rejection_reason
    db.commit()
    db.refresh(candidate)

    log_action(user.id, AuditAction.CANDIDATE_STATUS_CHANGED, db,
               entity_type="candidate", entity_id=candidate_id,
               details={"from": old_status, "to": body.status})
    return candidate


@router.get("/projects/{project_id}/candidates/duplicates")
def list_duplicates(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _get_project(project_id, user, db)
    candidates = db.query(Candidate).filter(
        Candidate.project_id == project_id,
        Candidate.parse_status == "ready",
    ).all()

    result = []
    for c in candidates:
        dups = (c.parsed_skills or {}).get("_possible_duplicates", [])
        if dups:
            result.append({
                "candidate_id": c.id,
                "display_name": c.display_name,
                "possible_duplicates": dups,
            })
    return result


@router.post("/candidates/{candidate_id}/merge/{duplicate_id}")
def merge_candidates(
    candidate_id: int,
    duplicate_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _get_candidate_for_user(candidate_id, user, db)
    _get_candidate_for_user(duplicate_id, user, db)
    return deduplicator.merge_candidates(candidate_id, duplicate_id, db)


@router.post("/candidates/{candidate_id}/not-duplicate/{other_id}")
def mark_not_duplicate(
    candidate_id: int,
    other_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    candidate = _get_candidate_for_user(candidate_id, user, db)
    skills_data = dict(candidate.parsed_skills or {})
    dups = skills_data.get("_possible_duplicates", [])
    skills_data["_possible_duplicates"] = [d for d in dups if d.get("candidate_id") != other_id]
    candidate.parsed_skills = skills_data
    db.commit()
    return {"status": "marked_not_duplicate"}
