# Hiring Optimizer

**English** | [Русский](README.ru.md)

A web app that picks the best team from a pool of candidates. An LLM parses resumes, a match matrix scores every candidate against every vacancy, and the Hungarian algorithm assigns candidates to vacancies — or an integer program, when there is a payroll budget. Around this core there is an HR workflow and an enterprise layer.

The UI and the generated reports are in Russian.

## What it does

**Core**
- Resume upload → names, emails and phone numbers are stripped by a regex anonymizer → the LLM extracts skills, experience and salary expectations (Mistral in cloud mode, a local Ollama `llama3.1:8b` in enterprise mode).
- Match matrix: fuzzy skill matching with adjustable weights (skills / salary / experience).
- Assignment: the Hungarian algorithm (`scipy.optimize.linear_sum_assignment`); with a payroll limit, an integer program (`scipy.optimize.milp`).
- "What if" simulator, skill gap, reserve list with reasons, payroll scenarios (budget → vacancy coverage), PDF report.

**HR workflow**
- Candidate statuses (8), private HR comments, duplicate detection (Jaccard + TF-IDF) with merging.
- Approval workflow for hiring decisions: submit, approve, reject, request changes.
- Import from email (IMAP) and Avito; notifications by email, Telegram and signed webhooks.

**Enterprise layer**
- 5 roles (RBAC), multi-tenancy by organization with PostgreSQL Row Level Security, audit log with CSV export.
- JWT access + refresh tokens with session management, MFA (TOTP + backup codes), LDAP/Active Directory, SAML 2.0, rate limiting.
- Integration credentials encrypted at rest (Fernet).
- Personal data (152-FZ / GDPR): consent, right to erasure, data export, breach notification, scheduled retention cleanup.
- Branded PDF reports, freemium plan limits.

## Stack

- **Frontend:** Next.js 14 (App Router), TypeScript, Tailwind CSS, Recharts
- **Backend:** Python, FastAPI, SQLAlchemy
- **Database:** SQLite locally, PostgreSQL in Docker
- **LLM:** Mistral API or a local Ollama model, behind one client (`services/llm_client.py`)
- **Math:** scipy (`linear_sum_assignment`, `milp`)
- **Enterprise (optional):** Celery + Redis, ldap3, python3-saml, pyotp

## Running locally

Create `.env` in the project root from `.env.example`:

```
MISTRAL_API_KEY=...
JWT_SECRET=...        # required; the backend refuses to start with "changeme"
```

**Backend** (port 8000):

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
python seed.py        # demo data, login demo@hireopt.ru / demo1234
```

**Frontend** (port 3000):

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 (API docs at http://localhost:8000/docs). Sample resumes for upload are in `sample_resumes/` — they are made up.

## Docker

```bash
docker compose up --build
```

Starts PostgreSQL, the backend and the frontend. The database password (`secret`) and the fallback JWT secret in `docker-compose.yml` are for local use only — change them anywhere else.

Enterprise setup (PostgreSQL, Redis, Ollama, Celery worker, backend, frontend):

```bash
docker compose -f docker-compose.enterprise.yml --env-file .env.enterprise up -d
docker compose -f docker-compose.enterprise.yml exec ollama ollama pull llama3.1:8b
```

`.env.enterprise` needs at least `DB_PASSWORD` and `JWT_SECRET`.

## Main environment variables

| Variable | Purpose |
|---|---|
| `MISTRAL_API_KEY` | resume parsing in cloud mode |
| `JWT_SECRET` | token signing, required |
| `DATABASE_URL` | defaults to local SQLite |
| `ALLOWED_ORIGINS` | CORS origins, comma-separated |
| `ENCRYPTION_KEY` | Fernet key for integration credentials — **without it they are stored in plain text** |
| `DEPLOYMENT_MODE`, `LOCAL_LLM_URL`, `LOCAL_LLM_MODEL` | enterprise mode with a local LLM |
| `LDAP_*`, `SMTP_*`, `TELEGRAM_BOT_TOKEN` | LDAP sign-in and notifications |

## Freemium limits

| Plan | Projects | Vacancies | Candidates |
|---|---|---|---|
| free | 1 | 3 | 10 |
| start / business | 999 | 50 | 200 |

Going over returns HTTP 402 with `"upgrade_required": true`.

## Notes and limitations

- Optional packages degrade gracefully: without Redis/Celery the async endpoints return 503; without pyotp/qrcode or python3-saml the MFA and SAML endpoints return 503; without scikit-learn deduplication uses Jaccard only; without slowapi rate limiting is off.
- Row Level Security only works on PostgreSQL; on SQLite the code filters by organization in queries instead.
- On Python 3.14: run uvicorn without `--reload` (it loops), and scipy/numpy need versions with 3.14 wheels (scipy ≥ 1.17.1, numpy ≥ 2.3.5).
- A vacancy's maximum salary is passed to the optimizer but not enforced yet.
- Not implemented: real billing, OIDC sign-in (only SAML 2.0), 1C integration, a mobile app.

## License

[MIT](LICENSE)

---

Author: [Fedor Makovskiy](https://fedor.alqira.ru), AI developer. Services and projects with quality metrics: [fedor.alqira.ru](https://fedor.alqira.ru).
