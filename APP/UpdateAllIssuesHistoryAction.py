# APP/UpdateHistoryByGlobalDateAction.py
import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from collections import defaultdict

from ActionEngine import (
    BaseSimpleAction,
    Context,
    TransactionContext,
    CheckRoles,
    IntFieldChecker,
    InstanceOfChecker,
    StringFieldChecker,
    PostgresConnectionManager,
    HandleException
)

from .FindIssuesNeedingHistoryUpdateAction import FindIssuesNeedingHistoryUpdateAction
from .FetchIssueStatusHistoryAction import FetchIssueStatusHistoryAction

logger = logging.getLogger(__name__)

# Дата по умолчанию, если история пуста (1900-01-01)
DEFAULT_START_DATE = datetime(1900, 1, 1)


@CheckRoles(CheckRoles.ANY, desc="Доступно аутентифицированным пользователям")
@StringFieldChecker("base_url", required=True, desc="URL YouTrack")
@StringFieldChecker("token", required=True, desc="Токен доступа")
@IntFieldChecker("page_size", required=True, min_value=1, max_value=10000, desc="Размер страницы для пагинации")
@InstanceOfChecker("card_types", expected_class=list, required=False, desc="Список типов карточек для фильтрации (если задан, не должен быть пустым)")
@StringFieldChecker("pg_host", required=True, desc="Хост PostgreSQL")
@IntFieldChecker("pg_port", required=True, desc="Порт PostgreSQL")
@StringFieldChecker("pg_db", required=True, desc="Имя БД")
@StringFieldChecker("pg_user", required=True, desc="Пользователь PostgreSQL")
@StringFieldChecker("pg_password", required=True, desc="Пароль PostgreSQL")
class UpdateAllIssuesHistoryAction(BaseSimpleAction):
    """
    Обновляет историю статусов для задач, которые изменились после глобальной даты
    последнего события (с учётом фильтра по типам карточек).
    Если передан card_types, он должен быть непустым списком.
    """

    @InstanceOfChecker("managers", expected_class=list, desc="Внутреннее")
    @InstanceOfChecker("tx_ctx", expected_class=TransactionContext, desc="Внутреннее")
    def _preHandleAspect(self, ctx: Context, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        # Дополнительная валидация: если card_types передан, он не должен быть пустым
        card_types = params.get("card_types")
        if card_types is not None and not card_types:
            raise ValueError("Параметр card_types, если задан, не может быть пустым списком")

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

    def _get_global_last_timestamp(self, cur, card_types: Optional[List[str]]) -> datetime:
        """
        Возвращает максимальный timestamp из таблицы истории статусов.
        Если заданы card_types, учитываются только задачи этих типов.
        """
        if card_types:
            placeholders = ','.join(['%s'] * len(card_types))
            query = f"""
                SELECT MAX(h.timestamp)
                FROM youtrack.issue_status_history h
                JOIN youtrack.issues i ON h.key = i.key
                WHERE i.type_issue IN ({placeholders})
            """
            cur.execute(query, card_types)
        else:
            cur.execute("SELECT MAX(timestamp) FROM youtrack.issue_status_history")
        row = cur.fetchone()
        if row and row[0]:
            return row[0]
        logger.info("Таблица истории пуста для заданных типов, используем дату 1900-01-01")
        return DEFAULT_START_DATE

    @IntFieldChecker("total_issues_processed", min_value=0, desc="Количество успешно обработанных задач")
    @IntFieldChecker("total_events_inserted", min_value=0, desc="Количество добавленных событий")
    @InstanceOfChecker("details_by_type", expected_class=dict, desc="Детальная статистика по типам")
    def _handleAspect(self, ctx: Context, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        tx_ctx = result["tx_ctx"]
        conn = tx_ctx.connection
        cur = conn.cursor()

        # 1. Получаем глобальную дату последнего события (с учётом типов)
        card_types = params.get("card_types")
        last_global = self._get_global_last_timestamp(cur, card_types)

        # 2. Получаем из YouTrack список задач, обновлённых после этой даты
        find_action = FindIssuesNeedingHistoryUpdateAction()
        find_params = {
            "base_url": params["base_url"],
            "token": params["token"],
            "page_size": params["page_size"],
            "since_timestamp_ms": int(last_global.timestamp() * 1000)
        }
        try:
            find_result = find_action.run(ctx, find_params)
            issue_keys = find_result.get("issue_keys", [])
        except Exception as e:
            raise HandleException(f"Не удалось получить список изменившихся задач: {e}")

        # 3. Фильтруем ключи по типам, если они заданы
        if card_types and issue_keys:
            placeholders_keys = ','.join(['%s'] * len(issue_keys))
            placeholders_types = ','.join(['%s'] * len(card_types))
            query = f"""
                SELECT key
                FROM youtrack.issues
                WHERE key IN ({placeholders_keys})
                  AND type_issue IN ({placeholders_types})
            """
            cur.execute(query, issue_keys + card_types)
            filtered_keys = [row[0] for row in cur.fetchall()]
            logger.info(f"После фильтрации по типам осталось {len(filtered_keys)} задач из {len(issue_keys)}")
            issue_keys = filtered_keys

        if not issue_keys:
            logger.info("Нет задач для обновления")
            return {
                "total_issues_processed": 0,
                "total_events_inserted": 0,
                "details_by_type": {}
            }

        # 4. Получаем типы этих задач (для статистики)
        placeholders = ','.join(['%s'] * len(issue_keys))
        cur.execute(f"SELECT key, type_issue FROM youtrack.issues WHERE key IN ({placeholders})", issue_keys)
        key_to_type = {row[0]: row[1] for row in cur.fetchall()}

        # 5. Обрабатываем каждую задачу
        fetch_action = FetchIssueStatusHistoryAction()
        total_events = 0
        processed_issues = 0
        stats_by_type = defaultdict(lambda: {"processed": 0, "inserted": 0})
        total = len(issue_keys)

        for idx, key in enumerate(issue_keys, 1):
            start_time = time.time()
            from_ms = int(last_global.timestamp() * 1000)

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
        logger.error(f"Ошибка в UpdateHistoryByGlobalDateAction: {error}")
        for mgr in result.get("managers", []):
            logger.debug("Откат транзакции")
            mgr.rollback()