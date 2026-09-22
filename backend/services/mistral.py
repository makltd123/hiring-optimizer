import json
import re
import httpx
from config import settings

PARSE_PROMPT = """Ты анализируешь анонимизированное резюме. Извлеки данные и верни ТОЛЬКО JSON без пояснений:

{{
  "skills": ["список навыков и технологий"],
  "experience_years": число лет общего опыта,
  "salary_expectation": число в рублях или null если не указано,
  "summary": "краткое описание профиля в 1-2 предложениях"
}}

Резюме:
{resume_text}"""

_FALLBACK = {"skills": [], "experience_years": 0, "salary_expectation": None, "summary": ""}


def parse_resume(anonymized_text: str) -> dict:
    try:
        response = httpx.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.mistral_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "mistral-small-latest",
                "messages": [{"role": "user", "content": PARSE_PROMPT.format(resume_text=anonymized_text)}],
            },
            timeout=30,
        )
        response.raise_for_status()
        raw = response.json()["choices"][0]["message"]["content"].strip()
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return _FALLBACK.copy()
    except Exception:
        return _FALLBACK.copy()
