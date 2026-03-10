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
    Создаёт схему youtrack и таблицы с нуля:
      - issues: id (PK), key (UNIQUE), project_code (GENERATED),
                last_update (дата последнего изменения задачи в YouTrack),
                last_activity_processed (серверное время последней обработки активностей)
      - user_tech_stories, taskitems, issues_status_history
    """

    @InstanceOfChecker("tables_created", expected_class=list, desc="Результат: список созданных таблиц")
    @StringFieldChecker("schema", desc="Результат: имя созданной схемы")
    def _handleAspect(self, ctx: TransactionContext, params: dict, result: dict) -> dict:
        conn = ctx.connection
        cur = conn.cursor()
        cur.execute("CREATE SCHEMA IF NOT EXISTS youtrack;")

        # --- Таблица issues ---
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
                project_code TEXT GENERATED ALWAYS AS (split_part(key, '-', 1)) STORED,
                last_update TIMESTAMP,                       -- дата последнего изменения задачи в YouTrack (из поля updated)
                last_activity_processed TIMESTAMP            -- серверное время последней обработки активностей
            );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_issues_project_code ON youtrack.issues(project_code);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_issues_last_update ON youtrack.issues(last_update);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_issues_last_activity ON youtrack.issues(last_activity_processed);")

        # --- Таблица user_tech_stories ---
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

        # --- Таблица taskitems ---
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

        cur.execute("CREATE INDEX IF NOT EXISTS idx_user_tech_stories_snapshot ON youtrack.user_tech_stories(snapshot_date);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_taskitems_snapshot ON youtrack.taskitems(snapshot_date);")

        # --- Таблица issues_status_history ---
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
        cur.execute("CREATE INDEX IF NOT EXISTS idx_issues_status_history_issue_id ON youtrack.issues_status_history(issue_id);")

        # --- Представление v_snapshot_summary (сокращено для читаемости) ---
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

        return {
            "tables_created": ["issues", "user_tech_stories", "taskitems", "issues_status_history"],
            "schema": "youtrack"
        }