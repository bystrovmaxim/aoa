# APP/InitDatabaseAction.py
from ActionEngine import (
    BaseTransactionAction,
    requires_connection_type,
    TransactionContext,
    InstanceOfChecker,
    StringFieldChecker)
import psycopg2

@requires_connection_type(psycopg2.extensions.connection, desc="Требуется соединение с PostgreSQL")
class InitDatabaseAction(BaseTransactionAction):
    """
    Создаёт схему youtrack и таблицы с нуля, включая:
      - issues: id (PK), key (UNIQUE), project_code (GENERATED)
      - user_tech_stories: issue_id (FK), snapshot_date, все общие поля (кроме id) + специфичные поля историй
      - taskitems: аналогично
      - issues_status_history: issue_id, timestamp, author_login, old_status, new_status
    Все таблицы расширений содержат дублирующиеся поля из issues для фиксации состояния на момент снимка.
    """

    @InstanceOfChecker("tables_created", expected_class=list, desc="Результат: список созданных таблиц")
    @StringFieldChecker("schema", desc="Результат: имя созданной схемы")
    def _handleAspect(self, ctx: TransactionContext, params: dict, result: dict) -> dict:
        conn = ctx.connection
        cur = conn.cursor()
        cur.execute("CREATE SCHEMA IF NOT EXISTS youtrack;")

        # --- Таблица issues (общие поля, актуальное состояние) ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS youtrack.issues (
                id TEXT PRIMARY KEY,
                key TEXT UNIQUE NOT NULL,
                title TEXT,
                description TEXT,
                created TIMESTAMP,
                parent_key TEXT,
                type_issue TEXT,
                class_issue TEXT,
                project_id TEXT,
                project_name TEXT,
                project_code TEXT GENERATED ALWAYS AS (split_part(key, '-', 1)) STORED
            );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_issues_project_code ON youtrack.issues(project_code);")

        # --- Таблица user_tech_stories (снимки историй) ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS youtrack.user_tech_stories (
                issue_id TEXT NOT NULL,
                key TEXT NOT NULL,
                snapshot_date DATE NOT NULL,
                title TEXT,
                description TEXT,
                created TIMESTAMP,
                parent_key TEXT,
                type_issue TEXT,
                project_id TEXT,
                project_name TEXT,
                project_code TEXT GENERATED ALWAYS AS (split_part(key, '-', 1)) STORED,
                -- специфичные поля историй
                updated TIMESTAMP,
                date_resolved TIMESTAMP,
                assignee_login TEXT,
                assignee_name TEXT,
                assignee_fullname TEXT,
                status TEXT,
                plan_start DATE,
                plan_finish DATE,
                fact_forecast_start DATE,
                fact_forecast_finish DATE,
                customer TEXT,
                sprints TEXT,
                imported_at TIMESTAMP DEFAULT NOW(),
                PRIMARY KEY (issue_id, snapshot_date),
                FOREIGN KEY (issue_id) REFERENCES youtrack.issues(id) ON UPDATE CASCADE ON DELETE RESTRICT
            );
        """)

        # --- Таблица taskitems (снимки задач) ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS youtrack.taskitems (
                issue_id TEXT NOT NULL,
                key TEXT NOT NULL,
                snapshot_date DATE NOT NULL,
                title TEXT,
                description TEXT,
                created TIMESTAMP,
                parent_key TEXT,
                type_issue TEXT,
                project_id TEXT,
                project_name TEXT,
                project_code TEXT GENERATED ALWAYS AS (split_part(key, '-', 1)) STORED,
                -- специфичные поля задач
                updated TIMESTAMP,
                date_resolved TIMESTAMP,
                assignee_login TEXT,
                assignee_name TEXT,
                assignee_fullname TEXT,
                tester_login TEXT,
                tester_name TEXT,
                tester_fullname TEXT,
                status TEXT,
                story_points NUMERIC,
                priority TEXT,
                subcomponent TEXT,
                sprints TEXT,
                imported_at TIMESTAMP DEFAULT NOW(),
                PRIMARY KEY (issue_id, snapshot_date),
                FOREIGN KEY (issue_id) REFERENCES youtrack.issues(id) ON UPDATE CASCADE ON DELETE RESTRICT
            );
        """)

        # Индексы для быстрого поиска по дате снимка
        cur.execute("CREATE INDEX IF NOT EXISTS idx_user_tech_stories_snapshot ON youtrack.user_tech_stories(snapshot_date);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_taskitems_snapshot ON youtrack.taskitems(snapshot_date);")

        # --- Таблица issues_status_history (история статусов) ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS youtrack.issues_status_history (
                issue_id TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                author_login TEXT,
                old_status TEXT,
                new_status TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                PRIMARY KEY (issue_id, timestamp),
                FOREIGN KEY (issue_id) REFERENCES youtrack.issues(id) ON UPDATE CASCADE ON DELETE CASCADE
            );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_issues_status_history_timestamp ON youtrack.issues_status_history(timestamp);")

        cur.execute("""
            CREATE OR REPLACE VIEW youtrack.v_snapshot_summary AS
            WITH combined AS (
                SELECT s.snapshot_date, i.type_issue, 'story' source
                FROM youtrack.issues i
                JOIN youtrack.user_tech_stories s ON i.id = s.issue_id
                UNION ALL
                SELECT t.snapshot_date, i.type_issue, 'task' source
                FROM youtrack.issues i
                JOIN youtrack.taskitems t ON i.id = t.issue_id
            )
            SELECT
                snapshot_date,
                COUNT(*) AS total_records,
                COUNT(CASE WHEN source = 'story' THEN 1 END) AS total_stories,
                COUNT(CASE WHEN source = 'task' THEN 1 END) AS total_tasks,
                COUNT(CASE WHEN type_issue = 'Пользовательская история' THEN 1 END) AS user_story_count,
                COUNT(CASE WHEN type_issue = 'Техническая история' THEN 1 END) AS tech_story_count,
                COUNT(CASE WHEN type_issue = 'Разработка' THEN 1 END) AS development_count,
                COUNT(CASE WHEN type_issue = 'Аналитика и проектирование' THEN 1 END) AS analytics_count,
                COUNT(CASE WHEN type_issue = 'Решение инцидентов' THEN 1 END) AS incident_count,
                COUNT(CASE WHEN type_issue = 'Работа вместо системы' THEN 1 END) AS work_instead_system_count
            FROM combined
            GROUP BY snapshot_date
            ORDER BY snapshot_date DESC;
        """)

        return {"tables_created": ["issues", "user_tech_stories", "taskitems", "issues_status_history"], "schema": "youtrack"}