# EntryPoint/BulkYouTrackIssueToPostgresAction.py
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import date

from ActionEngine import (
    BaseSimpleAction,
    TransactionContext,
    CheckRoles,
    IntFieldChecker,
    InstanceOfChecker,
    StringFieldChecker,
    PostgresConnectionManager,
    Context)

from APP.FetchIssuesFromYouTrackAction import FetchIssuesFromYouTrackAction
from APP.YouTrackStoryIssuesPostgresSaver import YouTrackStoryIssuesPostgresSaver
from APP.YouTrackTasksIssuesPostgresSaver import YouTrackTasksIssuesPostgresSaver
from APP.DeleteSnapshotPostgressAction import DeleteSnapshotProgressAction

logger = logging.getLogger(__name__)

@CheckRoles(CheckRoles.ANY, desc="Доступен любому аутентифицированному пользователю")
@IntFieldChecker("page_size", min_value=1, max_value=5000, desc="Входной параметр: размер страницы")
@StringFieldChecker("project_id", required=False, not_empty=True, desc="Входной параметр: идентификатор проекта (опционально)")
@StringFieldChecker("snapshot_date", required=True, desc="Входной параметр: дата снимка (строка YYYY-MM-DD, опционально)")
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
        db_params = {
            "host": params["pg_host"],
            "port": params["pg_port"],
            "dbname": params["pg_db"],
            "user": params["pg_user"],
            "password": params["pg_password"],
        }

        mgr = PostgresConnectionManager(db_params)
        mgr.open()
        tx_ctx = TransactionContext(
            user=ctx.user,
            request=ctx.request,
            environment=ctx.environment,
            connection=mgr.connection
        )

        # Создаём saver'ы
        stories_saver = YouTrackStoryIssuesPostgresSaver()
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

        # --- Добавляем удаление снимков ---
        snapshot_date = params.get("snapshot_date")
       
        # Выполняем удаление в той же транзакции
        delete_action = DeleteSnapshotProgressAction()
        delete_params = {
            "snapshot_date": snapshot_date,
            "tables": ["user_tech_stories", "taskitems"],
            "schema": params.get("schema", "youtrack")  # если есть параметр schema
        }
        # Запускаем действие удаления с тем же контекстом (tx_ctx)
        delete_result = delete_action.run(tx_ctx, delete_params)
        logger.info(f"Удалено записей перед загрузкой: {delete_result.get('deleted_total')}")
        # ---------------------------------

        return {"managers": [mgr], "savers": savers, "tx_ctx": tx_ctx}

    @IntFieldChecker("total_issues", min_value=0, desc="Результат _handleAspect: общее количество загруженных задач")
    @IntFieldChecker("pages", min_value=0, desc="Результат _handleAspect: количество обработанных страниц")
    @InstanceOfChecker("details", expected_class=dict, desc="Результат _handleAspect: детальная статистика по сейверам")
    def _handleAspect(self, ctx: Context, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Запускает загрузчик задач."""
        fetcher = FetchIssuesFromYouTrackAction()
        fetcher_ctx = Context(
            user=ctx.user,
            request=ctx.request,
            environment=ctx.environment
        )

        snapshot_date = params.get("snapshot_date")

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
        fetch_result["tx_ctx"] = result["tx_ctx"]
        return fetch_result

    @IntFieldChecker("total_issues", min_value=0, desc="Результат _postHandleAspect: общее количество загруженных задач")
    @IntFieldChecker("pages", min_value=0, desc="Результат _postHandleAspect: количество обработанных страниц")
    @InstanceOfChecker("details", expected_class=dict, desc="Результат _postHandleAspect: детальная статистика по сейверам")
    def _postHandleAspect(self, ctx: Context, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Фиксирует транзакцию и возвращает только статистику загрузки."""
        for mgr in result.get("managers", []):
            mgr.commit()
        # Убираем служебные ключи, но сохраняем details
        result.pop("managers", None)
        result.pop("savers", None)
        result.pop("tx_ctx", None)
        # result уже содержит total_issues, pages, details
        return result
    
    def _onErrorAspect(self, ctx: Context, params: Dict[str, Any], result: Dict[str, Any], error: Exception) -> None:
        """При ошибке откатывает все открытые соединения PostgreSQL."""
        for mgr in result.get("managers", []):
            try:
                mgr.rollback()
            except Exception:
                pass
        logger.error(f"Ошибка в BulkYouTrackIssueToPostgresAction: {error}")