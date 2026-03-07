# APP/FindIssuesNeedingHistoryUpdateAction.py
from typing import List, Dict, Any
import logging

import psycopg2
from psycopg2 import sql

from ActionEngine import (
    BaseTransactionAction,
    requires_connection_type,
    TransactionContext,
    InstanceOfChecker,
    HandleException)

logger = logging.getLogger(__name__)


@requires_connection_type(psycopg2.extensions.connection, desc="Требуется соединение с PostgreSQL")
class FindIssuesNeedingHistoryUpdateAction(BaseTransactionAction):
    """
    Находит ключи задач, для которых необходимо обновить историю статусов.

    Логика:
        Для каждой задачи вычисляем максимальное время последнего изменения (updated)
        из всех таблиц расширений (user_tech_stories, taskitems). Если у задачи нет
        записей в истории статусов, она попадает в список. Иначе сравниваем максимальный
        updated с максимальным timestamp в истории. Если updated > max_timestamp, задача
        требует обновления.

    Возвращает список ключей в поле "issue_keys".
    """

    @InstanceOfChecker("issue_keys", expected_class=list, desc="Список ключей задач, требующих обновления истории")
    def _handleAspect(self, ctx: TransactionContext, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        conn = ctx.connection
        cur = conn.cursor()

        # Находим максимальный updated для каждой задачи из всех таблиц расширений
        # Предполагаем, что все таблицы расширений имеют поле updated и key
        query = sql.SQL("""
            WITH max_updated AS (
                SELECT key, MAX(updated) as last_updated
                FROM (
                    SELECT key, updated FROM youtrack.user_tech_stories
                    UNION ALL
                    SELECT key, updated FROM youtrack.taskitems
                ) all_updates
                GROUP BY key
            )
            SELECT mu.key
            FROM max_updated mu
            LEFT JOIN (
                SELECT key, MAX(timestamp) as last_event
                FROM youtrack.issue_status_history
                GROUP BY key
            ) h ON mu.key = h.key
            WHERE
                (h.last_event IS NULL) OR
                (mu.last_updated > h.last_event)
        """)
        cur.execute(query)
        rows = cur.fetchall()
        issue_keys = [row[0] for row in rows]
        logger.debug(f"Найдено {len(issue_keys)} задач для обновления истории")
        return {"issue_keys": issue_keys}