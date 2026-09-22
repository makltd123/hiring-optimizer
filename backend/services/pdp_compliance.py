from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from models.models import Candidate, ConsentRecord, ErasureRequest, Project
from services.audit import AuditAction, log_action


class DataRetentionPolicy:
    CANDIDATE_DATA_DAYS = 180
    AUDIT_LOG_DAYS = 365 * 3
    ANONYMIZED_DATA_DAYS = 365 * 5


class PDPService:
    def record_consent(
        self,
        candidate_id: int,
        consent_type: str,
        ip_address: str | None,
        user_agent: str | None,
        db: Session,
    ) -> ConsentRecord:
        consent = ConsentRecord(
            candidate_id=candidate_id,
            consent_type=consent_type,
            granted_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=365),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(consent)
        db.commit()
        db.refresh(consent)
        return consent

    def process_erasure_request(
        self,
        candidate_id: int,
        requested_by: int | None,
        db: Session,
    ) -> dict:
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if not candidate:
            raise ValueError("Кандидат не найден")
        if candidate.erased_at:
            return {"status": "already_erased", "candidate_id": candidate_id}

        candidate.raw_text_anonymized = "[УДАЛЕНО ПО ЗАПРОСУ СУБЪЕКТА]"
        candidate.parsed_skills = {}
        candidate.salary_expectation = None
        candidate.display_name = f"[Удалён {datetime.utcnow().date()}]"
        candidate.erased_at = datetime.utcnow()
        candidate.erased_by = requested_by

        req = ErasureRequest(
            candidate_id=candidate_id,
            requested_by=requested_by,
            requested_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            status="completed",
        )
        db.add(req)

        if requested_by:
            log_action(
                user_id=requested_by,
                action=AuditAction.DATA_ERASURE_REQUEST,
                entity_type="candidate",
                entity_id=candidate_id,
                details={"reason": "subject_request"},
                db=db,
            )

        db.commit()
        return {"status": "erased", "candidate_id": candidate_id}

    def get_data_export(self, candidate_id: int, db: Session) -> dict:
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if not candidate:
            raise ValueError("Кандидат не найден")
        consents = db.query(ConsentRecord).filter(ConsentRecord.candidate_id == candidate_id).all()
        return {
            "candidate_id": candidate_id,
            "data_stored": {
                "display_name": candidate.display_name,
                "skills": candidate.parsed_skills,
                "salary_expectation": candidate.salary_expectation,
                "parse_status": candidate.parse_status,
                "created_at": str(candidate.created_at),
                "erased_at": str(candidate.erased_at) if candidate.erased_at else None,
            },
            "consents": [
                {
                    "type": c.consent_type,
                    "granted_at": str(c.granted_at),
                    "expires_at": str(c.expires_at) if c.expires_at else None,
                    "revoked_at": str(c.revoked_at) if c.revoked_at else None,
                }
                for c in consents
            ],
            "exported_at": str(datetime.utcnow()),
        }

    def run_retention_cleanup(self, db: Session) -> int:
        cutoff_date = datetime.utcnow() - timedelta(days=DataRetentionPolicy.CANDIDATE_DATA_DAYS)
        old_candidates = (
            db.query(Candidate)
            .join(Project, Candidate.project_id == Project.id)
            .filter(
                Project.status == "closed",
                Project.created_at < cutoff_date,
                Candidate.erased_at.is_(None),
            )
            .all()
        )
        count = 0
        for candidate in old_candidates:
            try:
                self.process_erasure_request(candidate.id, None, db)
                count += 1
            except Exception:
                pass
        return count


pdp_service = PDPService()
