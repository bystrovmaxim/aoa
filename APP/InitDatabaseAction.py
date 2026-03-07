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
    Создаёт схему youtrack и следующие таблицы:
      - issues         – общие поля для всех задач
      - user_tech_stories – расширение для историй (пользовательские/технические)
      - taskitems          – расширение для задач (разработка, аналитика, инциденты, работа вместо системы)
      - issue_status_history – история изменений статусов задач

    Также создаёт представления:
      - v_user_tech_stories_full – полные данные историй с общими полями
      - v_taskitems_full          – полные данные задач с общими полями
      - v_snapshot_summary        – сводка по датам снимков с разбивкой по типам задач

    Связи:
      - issues.key (первичный ключ)
      - В таблицах-расширениях составной первичный ключ (key, snapshot_date)
      - Внешний ключ key -> issues.key с ограничением ON DELETE RESTRICT
        (нельзя удалить задачу, пока существуют её снимки)
      - parent_key в issues не имеет внешнего ключа (хранится как обычное текстовое поле)
      - issue_status_history.key -> issues.key с ON DELETE CASCADE (при удалении задачи удаляется и её история)
    """

    @InstanceOfChecker("tables_created", expected_class=list, desc="Результат: список созданных таблиц")
    @StringFieldChecker("schema", desc="Результат: имя созданной схемы")
    def _handleAspect(self, ctx: TransactionContext, params: dict, result: dict) -> dict:
        conn = ctx.connection
        cur = conn.cursor()

        # Создаём схему, если её нет
        cur.execute("CREATE SCHEMA IF NOT EXISTS youtrack;")

        # --- Таблица issues (общие поля) ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS youtrack.issues (
                key TEXT PRIMARY KEY,                     -- idReadable из YouTrack
                id TEXT,                                   -- внутренний ID YouTrack
                title TEXT,
                description TEXT,
                created TIMESTAMP,
                parent_key TEXT,                           -- ссылка на другую задачу (key) – без внешнего ключа
                type_issue TEXT,                           -- тип карточки (например, "Пользовательская история")
                class_issue TEXT                           -- имя таблицы-расширения (например, 'user_tech_stories')
            );
        """)

        # --- Таблица user_tech_stories (расширение для историй) ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS youtrack.user_tech_stories (
                key TEXT NOT NULL,
                snapshot_date DATE NOT NULL,
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
                PRIMARY KEY (key, snapshot_date)
            );
        """)

        # Удаляем существующее ограничение, если оно есть, и создаём заново
        cur.execute("ALTER TABLE youtrack.user_tech_stories DROP CONSTRAINT IF EXISTS fk_ustories_issues;")
        cur.execute("""
            ALTER TABLE youtrack.user_tech_stories
            ADD CONSTRAINT fk_ustories_issues
            FOREIGN KEY (key) REFERENCES youtrack.issues(key)
            ON UPDATE CASCADE ON DELETE RESTRICT;
        """)

        # --- Таблица taskitems (расширение для задач) ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS youtrack.taskitems (
                key TEXT NOT NULL,
                snapshot_date DATE NOT NULL,
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
                PRIMARY KEY (key, snapshot_date)
            );
        """)

        cur.execute("ALTER TABLE youtrack.taskitems DROP CONSTRAINT IF EXISTS fk_taskitems_issues;")
        cur.execute("""
            ALTER TABLE youtrack.taskitems
            ADD CONSTRAINT fk_taskitems_issues
            FOREIGN KEY (key) REFERENCES youtrack.issues(key)
            ON UPDATE CASCADE ON DELETE RESTRICT;
        """)

        # Индексы для быстрого поиска по дате снимка
        cur.execute("CREATE INDEX IF NOT EXISTS idx_user_tech_stories_snapshot ON youtrack.user_tech_stories(snapshot_date);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_taskitems_snapshot ON youtrack.taskitems(snapshot_date);")

        # --- Таблица issue_status_history (история статусов) ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS youtrack.issue_status_history (
                key TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                author_login TEXT,
                old_status TEXT,
                new_status TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                PRIMARY KEY (key, timestamp)
            );
        """)

        # Внешний ключ с каскадным удалением
        cur.execute("ALTER TABLE youtrack.issue_status_history DROP CONSTRAINT IF EXISTS fk_status_history_issues;")
        cur.execute("""
            ALTER TABLE youtrack.issue_status_history
            ADD CONSTRAINT fk_status_history_issues
            FOREIGN KEY (key) REFERENCES youtrack.issues(key)
            ON UPDATE CASCADE ON DELETE CASCADE;
        """)

        # Индекс для ускорения запросов по времени
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_issue_status_history_timestamp
            ON youtrack.issue_status_history (timestamp);
        """)

        # --- Представление v_user_tech_stories_full (полные данные историй) ---
        cur.execute("""
            CREATE OR REPLACE VIEW youtrack.v_user_tech_stories_full AS
            SELECT
                i.key,
                i.id,
                i.title,
                i.description,
                i.created,
                i.parent_key,
                i.type_issue,
                i.class_issue,
                s.snapshot_date,
                s.updated,
                s.date_resolved,
                s.assignee_login,
                s.assignee_name,
                s.assignee_fullname,
                s.status,
                s.plan_start,
                s.plan_finish,
                s.fact_forecast_start,
                s.fact_forecast_finish,
                s.customer,
                s.sprints,
                s.imported_at
            FROM youtrack.issues i
            JOIN youtrack.user_tech_stories s ON i.key = s.key;
        """)

        # --- Представление v_taskitems_full (полные данные задач) ---
        cur.execute("""
            CREATE OR REPLACE VIEW youtrack.v_taskitems_full AS
            SELECT
                i.key,
                i.id,
                i.title,
                i.description,
                i.created,
                i.parent_key,
                i.type_issue,
                i.class_issue,
                t.snapshot_date,
                t.updated,
                t.date_resolved,
                t.assignee_login,
                t.assignee_name,
                t.assignee_fullname,
                t.tester_login,
                t.tester_name,
                t.tester_fullname,
                t.status,
                t.story_points,
                t.priority,
                t.subcomponent,
                t.sprints,
                t.imported_at
            FROM youtrack.issues i
            JOIN youtrack.taskitems t ON i.key = t.key;
        """)

        # --- Представление v_snapshot_summary (сводка по датам снимков) ---
        cur.execute("""
            CREATE OR REPLACE VIEW youtrack.v_snapshot_summary AS
            WITH combined AS (
                SELECT
                    s.snapshot_date,
                    i.type_issue,
                    'story' AS source
                FROM youtrack.issues i
                JOIN youtrack.user_tech_stories s ON i.key = s.key
                UNION ALL
                SELECT
                    t.snapshot_date,
                    i.type_issue,
                    'task' AS source
                FROM youtrack.issues i
                JOIN youtrack.taskitems t ON i.key = t.key
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

        return {"tables_created": ["issues", "user_tech_stories", "taskitems", "issue_status_history"], "schema": "youtrack"}