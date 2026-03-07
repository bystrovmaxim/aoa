# APP/UpdateAllIssuesHistoryAction.py
import logging
import time
from collections import defaultdict
from typing import Dict, Any

from ActionEngine import (
    BaseSimpleAction,
    Context,
    TransactionContext,
    CheckRoles,
    IntFieldChecker,
    InstanceOfChecker,
    StringFieldChecker,
    PostgresConnectionManager
)

from .FindIssuesNeedingHistoryUpdateAction import FindIssuesNeedingHistoryUpdateAction
from .FetchIssueStatusHistoryAction import FetchIssueStatusHistoryAction

logger = logging.getLogger(__name__)


@CheckRoles(CheckRoles.ANY, desc="Доступно аутентифицированным пользователям")
@StringFieldChecker("base_url", required=True, desc="URL YouTrack")
@StringFieldChecker("token", required=True, desc="Токен доступа")
@StringFieldChecker("pg_host", required=True, desc="Хост PostgreSQL")
@IntFieldChecker("pg_port", required=True, desc="Порт PostgreSQL")
@StringFieldChecker("pg_db", required=True, desc="Имя БД")
@StringFieldChecker("pg_user", required=True, desc="Пользователь PostgreSQL")
@StringFieldChecker("pg_password", required=True, desc="Пароль PostgreSQL")
class UpdateAllIssuesHistoryAction(BaseSimpleAction):
    """
    Координатор обновления истории статусов для всех задач, которые изменились.
    Для каждой задачи выводит одну строку результата (✅ успех / ❌ ошибка).
    Возвращает статистику по типам задач.
    """

    @InstanceOfChecker("managers", expected_class=list, desc="Внутреннее")
    @InstanceOfChecker("tx_ctx", expected_class=TransactionContext, desc="Внутреннее")
    def _preHandleAspect(self, ctx: Context, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        db_params = {
            "host": params["pg_host"],
            "port": params["pg_port"],
            "dbname": params["pg_db"],
            "user": params["pg_user"],
            "password": params["pg_password"],
        }
        logger.debug("Открытие соединения с PostgreSQL")
        mgr = PostgresConnectionManager(db_params)
        mgr.open()
        tx_ctx = TransactionContext(
            user=ctx.user,
            request=ctx.request,
            environment=ctx.environment,
            connection=mgr.connection
        )
        return {"managers": [mgr], "tx_ctx": tx_ctx}

    @IntFieldChecker("total_issues_processed", min_value=0, desc="Количество успешно обработанных задач")
    @IntFieldChecker("total_events_inserted", min_value=0, desc="Количество добавленных событий")
    @InstanceOfChecker("details_by_type", expected_class=dict, desc="Детальная статистика по типам")
    def _handleAspect(self, ctx: Context, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        tx_ctx = result["tx_ctx"]
        conn = tx_ctx.connection

        # Шаг 1: найти задачи, требующие обновления
        logger.debug("Поиск задач, требующих обновления истории статусов")
        find_action = FindIssuesNeedingHistoryUpdateAction()
        find_result = find_action.run(tx_ctx, {})
        issue_keys = find_result.get("issue_keys", [])
        logger.debug(f"Найдено {len(issue_keys)} задач, требующих обновления")

        if not issue_keys:
            logger.debug("Нет задач для обновления")
            return {
                "total_issues_processed": 0,
                "total_events_inserted": 0,
                "details_by_type": {}
            }

        # Шаг 2: получить типы этих задач одним запросом
        cur = conn.cursor()
        placeholders = ','.join(['%s'] * len(issue_keys))
        cur.execute(f"SELECT key, type_issue FROM youtrack.issues WHERE key IN ({placeholders})", issue_keys)
        key_to_type = {row[0]: row[1] for row in cur.fetchall()}

        # Шаг 3: для каждого ключа обработать историю
        fetch_action = FetchIssueStatusHistoryAction()
        total_events = 0
        processed_issues = 0
        stats_by_type = defaultdict(lambda: {"processed": 0, "inserted": 0})

        total = len(issue_keys)
        for idx, key in enumerate(issue_keys, 1):
            start_time = time.time()

            # Получаем максимальный timestamp из истории для этой задачи
            cur.execute("SELECT MAX(timestamp) FROM youtrack.issue_status_history WHERE key = %s", (key,))
            row = cur.fetchone()
            max_ts = row[0]
            from_ms = None
            if max_ts:
                from_ms = int(max_ts.timestamp() * 1000)

            fetch_params = {
                "base_url": params["base_url"],
                "token": params["token"],
                "issue_id": key,
                "from_timestamp_ms": from_ms
            }
            try:
                fetch_result = fetch_action.run(tx_ctx, fetch_params)
                inserted = fetch_result.get("inserted", 0)
                total_events += inserted
                processed_issues += 1
                issue_type = key_to_type.get(key, "unknown")
                stats_by_type[issue_type]["processed"] += 1
                stats_by_type[issue_type]["inserted"] += inserted
                elapsed = time.time() - start_time
                print(f"✅ [{idx}/{total}] {key}: вставлено {inserted} событий ({elapsed:.1f}с)")
            except Exception as e:
                print(f"❌ [{idx}/{total}] {key}: ошибка - {e}")
                logger.error(f"Ошибка при обработке задачи {key}: {e}")

        logger.debug(f"Обработка завершена. Всего обработано задач: {processed_issues}, вставлено событий: {total_events}")
        return {
            "total_issues_processed": processed_issues,
            "total_events_inserted": total_events,
            "details_by_type": dict(stats_by_type)
        }

    @IntFieldChecker("total_issues_processed", min_value=0, desc="Количество успешно обработанных задач")
    @IntFieldChecker("total_events_inserted", min_value=0, desc="Количество добавленных событий")
    @InstanceOfChecker("details_by_type", expected_class=dict, desc="Детальная статистика по типам")
    def _postHandleAspect(self, ctx: Context, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        for mgr in result.get("managers", []):
            logger.debug("Фиксация транзакции")
            mgr.commit()
        result.pop("managers", None)
        result.pop("tx_ctx", None)
        return result

    def _onErrorAspect(self, ctx: Context, params: Dict[str, Any], result: Dict[str, Any], error: Exception) -> None:
        logger.error(f"Ошибка в UpdateAllIssuesHistoryAction: {error}")
        for mgr in result.get("managers", []):
            logger.debug("Откат транзакции из-за ошибки")
            mgr.rollback()