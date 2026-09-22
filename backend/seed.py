"""Seed script: creates demo user, project, vacancies, candidates."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import bcrypt
from models.base import SessionLocal, engine
from models.models import Base, User, Project, Vacancy, Candidate

Base.metadata.create_all(bind=engine)
db = SessionLocal()

# --- User ---
EMAIL, PASSWORD = "demo@hireopt.ru", "demo1234"
user = db.query(User).filter(User.email == EMAIL).first()
if not user:
    user = User(email=EMAIL, password_hash=bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt()).decode())
    db.add(user); db.commit(); db.refresh(user)
    print(f"User created: {EMAIL} / {PASSWORD}")
else:
    print(f"User already exists: {EMAIL}")

# --- Project ---
project = db.query(Project).filter(Project.user_id == user.id).first()
if not project:
    project = Project(user_id=user.id, title="Запуск продукта — осень 2024", fot_limit=600000)
    db.add(project); db.commit(); db.refresh(project)
    print(f"Project created: {project.title}")
else:
    print(f"Project already exists: {project.title}")

# --- Vacancies ---
vacancies_data = [
    {"title": "Backend Developer", "required_skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "REST API"], "salary_max": 180000},
    {"title": "Frontend Developer", "required_skills": ["React", "TypeScript", "Tailwind CSS", "Next.js"], "salary_max": 160000},
    {"title": "Data Analyst",       "required_skills": ["SQL", "Python", "pandas", "Tableau", "Excel"],       "salary_max": 130000},
]
existing_vac = db.query(Vacancy).filter(Vacancy.project_id == project.id).count()
if existing_vac == 0:
    for v in vacancies_data:
        db.add(Vacancy(project_id=project.id, **v))
    db.commit()
    print(f"Vacancies created: {len(vacancies_data)}")
else:
    print(f"Vacancies already exist: {existing_vac}")

# --- Candidates ---
candidates_data = [
    {
        "display_name": "Кандидат 1",
        "raw_text_anonymized": "[ИМЯ УДАЛЕНО]\nPython-разработчик, 4 года опыта. FastAPI, PostgreSQL, Docker, Redis, REST API.",
        "parsed_skills": {"skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis", "REST API"], "experience_years": 4, "salary_expectation": 170000, "summary": "Backend Python-разработчик с опытом построения REST API."},
        "salary_expectation": 170000,
    },
    {
        "display_name": "Кандидат 2",
        "raw_text_anonymized": "[ИМЯ УДАЛЕНО]\nFrontend-разработчик. React, TypeScript, Next.js, Tailwind CSS, GraphQL, 3 года.",
        "parsed_skills": {"skills": ["React", "TypeScript", "Next.js", "Tailwind CSS", "GraphQL"], "experience_years": 3, "salary_expectation": 155000, "summary": "Frontend-разработчик, специализация React/Next.js."},
        "salary_expectation": 155000,
    },
    {
        "display_name": "Кандидат 3",
        "raw_text_anonymized": "[ИМЯ УДАЛЕНО]\nАналитик данных. SQL, Python, pandas, Power BI, Tableau, Excel. 5 лет опыта.",
        "parsed_skills": {"skills": ["SQL", "Python", "pandas", "Power BI", "Tableau", "Excel"], "experience_years": 5, "salary_expectation": 125000, "summary": "Аналитик данных с глубокой экспертизой в BI-инструментах."},
        "salary_expectation": 125000,
    },
    {
        "display_name": "Кандидат 4",
        "raw_text_anonymized": "[ИМЯ УДАЛЕНО]\nFullstack-разработчик. Python, Django, React, PostgreSQL, Docker. 2 года.",
        "parsed_skills": {"skills": ["Python", "Django", "React", "PostgreSQL", "Docker"], "experience_years": 2, "salary_expectation": 140000, "summary": "Fullstack-разработчик, опыт Python/Django + React."},
        "salary_expectation": 140000,
    },
    {
        "display_name": "Кандидат 5",
        "raw_text_anonymized": "[ИМЯ УДАЛЕНО]\nData Scientist. Python, pandas, scikit-learn, SQL, Jupyter. 3 года.",
        "parsed_skills": {"skills": ["Python", "pandas", "scikit-learn", "SQL", "Jupyter"], "experience_years": 3, "salary_expectation": 150000, "summary": "Data Scientist, опыт машинного обучения и анализа данных."},
        "salary_expectation": 150000,
    },
]
existing_cand = db.query(Candidate).filter(Candidate.project_id == project.id).count()
if existing_cand == 0:
    for c in candidates_data:
        db.add(Candidate(project_id=project.id, parse_status="ready", **c))
    db.commit()
    print(f"Candidates created: {len(candidates_data)}")
else:
    print(f"Candidates already exist: {existing_cand}")

db.close()
print("\nDone! Open http://localhost:3000 and login:")
print(f"  Email:    {EMAIL}")
print(f"  Password: {PASSWORD}")
