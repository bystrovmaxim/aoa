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

@CheckRoles(CheckRoles.ANY, desc="Доступен любому аутентифицированному пользователю")
@IntFieldChecker("page_size", min_value=1, max_value=500, desc="Входной параметр: размер страницы")
@StringFieldChecker("project_id", required=False, not_empty=True, desc="Входной параметр: идентификатор проекта (опционально)")
@StringFieldChecker("snapshot_date", required=False, desc="Входной параметр: дата снимка (строка YYYY-MM-DD, опционально)")
@StringFieldChecker("base_url", required=True, desc="Входной параметр: URL YouTrack")
@StringFieldChecker("token", required=True, desc="Входной параметр: токен доступа")
@StringFieldChecker("pg_host", required=True, desc="Входной параметр: хост PostgreSQL")
@IntFieldChecker("pg_port", required=True, desc="Входной параметр: порт PostgreSQL")
@StringFieldChecker("pg_db", required=True, desc="Входной параметр: имя базы данных PostgreSQL")
@StringFieldChecker("pg_user", required=True, desc="Входной параметр: пользователь PostgreSQL")
@StringFieldChecker("pg_password", required=True, desc="Входной параметр: пароль PostgreSQL")
class BulkYouTrackIssueToPostgresAction(BaseSimpleAction):

    @InstanceOfChecker("managers", expected_class=list, desc="Результат _preHandleAspect: список менеджеров соединений (один элемент)")
    @InstanceOfChecker("savers", expected_class=list, desc="Результат _preHandleAspect: список кортежей (context, saver, card_types)")
    def _preHandleAspect(self, ctx: Context, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Создаёт менеджер соединения и два saver'а (истории и задачи)."""
        db_params = {
            "host": params["pg_host"],
            "port": params["pg_port"],
            "dbname": params["pg_db"],
            "user": params["pg_user"],
            "password": params["pg_password"],
        }

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

        return {"managers": [mgr], "savers": savers}

    @IntFieldChecker("total_issues", min_value=0, desc="Результат _handleAspect: общее количество загруженных задач")
    @IntFieldChecker("pages", min_value=0, desc="Результат _handleAspect: количество обработанных страниц")
    def _handleAspect(self, ctx: Context, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Запускает загрузчик задач."""
        fetcher = FetchIssuesFromYouTrackAction()
        fetcher_ctx = Context(user_id=ctx.user_id, roles=ctx.roles)

        # snapshot_date берём из params, если не задано, используем сегодня
        snapshot_date = params.get("snapshot_date")
        if snapshot_date is None:
            snapshot_date = date.today().isoformat()

        fetch_params = {
            "base_url": params["base_url"],
            "token": params["token"],
            "page_size": params["page_size"],
            "project_id": params.get("project_id"),
            "savers": result["savers"],
            "snapshot_date": snapshot_date,
        }

        fetch_result = fetcher.run(fetcher_ctx, fetch_params)
        # Добавляем менеджеры в результат для пост-обработки
        fetch_result["managers"] = result["managers"]
        return fetch_result

    @IntFieldChecker("total_issues", min_value=0, desc="Результат _postHandleAspect: общее количество загруженных задач")
    @IntFieldChecker("pages", min_value=0, desc="Результат _postHandleAspect: количество обработанных страниц")
    def _postHandleAspect(self, ctx: Context, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Фиксирует транзакцию и возвращает только статистику загрузки."""
        for mgr in result.get("managers", []):
            mgr.commit()
        result.pop("managers", None)
        result.pop("savers", None)
        return result