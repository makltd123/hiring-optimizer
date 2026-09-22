import json
import re
from abc import ABC, abstractmethod

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


def _extract_json(text: str) -> dict:
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    return _FALLBACK.copy()


class BaseLLMClient(ABC):
    @abstractmethod
    def parse_resume(self, anonymized_text: str) -> dict:
        pass


class MistralLLMClient(BaseLLMClient):
    """Cloud Edition — Mistral API."""

    def parse_resume(self, anonymized_text: str) -> dict:
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
            return _extract_json(raw)
        except Exception:
            return _FALLBACK.copy()


class LocalLLMClient(BaseLLMClient):
    """Enterprise Edition — локальная модель через Ollama."""

    def parse_resume(self, anonymized_text: str) -> dict:
        try:
            response = httpx.post(
                f"{settings.local_llm_url}/api/generate",
                json={
                    "model": settings.local_llm_model,
                    "prompt": PARSE_PROMPT.format(resume_text=anonymized_text),
                    "stream": False,
                },
                timeout=120.0,
            )
            response.raise_for_status()
            raw = response.json().get("response", "").strip()
            return _extract_json(raw)
        except Exception:
            return _FALLBACK.copy()


def get_llm_client() -> BaseLLMClient:
    if settings.deployment_mode == "enterprise":
        return LocalLLMClient()
    return MistralLLMClient()
