# Оптимизатор найма

[English](README.md) | **Русский**

Веб-приложение, которое подбирает лучшую команду из пула кандидатов. LLM разбирает резюме, матрица соответствия оценивает каждого кандидата для каждой вакансии, а венгерский алгоритм распределяет кандидатов по вакансиям — или целочисленная оптимизация, если задан бюджет ФОТ. Вокруг этого ядра — HR-процессы и корпоративный слой.

## Что умеет

**Ядро**
- Загрузка резюме → ФИО, почта и телефон вырезаются регулярными выражениями → LLM извлекает навыки, опыт и зарплатные ожидания (Mistral в облачном режиме, локальная Ollama `llama3.1:8b` в корпоративном).
- Матрица соответствия: нечёткое сравнение навыков с настраиваемыми весами (навыки / зарплата / опыт).
- Распределение: венгерский алгоритм (`scipy.optimize.linear_sum_assignment`); при лимите ФОТ — целочисленная задача (`scipy.optimize.milp`).
- Симулятор «что если», дефицит навыков, резервный список с причинами, сценарии ФОТ (бюджет → покрытие вакансий), PDF-отчёт.

**HR-процессы**
- Статусы кандидатов (8), приватные комментарии HR, поиск дубликатов (Jaccard + TF-IDF) с объединением.
- Согласование решений о найме: отправить, утвердить, отклонить, вернуть на доработку.
- Импорт с почты (IMAP) и с Авито; уведомления по email, в Telegram и через подписанные вебхуки.

**Корпоративный слой**
- 5 ролей (RBAC), разделение данных по организациям с Row Level Security в PostgreSQL, журнал аудита с экспортом в CSV.
- JWT access + refresh токены с управлением сессиями, MFA (TOTP + резервные коды), LDAP/Active Directory, SAML 2.0, ограничение частоты запросов.
- Учётные данные интеграций шифруются при хранении (Fernet).
- Персональные данные (152-ФЗ / GDPR): согласия, право на забвение, выгрузка данных, уведомление об утечке, плановая очистка по сроку хранения.
- PDF-отчёты с брендингом, лимиты тарифов freemium.

## Стек

- **Frontend:** Next.js 14 (App Router), TypeScript, Tailwind CSS, Recharts
- **Backend:** Python, FastAPI, SQLAlchemy
- **БД:** SQLite локально, PostgreSQL в Docker
- **LLM:** Mistral API или локальная модель в Ollama через единый клиент (`services/llm_client.py`)
- **Математика:** scipy (`linear_sum_assignment`, `milp`)
- **Корпоративные опции:** Celery + Redis, ldap3, python3-saml, pyotp

## Локальный запуск

Создайте `.env` в корне проекта по образцу `.env.example`:

```
MISTRAL_API_KEY=...
JWT_SECRET=...        # обязательно; со значением "changeme" backend не запустится
```

**Backend** (порт 8000):

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
python seed.py        # демо-данные, вход demo@hireopt.ru / demo1234
```

**Frontend** (порт 3000):

```bash
cd frontend
npm install
npm run dev
```

Откройте http://localhost:3000 (документация API — http://localhost:8000/docs). Резюме для загрузки лежат в `sample_resumes/`, они выдуманные.

## Docker

```bash
docker compose up --build
```

Поднимает PostgreSQL, backend и frontend. Пароль базы (`secret`) и запасной JWT-секрет в `docker-compose.yml` годятся только для локального запуска — в любом другом месте их нужно заменить.

Корпоративная сборка (PostgreSQL, Redis, Ollama, Celery worker, backend, frontend):

```bash
docker compose -f docker-compose.enterprise.yml --env-file .env.enterprise up -d
docker compose -f docker-compose.enterprise.yml exec ollama ollama pull llama3.1:8b
```

В `.env.enterprise` нужны как минимум `DB_PASSWORD` и `JWT_SECRET`.

## Основные переменные окружения

| Переменная | Назначение |
|---|---|
| `MISTRAL_API_KEY` | разбор резюме в облачном режиме |
| `JWT_SECRET` | подпись токенов, обязательно |
| `DATABASE_URL` | по умолчанию локальная SQLite |
| `ALLOWED_ORIGINS` | разрешённые origins для CORS через запятую |
| `ENCRYPTION_KEY` | ключ Fernet для учётных данных интеграций — **без него они хранятся открытым текстом** |
| `DEPLOYMENT_MODE`, `LOCAL_LLM_URL`, `LOCAL_LLM_MODEL` | корпоративный режим с локальной LLM |
| `LDAP_*`, `SMTP_*`, `TELEGRAM_BOT_TOKEN` | вход через LDAP и уведомления |

## Лимиты freemium

| Тариф | Проекты | Вакансии | Кандидаты |
|---|---|---|---|
| free | 1 | 3 | 10 |
| start / business | 999 | 50 | 200 |

При превышении API возвращает HTTP 402 с `"upgrade_required": true`.

## Особенности и ограничения

- Необязательные пакеты отключаются мягко: без Redis/Celery асинхронные эндпоинты возвращают 503; без pyotp/qrcode или python3-saml — эндпоинты MFA и SAML возвращают 503; без scikit-learn дубликаты ищутся только по Jaccard; без slowapi ограничение частоты запросов выключено.
- Row Level Security работает только в PostgreSQL; на SQLite данные фильтруются по организации в самих запросах.
- На Python 3.14: uvicorn запускать без `--reload` (он зацикливается), а scipy/numpy нужны версии со сборками под 3.14 (scipy ≥ 1.17.1, numpy ≥ 2.3.5).
- Максимальная зарплата вакансии передаётся в оптимизатор, но пока не учитывается.
- Не реализовано: реальный биллинг, вход через OIDC (есть только SAML 2.0), интеграция с 1С, мобильное приложение.

## Лицензия

[MIT](LICENSE)
