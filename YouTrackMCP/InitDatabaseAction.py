# YouTrackMCP/InitDatabaseAction.py
from ActionEngine.BaseTransactionAction import BaseTransactionAction
from ActionEngine.TransactionContext import TransactionContext
from ActionEngine.requires_connection_type import requires_connection_type
import psycopg2

@requires_connection_type(psycopg2.extensions.connection)
class InitDatabaseAction(BaseTransactionAction):
    """
    Создаёт схему youtrack и две таблицы для хранения ежедневных снимков:
    - user_tech_stories
    - taskitems
    Каждая запись уникальна по (key, snapshot_date).
    """

    def _handleAspect(self, ctx: TransactionContext, params: dict, result: dict) -> dict:
        conn = ctx.connection
        cur = conn.cursor()

        cur.execute("CREATE SCHEMA IF NOT EXISTS youtrack;")

        # Таблица user_tech_stories
        cur.execute("""
            CREATE TABLE IF NOT EXISTS youtrack.user_tech_stories (
                key TEXT NOT NULL,
                snapshot_date DATE NOT NULL,
                id TEXT,
                title TEXT,
                description TEXT,
                created TIMESTAMP,
                updated TIMESTAMP,
                date_resolved TIMESTAMP,
                parent_key TEXT,
                assignee_login TEXT,
                assignee_name TEXT,
                assignee_fullname TEXT,
                type TEXT,
                status TEXT,
                plan_start DATE,
                plan_finish DATE,
                fact_forecast_start DATE,
                fact_forecast_finish DATE,
                customer TEXT,
                sprints TEXT,
                imported_at TIMESTAMP DEFAULT NOW(),
                PRIMARY KEY (key, snapshot_date)
            );
        """)

        # Таблица taskitems
        cur.execute("""
            CREATE TABLE IF NOT EXISTS youtrack.taskitems (
                key TEXT NOT NULL,
                snapshot_date DATE NOT NULL,
                id TEXT,
                title TEXT,
                description TEXT,
                created TIMESTAMP,
                updated TIMESTAMP,
                date_resolved TIMESTAMP,
                parent_key TEXT,
                assignee_login TEXT,
                assignee_name TEXT,
                assignee_fullname TEXT,
                tester_login TEXT,
                tester_name TEXT,
                tester_fullname TEXT,
                type TEXT,
                status TEXT,
                story_points NUMERIC,
                priority TEXT,
                subcomponent TEXT,
                sprints TEXT,
                imported_at TIMESTAMP DEFAULT NOW(),
                PRIMARY KEY (key, snapshot_date)
            );
        """)

        # Индексы для ускорения запросов по дате снимка
        cur.execute("CREATE INDEX IF NOT EXISTS idx_user_tech_stories_snapshot ON youtrack.user_tech_stories(snapshot_date);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_taskitems_snapshot ON youtrack.taskitems(snapshot_date);")

        conn.commit()
        return {"tables_created": ["user_tech_stories", "taskitems"], "schema": "youtrack"}