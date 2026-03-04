import logging
import os
from typing import Optional, Dict, Any
from datetime import date

from ActionEngine.Context import Context
from ActionEngine.TransactionContext import TransactionContext
from ActionEngine.CsvConnectionManager import CsvConnectionManager
from ActionEngine.PostgresConnectionManager import PostgresConnectionManager
from .FetchIssuesFromYouTrackAction import FetchIssuesFromYouTrackAction
from .YouTrackIssuesCSVSaver import YouTrackIssuesCSVSaver
from .YouTrackStoriyIssuesPostgresSaver import YouTrackStoriyIssuesPostgresSaver
from .YouTrackTasksIssuesPostgresSaver import YouTrackTasksIssuesPostgresSaver
from .InitDatabaseAction import InitDatabaseAction   # если нужен

logger = logging.getLogger(__name__)


class YouTrackMCPServer:
    """
    Фасад для вызова действий YouTrack.
    """

    @staticmethod
    def init_database() -> Dict[str, Any]:
        """
        Инициализирует таблицы в PostgreSQL (использует переменные окружения).
        """
        host = os.getenv("POSTGRES_HOST", "localhost")
        try:
            port = int(os.getenv("POSTGRES_PORT", "5432"))
        except ValueError:
            return {"success": False, "result": None, "errors": ["POSTGRES_PORT должен быть числом"]}
        dbname = os.getenv("POSTGRES_DB")
        user = os.getenv("POSTGRES_USER")
        password = os.getenv("POSTGRES_PASSWORD")

        if not dbname:
            return {"success": False, "result": None, "errors": ["POSTGRES_DB не задана"]}
        if not user:
            return {"success": False, "result": None, "errors": ["POSTGRES_USER не задан"]}
        if not password:
            return {"success": False, "result": None, "errors": ["POSTGRES_PASSWORD не задан"]}

        db_params = {"host": host, "port": port, "dbname": dbname, "user": user, "password": password}
        mgr = PostgresConnectionManager(db_params)
        mgr.open()
        ctx = TransactionContext(
            base_ctx=Context(user_id="system", roles=["admin"]),
            connection=mgr.connection
        )
        action = InitDatabaseAction()
        try:
            result = action.run(ctx, {})
            mgr.commit()
            return {"success": True, "result": result, "errors": []}
        except Exception as e:
            mgr.rollback()
            logger.exception("Ошибка при инициализации БД")
            return {"success": False, "result": None, "errors": [str(e)]}

    @staticmethod
    def bulk_youtrack_issue_to_csv(
        user_stories_file: Optional[str] = None,
        tasks_file: Optional[str] = None,
        page_size: int = 100,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        base_url = os.getenv("YOUTRACK_URL")
        token = os.getenv("YOUTRACK_TOKEN")
        if not base_url or not token:
            return {"success": False, "result": None, "errors": ["YOUTRACK_URL или YOUTRACK_TOKEN не заданы"]}

        # Один экземпляр saver'а для всех CSV
        csv_saver = YouTrackIssuesCSVSaver()
        savers = []
        managers = []

        if user_stories_file:
            mgr = CsvConnectionManager(filepath=user_stories_file)
            mgr.open()
            managers.append(mgr)
            ctx = TransactionContext(
                base_ctx=Context(user_id="system", roles=["user"]),
                connection=mgr
            )
            savers.append((ctx, csv_saver, ["Пользовательская история", "Техническая история"]))

        if tasks_file:
            mgr = CsvConnectionManager(filepath=tasks_file)
            mgr.open()
            managers.append(mgr)
            ctx = TransactionContext(
                base_ctx=Context(user_id="system", roles=["user"]),
                connection=mgr
            )
            savers.append((ctx, csv_saver, [
                "Разработка",
                "Аналитика и проектирование",
                "Решение инцидентов",
                "Работа вместо системы"
            ]))

        if not savers:
            return {"success": False, "result": None, "errors": ["Не указано ни одного файла"]}

        fetcher = FetchIssuesFromYouTrackAction()
        params = {
            "base_url": base_url,
            "token": token,
            "page_size": page_size,
            "project_id": project_id,
            "savers": savers,
        }

        try:
            # Для запуска fetcher'а нужен любой контекст (первый из списка)
            result = fetcher.run(savers[0][0], params)
            for mgr in managers:
                mgr.commit()
            return {"success": True, "result": result, "errors": []}
        except Exception as e:
            for mgr in managers:
                mgr.rollback()
            logger.exception("Ошибка в bulk_youtrack_issue_to_csv")
            return {"success": False, "result": None, "errors": [str(e)]}

    @staticmethod
    def bulk_youtrack_issue_to_postgres(
        project_id: Optional[str] = None,
        page_size: int = 100,
        snapshot_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        base_url = os.getenv("YOUTRACK_URL")
        token = os.getenv("YOUTRACK_TOKEN")
        if not base_url or not token:
            return {"success": False, "result": None, "errors": ["YOUTRACK_URL или YOUTRACK_TOKEN не заданы"]}

        # Параметры PostgreSQL из окружения
        host = os.getenv("POSTGRES_HOST", "localhost")
        try:
            port = int(os.getenv("POSTGRES_PORT", "5432"))
        except ValueError:
            return {"success": False, "result": None, "errors": ["POSTGRES_PORT должен быть числом"]}
        dbname = os.getenv("POSTGRES_DB")
        user = os.getenv("POSTGRES_USER")
        password = os.getenv("POSTGRES_PASSWORD")
        if not dbname or not user or not password:
            return {"success": False, "result": None, "errors": ["POSTGRES_* переменные не заданы"]}

        db_params = {"host": host, "port": port, "dbname": dbname, "user": user, "password": password}

        if snapshot_date is None:
            snapshot_date = date.today()

        # Единый менеджер и один контекст для обоих saver'ов
        mgr = PostgresConnectionManager(db_params)
        mgr.open()
        ctx = TransactionContext(
            base_ctx=Context(user_id="system", roles=["user"]),
            connection=mgr.connection
        )

        stories_saver = YouTrackStoriyIssuesPostgresSaver(snapshot_date=snapshot_date)
        tasks_saver = YouTrackTasksIssuesPostgresSaver(snapshot_date=snapshot_date)

        savers = [
            (ctx, stories_saver, ["Пользовательская история", "Техническая история"]),
            (ctx, tasks_saver, [
                "Разработка",
                "Аналитика и проектирование",
                "Решение инцидентов",
                "Работа вместо системы"
            ])
        ]

        fetcher = FetchIssuesFromYouTrackAction()
        params = {
            "base_url": base_url,
            "token": token,
            "page_size": page_size,
            "project_id": project_id,
            "savers": savers,
        }

        try:
            result = fetcher.run(ctx, params)
            mgr.commit()
            return {"success": True, "result": result, "errors": []}
        except Exception as e:
            mgr.rollback()
            logger.exception("Ошибка в bulk_youtrack_issue_to_postgres")
            return {"success": False, "result": None, "errors": [str(e)]}