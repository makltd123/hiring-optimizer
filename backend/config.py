from pathlib import Path
from pydantic_settings import BaseSettings

_ROOT = Path(__file__).parent.parent


class Settings(BaseSettings):
    database_url: str = "sqlite:///./hiring_optimizer.db"
    mistral_api_key: str = ""
    jwt_secret: str = "changeme"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    # CORS
    allowed_origins: str = "http://localhost:3000"

    # Encryption key for sensitive data at rest (Fernet base64-url-safe 32-byte key)
    # Generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    encryption_key: str = ""

    # Режим развёртывания: "cloud" или "enterprise"
    deployment_mode: str = "cloud"

    # Enterprise — локальная LLM через Ollama
    local_llm_url: str = "http://localhost:11434"
    local_llm_model: str = "llama3.1:8b"

    # v4: короткий access token + refresh token
    jwt_access_expire_minutes: int = 30
    jwt_refresh_expire_days: int = 30

    # Enterprise — LDAP/Active Directory
    ldap_enabled: bool = False
    ldap_server: str = ""
    ldap_base_dn: str = ""
    ldap_bind_dn: str = ""
    ldap_bind_password: str = ""

    # v4: уведомления
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    smtp_from: str = "noreply@hiringoptimizer.ru"
    telegram_bot_token: str = ""

    class Config:
        env_file = str(_ROOT / ".env")


settings = Settings()

if settings.jwt_secret == "changeme":
    raise RuntimeError(
        "JWT_SECRET не задан. Установите переменную окружения JWT_SECRET "
        "со случайным секретом (минимум 32 символа). "
        "Пример: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
    )
