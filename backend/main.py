from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from sqlalchemy import text
from models.base import Base, engine
from routers import auth, projects, candidates, vacancies, optimize, simulate, skill_gap, reserve, budget
from routers import org, integrations, admin
from routers import pdp, comments, approvals
from config import settings

Base.metadata.create_all(bind=engine)


def _run_migrations():
    v1_v2 = [
        "ALTER TABLE projects ADD COLUMN optimization_weights JSON DEFAULT '{\"skill_match\": 0.6, \"salary_fit\": 0.3, \"experience\": 0.1}'",
        "ALTER TABLE optimization_results ADD COLUMN coverage FLOAT",
        "ALTER TABLE optimization_results ADD COLUMN weights_used JSON",
    ]
    v3_columns = [
        # users
        "ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'hr_manager'",
        "ALTER TABLE users ADD COLUMN org_id INTEGER REFERENCES organizations(id)",
        "ALTER TABLE users ADD COLUMN dept_id INTEGER REFERENCES departments(id)",
        "ALTER TABLE users ADD COLUMN ldap_dn TEXT",
        "ALTER TABLE users ADD COLUMN last_login DATETIME",
        # projects
        "ALTER TABLE projects ADD COLUMN org_id INTEGER REFERENCES organizations(id)",
        "ALTER TABLE projects ADD COLUMN dept_id INTEGER REFERENCES departments(id)",
        "ALTER TABLE projects ADD COLUMN priority TEXT DEFAULT 'normal'",
        "ALTER TABLE projects ADD COLUMN deadline DATETIME",
        # candidates
        "ALTER TABLE candidates ADD COLUMN source TEXT DEFAULT 'upload'",
    ]
    v3_tables = [
        """CREATE TABLE IF NOT EXISTS organizations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            domain TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            settings_json JSON DEFAULT '{}'
        )""",
        """CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            org_id INTEGER NOT NULL REFERENCES organizations(id),
            name TEXT NOT NULL,
            parent_id INTEGER REFERENCES departments(id),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER REFERENCES users(id),
            action TEXT NOT NULL,
            entity_type TEXT,
            entity_id INTEGER,
            details JSON DEFAULT '{}',
            ip_address TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS integration_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            type TEXT NOT NULL,
            config_json JSON DEFAULT '{}',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )""",
    ]
    # v4: новые колонки
    v4_columns = [
        # users — MFA
        "ALTER TABLE users ADD COLUMN mfa_enabled BOOLEAN DEFAULT FALSE",
        "ALTER TABLE users ADD COLUMN mfa_secret TEXT",
        "ALTER TABLE users ADD COLUMN mfa_backup_codes JSON DEFAULT '[]'",
        "ALTER TABLE users ADD COLUMN mfa_verified_at DATETIME",
        # users — refresh tokens + уведомления
        "ALTER TABLE users ADD COLUMN token_version INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN notify_email BOOLEAN DEFAULT TRUE",
        "ALTER TABLE users ADD COLUMN telegram_chat_id TEXT",
        # organizations — SAML/OIDC
        "ALTER TABLE organizations ADD COLUMN saml_enabled BOOLEAN DEFAULT FALSE",
        "ALTER TABLE organizations ADD COLUMN saml_entity_id TEXT",
        "ALTER TABLE organizations ADD COLUMN saml_sso_url TEXT",
        "ALTER TABLE organizations ADD COLUMN saml_certificate TEXT",
        "ALTER TABLE organizations ADD COLUMN oidc_enabled BOOLEAN DEFAULT FALSE",
        "ALTER TABLE organizations ADD COLUMN oidc_client_id TEXT",
        "ALTER TABLE organizations ADD COLUMN oidc_client_secret TEXT",
        "ALTER TABLE organizations ADD COLUMN oidc_discovery_url TEXT",
        # organizations — вебхуки + брендинг
        "ALTER TABLE organizations ADD COLUMN webhook_url TEXT",
        "ALTER TABLE organizations ADD COLUMN webhook_secret TEXT",
        "ALTER TABLE organizations ADD COLUMN logo_url TEXT",
        "ALTER TABLE organizations ADD COLUMN brand_color TEXT",
        "ALTER TABLE organizations ADD COLUMN report_footer TEXT",
        # candidates — workflow + GDPR
        "ALTER TABLE candidates ADD COLUMN workflow_status TEXT DEFAULT 'new'",
        "ALTER TABLE candidates ADD COLUMN status_changed_at DATETIME",
        "ALTER TABLE candidates ADD COLUMN status_changed_by INTEGER REFERENCES users(id)",
        "ALTER TABLE candidates ADD COLUMN rejection_reason TEXT",
        "ALTER TABLE candidates ADD COLUMN merged_into INTEGER REFERENCES candidates(id)",
        "ALTER TABLE candidates ADD COLUMN erased_at DATETIME",
        "ALTER TABLE candidates ADD COLUMN erased_by INTEGER",
        # v4.1: TOTP replay protection
        "ALTER TABLE users ADD COLUMN mfa_last_totp_counter INTEGER",
    ]
    # v4: новые таблицы
    v4_tables = [
        """CREATE TABLE IF NOT EXISTS refresh_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            token_hash TEXT NOT NULL UNIQUE,
            expires_at DATETIME NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            revoked BOOLEAN DEFAULT FALSE,
            revoked_at DATETIME,
            user_agent TEXT,
            ip_address TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS candidate_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER NOT NULL REFERENCES candidates(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            text TEXT NOT NULL,
            is_private BOOLEAN DEFAULT FALSE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            deleted_at DATETIME
        )""",
        """CREATE TABLE IF NOT EXISTS consent_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER NOT NULL REFERENCES candidates(id),
            consent_type TEXT NOT NULL,
            granted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            expires_at DATETIME,
            revoked_at DATETIME,
            ip_address TEXT,
            user_agent TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS erasure_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER NOT NULL REFERENCES candidates(id),
            requested_by INTEGER REFERENCES users(id),
            requested_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            completed_at DATETIME,
            status TEXT DEFAULT 'pending'
        )""",
        """CREATE TABLE IF NOT EXISTS breach_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            detected_at DATETIME NOT NULL,
            notified_at DATETIME,
            affected_records INTEGER,
            description TEXT NOT NULL,
            status TEXT DEFAULT 'open',
            created_by INTEGER REFERENCES users(id),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS webhook_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            org_id INTEGER REFERENCES organizations(id),
            event TEXT NOT NULL,
            payload JSON DEFAULT '{}',
            status_code INTEGER,
            response_body TEXT,
            sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            retry_count INTEGER DEFAULT 0
        )""",
        """CREATE TABLE IF NOT EXISTS hiring_approvals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL REFERENCES projects(id),
            result_id INTEGER NOT NULL REFERENCES optimization_results(id),
            requested_by INTEGER NOT NULL REFERENCES users(id),
            approver_id INTEGER REFERENCES users(id),
            status TEXT DEFAULT 'pending',
            comment TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            decided_at DATETIME
        )""",
    ]

    with engine.connect() as conn:
        for sql in v3_tables + v4_tables:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                pass
        for sql in v1_v2 + v3_columns + v4_columns:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                pass


