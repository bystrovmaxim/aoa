import os
import logging
from typing import Optional, Dict, Any
from datetime import date

from ActionEngine.Context import Context
from .BulkYouTrackIssueToCsvAction import BulkYouTrackIssueToCsvAction
from .BulkYouTrackIssueToPostgresAction import BulkYouTrackIssueToPostgresAction
from .InitDatabaseServerAction import InitDatabaseServerAction

logger = logging.getLogger(__name__)

class YouTrackMCPServer:
    """
    Тонкий фасад для вызова оркестрирующих действий из внешних систем (n8n).
    Преобразует исключения в стандартный формат ответа.
    """

    @staticmethod
    def init_database() -> Dict[str, Any]:
        pg_host = os.getenv("POSTGRES_HOST")
        if not pg_host:
            return {"success": False, "result": None, "errors": ["POSTGRES_HOST не задан"]}
        try:
            pg_port = int(os.getenv("POSTGRES_PORT", "5432"))
        except ValueError:
            return {"success": False, "result": None, "errors": ["POSTGRES_PORT должен быть числом"]}
        pg_db = os.getenv("POSTGRES_DB")
        pg_user = os.getenv("POSTGRES_USER")
        pg_password = os.getenv("POSTGRES_PASSWORD")
        if not pg_db or not pg_user or not pg_password:
            return {"success": False, "result": None, "errors": ["POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD должны быть заданы"]}

        action = InitDatabaseServerAction()
        ctx = Context(user_id="system", roles=["admin"])
        params = {
            "pg_host": pg_host,
            "pg_port": pg_port,
            "pg_db": pg_db,
            "pg_user": pg_user,
            "pg_password": pg_password,
        }
        try:
            result = action.run(ctx, params)
            return {"success": True, "result": result, "errors": []}
        except Exception as e:
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

        action = BulkYouTrackIssueToCsvAction()
        ctx = Context(user_id="system", roles=["user"])
        params = {
            "base_url": base_url,
            "token": token,
            "user_stories_file": user_stories_file,
            "tasks_file": tasks_file,
            "page_size": page_size,
            "project_id": project_id,
        }
        try:
            result = action.run(ctx, params)
            return {"success": True, "result": result, "errors": []}
        except Exception as e:
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

        pg_host = os.getenv("POSTGRES_HOST")
        if not pg_host:
            return {"success": False, "result": None, "errors": ["POSTGRES_HOST не задан"]}
        try:
            pg_port = int(os.getenv("POSTGRES_PORT", "5432"))
        except ValueError:
            return {"success": False, "result": None, "errors": ["POSTGRES_PORT должен быть числом"]}
        pg_db = os.getenv("POSTGRES_DB")
        pg_user = os.getenv("POSTGRES_USER")
        pg_password = os.getenv("POSTGRES_PASSWORD")
        if not pg_db or not pg_user or not pg_password:
            return {"success": False, "result": None, "errors": ["POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD должны быть заданы"]}

        action = BulkYouTrackIssueToPostgresAction()
        ctx = Context(user_id="system", roles=["user"])
        params = {
            "base_url": base_url,
            "token": token,
            "project_id": project_id,
            "page_size": page_size,
            "snapshot_date": snapshot_date.isoformat() if snapshot_date else None,
            "pg_host": pg_host,
            "pg_port": pg_port,
            "pg_db": pg_db,
            "pg_user": pg_user,
            "pg_password": pg_password,
        }
        try:
            result = action.run(ctx, params)
            return {"success": True, "result": result, "errors": []}
        except Exception as e:
            logger.exception("Ошибка в bulk_youtrack_issue_to_postgres")
            return {"success": False, "result": None, "errors": [str(e)]}