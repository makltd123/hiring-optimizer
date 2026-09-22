"""
Импорт резюме из корпоративной почты через IMAP.
HH.ru отправляет PDF резюме откликнувшихся кандидатов на email HR-менеджера.
"""
import email
import imaplib
from io import BytesIO

from sqlalchemy.orm import Session


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    try:
        import pdfplumber
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            pages = [p.extract_text() or "" for p in pdf.pages]
            return "\n".join(pages).strip()
    except Exception:
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(BytesIO(pdf_bytes))
            return "\n".join(p.extract_text() or "" for p in reader.pages).strip()
        except Exception:
            return ""


class EmailResumeImporter:
    def __init__(self, host: str, port: int, user: str, password: str):
        self.mail = imaplib.IMAP4_SSL(host, port)
        self.mail.login(user, password)

    def fetch_new_resumes(self, sender_filter: str = "noreply@hh.ru") -> list[dict]:
        """Забрать непрочитанные письма с PDF-резюме."""
        self.mail.select("inbox")
        _, ids = self.mail.search(None, f'(FROM "{sender_filter}" UNSEEN)')

        pdfs = []
        for msg_id in ids[0].split():
            _, data = self.mail.fetch(msg_id, "(RFC822)")
            msg = email.message_from_bytes(data[0][1])

            for part in msg.walk():
                if part.get_content_type() == "application/pdf":
                    pdfs.append({
                        "pdf_bytes": part.get_payload(decode=True),
                        "filename": part.get_filename() or "resume.pdf",
                    })

            self.mail.store(msg_id, "+FLAGS", "\\Seen")

        return pdfs

    def test_connection(self) -> bool:
        try:
            self.mail.select("inbox")
            return True
        except Exception:
            return False

    def close(self):
        try:
            self.mail.logout()
        except Exception:
            pass


def import_from_email(project_id: int, email_config: dict, db: Session) -> int:
    """
    Импортировать резюме из почтового ящика в проект.
    email_config: {host, port, user, password, sender_filter?}
    Возвращает количество импортированных кандидатов.
    """
    from models.models import Candidate
    from services.anonymizer import anonymize
    from services.llm_client import get_llm_client

    importer = EmailResumeImporter(
        host=email_config["host"],
        port=int(email_config.get("port", 993)),
        user=email_config["user"],
        password=email_config["password"],
    )
    sender_filter = email_config.get("sender_filter", "noreply@hh.ru")
    llm = get_llm_client()
    count = 0

    try:
        existing_count = db.query(Candidate).filter(Candidate.project_id == project_id).count()
        pdfs = importer.fetch_new_resumes(sender_filter)

        for i, pdf_data in enumerate(pdfs):
            raw_text = _extract_pdf_text(pdf_data["pdf_bytes"])
            if not raw_text:
                continue

            anonymized = anonymize(raw_text)
            parsed = llm.parse_resume(anonymized)

            candidate = Candidate(
                project_id=project_id,
                display_name=f"Кандидат {existing_count + count + 1}",
                raw_text_anonymized=anonymized,
                parsed_skills=parsed,
                salary_expectation=float(parsed["salary_expectation"]) if parsed.get("salary_expectation") else None,
                parse_status="ready",
                source="email",
            )
            db.add(candidate)
            count += 1

        if count > 0:
            db.commit()
    finally:
        importer.close()

    return count