_run_migrations()

# slowapi rate limiting
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded

    limiter = Limiter(key_func=get_remote_address)
    _SLOWAPI_AVAILABLE = True
except ImportError:
    limiter = None
    _SLOWAPI_AVAILABLE = False

app = FastAPI(title="Hiring Optimizer API", version="4.0.0")

if _SLOWAPI_AVAILABLE:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_allowed_origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

from middleware.tenant import TenantMiddleware
app.add_middleware(TenantMiddleware)


@app.middleware("http")
async def security_headers_middleware(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# Статические файлы (логотипы)
uploads_path = Path("uploads")
uploads_path.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# v1 + v2 роутеры
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(projects.router, prefix="/projects", tags=["projects"])
app.include_router(candidates.router, tags=["candidates"])
app.include_router(vacancies.router, tags=["vacancies"])
app.include_router(optimize.router, tags=["optimize"])
app.include_router(simulate.router, tags=["simulate"])
app.include_router(skill_gap.router, tags=["skill-gap"])
app.include_router(reserve.router, tags=["reserve"])
app.include_router(budget.router, tags=["budget"])

# v3 роутеры
app.include_router(org.router)
app.include_router(integrations.router)
app.include_router(admin.router)

# v4 роутеры
app.include_router(pdp.router)
app.include_router(comments.router)
app.include_router(approvals.router)


@app.get("/health")
def health():
    from sqlalchemy import text as _text
    from models.base import engine as _engine

    db_ok = False
    try:
        with _engine.connect() as conn:
            conn.execute(_text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    llm_ok = False
    llm_detail = {}
    if settings.deployment_mode == "enterprise":
        try:
            import httpx
            r = httpx.get(f"{settings.local_llm_url}/api/tags", timeout=3)
            llm_ok = r.status_code == 200
            llm_detail = {"url": settings.local_llm_url, "model": settings.local_llm_model}
        except Exception:
            llm_detail = {"url": settings.local_llm_url, "error": "unreachable"}
    else:
        llm_ok = bool(settings.mistral_api_key)
        llm_detail = {"provider": "mistral", "configured": llm_ok}

    celery_ok = False
    try:
        from services.task_queue import celery_app
        inspect = celery_app.control.inspect(timeout=1)
        stats = inspect.stats()
        celery_ok = bool(stats)
    except Exception:
        pass

    overall = "ok" if db_ok else "degraded"
    return {
        "status": overall,
        "deployment_mode": settings.deployment_mode,
        "db": {"connected": db_ok},
        "llm": {"available": llm_ok, **llm_detail},
        "celery": {"available": celery_ok},
        "version": "4.0.0",
    }


@app.get("/health/llm")
def health_llm():
    if settings.deployment_mode == "enterprise":
        try:
            import httpx
            r = httpx.get(f"{settings.local_llm_url}/api/tags", timeout=5)
            models = [m["name"] for m in r.json().get("models", [])]
            return {
                "available": True,
                "url": settings.local_llm_url,
                "model": settings.local_llm_model,
                "loaded_models": models,
            }
        except Exception as e:
            return {"available": False, "url": settings.local_llm_url, "error": str(e)}
    return {
        "available": bool(settings.mistral_api_key),
        "provider": "mistral",
        "model": "mistral-small-latest",
    }


@app.get("/health/db")
def health_db():
    from sqlalchemy import inspect as sa_inspect
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        inspector = sa_inspect(engine)
        tables = inspector.get_table_names()
        return {"connected": True, "tables": tables}
    except Exception as e:
        return {"connected": False, "error": str(e)}
