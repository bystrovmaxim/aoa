import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import date

from ActionEngine.BaseSimpleAction import BaseSimpleAction
from ActionEngine.Context import Context
from ActionEngine.TransactionContext import TransactionContext
from ActionEngine.PostgresConnectionManager import PostgresConnectionManager
from ActionEngine.CheckRoles import CheckRoles
from ActionEngine.IntFieldChecker import IntFieldChecker
from ActionEngine.StringFieldChecker import StringFieldChecker
from ActionEngine.InstanceOfChecker import InstanceOfChecker

from App.FetchIssuesFromYouTrackAction import FetchIssuesFromYouTrackAction
from App.YouTrackStoriyIssuesPostgresSaver import YouTrackStoriyIssuesPostgresSaver
from App.YouTrackTasksIssuesPostgresSaver import YouTrackTasksIssuesPostgresSaver

logger = logging.getLogger(__name__)


@CheckRoles(CheckRoles.ANY)
@IntFieldChecker("page_size", min_value=1, max_value=500)
@StringFieldChecker("project_id", required=False, not_empty=True)
@StringFieldChecker("snapshot_date", required=False)
@StringFieldChecker("base_url", required=True)
@StringFieldChecker("token", required=True)
@StringFieldChecker("pg_host", required=True)
@IntFieldChecker("pg_port", required=True)
@StringFieldChecker("pg_db", required=True)
@StringFieldChecker("pg_user", required=True)
@StringFieldChecker("pg_password", required=True)
class BulkYouTrackIssueToPostgresAction(BaseSimpleAction):
    """
    Оркестрирующее действие: загружает задачи из YouTrack и сохраняет снимки в PostgreSQL.
    Параметры:
        base_url, token, page_size, project_id (опц.), snapshot_date (опц.),
        pg_host, pg_port, pg_db, pg_user, pg_password.
    """

    @InstanceOfChecker("managers", expected_class=list)  # <-- теперь managers, а не manager
    @InstanceOfChecker("savers", expected_class=list)
    def _preHandleAspect(self, ctx: Context, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Создаёт менеджер соединения и два saver'а (истории и задачи)."""
        db_params = {
            "host": params["pg_host"],
            "port": params["pg_port"],
            "dbname": params["pg_db"],
            "user": params["pg_user"],
            "password": params["pg_password"],
        }

        snapshot_date = params.get("snapshot_date")
        if snapshot_date is None:
            snapshot_date = date.today().isoformat()
        else:
            # проверка формата будет в saver'е
            pass

        mgr = PostgresConnectionManager(db_params)
        mgr.open()
        tx_ctx = TransactionContext(base_ctx=ctx, connection=mgr.connection)

        stories_saver = YouTrackStoriyIssuesPostgresSaver()
        tasks_saver = YouTrackTasksIssuesPostgresSaver()

        savers = [
            (tx_ctx, stories_saver, ["Пользовательская история", "Техническая история"]),
            (tx_ctx, tasks_saver, [
                "Разработка",
                "Аналитика и проектирование",
                "Решение инцидентов",
                "Работа вместо системы"
            ])
        ]

        return {"managers": [mgr], "savers": savers, "snapshot_date": snapshot_date}

    @IntFieldChecker("total_issues", min_value=0)
    @IntFieldChecker("pages", min_value=0)
    def _handleAspect(self, ctx: Context, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Запускает загрузчик задач."""
        fetcher = FetchIssuesFromYouTrackAction()
        fetcher_ctx = Context(user_id=ctx.user_id, roles=ctx.roles)

        fetch_params = {
            "base_url": params["base_url"],
            "token": params["token"],
            "page_size": params["page_size"],
            "project_id": params.get("project_id"),
            "savers": result["savers"],
            "snapshot_date": result["snapshot_date"],
        }

        fetch_result = fetcher.run(fetcher_ctx, fetch_params)
        # Добавляем менеджеры и snapshot_date в результат для пост-обработки
        fetch_result["managers"] = result["managers"]
        fetch_result["snapshot_date"] = result["snapshot_date"]
        return fetch_result

    @IntFieldChecker("total_issues", min_value=0)
    @IntFieldChecker("pages", min_value=0)
    def _postHandleAspect(self, ctx: Context, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Фиксирует транзакцию и возвращает только статистику загрузки."""
        for mgr in result.get("managers", []):
            mgr.commit()
        result.pop("managers", None)
        result.pop("savers", None)
        return result