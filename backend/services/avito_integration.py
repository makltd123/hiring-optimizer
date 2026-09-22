"""
Интеграция с Авито Работа API.
API доступен по заявке на partners.avito.ru.
Документация: https://developers.avito.ru/api-catalog/job
"""
import httpx
from sqlalchemy.orm import Session

AVITO_API_BASE = "https://api.avito.ru"


class AvitoWorkClient:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token: str | None = None

    def authenticate(self) -> bool:
        """Получить токен через OAuth2 client_credentials."""
        try:
            response = httpx.post(
                f"{AVITO_API_BASE}/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                timeout=15,
            )
            response.raise_for_status()
            self.access_token = response.json()["access_token"]
            return True
        except Exception:
            return False

    def get_responses(self, vacancy_id: str) -> list[dict]:
        """Получить отклики на вакансию."""
        if not self.access_token:
            return []
        try:
            response = httpx.get(
                f"{AVITO_API_BASE}/job/v2/vacancies/{vacancy_id}/responses",
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=30,
            )
            response.raise_for_status()
            return response.json().get("responses", [])
        except Exception:
            return []

    def get_resume_text(self, resume_id: str) -> str:
        """Получить текст резюме по ID."""
        if not self.access_token:
            return ""
        try:
            response = httpx.get(
                f"{AVITO_API_BASE}/job/v2/resumes/{resume_id}",
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            parts = []
            if data.get("title"):
                parts.append(f"Должность: {data['title']}")
            if data.get("experience"):
                for exp in data["experience"]:
                    parts.append(f"{exp.get('position', '')} в {exp.get('company', '')}: {exp.get('description', '')}")
            if data.get("skills"):
                parts.append(f"Навыки: {', '.join(data['skills'])}")
            if data.get("salary") and data["salary"].get("amount"):
                parts.append(f"Ожидаемая зарплата: {data['salary']['amount']} ₽")
            return "\n".join(parts)
        except Exception:
            return ""


def import_from_avito(project_id: int, vacancy_id: str, avito_config: dict, db: Session) -> int:
    """
    Импортировать отклики с Авито по ID вакансии.
    avito_config: {client_id, client_secret}
    """
    from models.models import Candidate
    from services.anonymizer import anonymize
    from services.llm_client import get_llm_client

    client = AvitoWorkClient(
        client_id=avito_config["client_id"],
        client_secret=avito_config["client_secret"],
    )
    if not client.authenticate():
        raise ValueError("Не удалось аутентифицироваться в Авито API")

    responses = client.get_responses(vacancy_id)
    llm = get_llm_client()
    count = 0
    existing_count = db.query(Candidate).filter(Candidate.project_id == project_id).count()

    for resp in responses:
        resume_id = resp.get("resume_id") or resp.get("id")
        if not resume_id:
            continue

        raw_text = client.get_resume_text(str(resume_id))
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
            source="avito",
        )
        db.add(candidate)
        count += 1

    if count > 0:
        db.commit()

    return count
