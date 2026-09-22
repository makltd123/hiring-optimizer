-- PostgreSQL Row Level Security для multi-tenancy изоляции.
-- Применять только в Enterprise развёртывании (PostgreSQL, не SQLite).
-- Запускать от суперпользователя ОДИН РАЗ после первичного деплоя.

-- Включаем RLS
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE candidates ENABLE ROW LEVEL SECURITY;
ALTER TABLE vacancies ENABLE ROW LEVEL SECURITY;
ALTER TABLE optimization_results ENABLE ROW LEVEL SECURITY;

-- Суперпользователь обходит RLS
ALTER TABLE projects FORCE ROW LEVEL SECURITY;
ALTER TABLE candidates FORCE ROW LEVEL SECURITY;
ALTER TABLE vacancies FORCE ROW LEVEL SECURITY;
ALTER TABLE optimization_results FORCE ROW LEVEL SECURITY;

-- Политики для projects
CREATE POLICY org_isolation_projects ON projects
    USING (
        org_id IS NULL
        OR org_id = NULLIF(current_setting('app.current_org_id', true), '')::int
    );

-- Политики для candidates (через join на projects)
CREATE POLICY org_isolation_candidates ON candidates
    USING (
        project_id IN (
            SELECT id FROM projects
            WHERE org_id IS NULL
               OR org_id = NULLIF(current_setting('app.current_org_id', true), '')::int
        )
    );

-- Политики для vacancies
CREATE POLICY org_isolation_vacancies ON vacancies
    USING (
        project_id IN (
            SELECT id FROM projects
            WHERE org_id IS NULL
               OR org_id = NULLIF(current_setting('app.current_org_id', true), '')::int
        )
    );

-- Политики для optimization_results
CREATE POLICY org_isolation_results ON optimization_results
    USING (
        project_id IN (
            SELECT id FROM projects
            WHERE org_id IS NULL
               OR org_id = NULLIF(current_setting('app.current_org_id', true), '')::int
        )
    );
