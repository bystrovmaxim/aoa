# APP/DeleteSnapshotPostgressAction.py
from typing import List
from datetime import date
import logging

from psycopg2 import sql
import psycopg2

from ActionEngine import (
    TransactionContext,
    IntFieldChecker,
    InstanceOfChecker,
    StringFieldChecker,
    requires_connection_type,
    BaseTransactionAction)

logger = logging.getLogger(__name__)


@requires_connection_type(psycopg2.extensions.connection, desc="Требуется соединение с PostgreSQL")
@StringFieldChecker("snapshot_date", required=True, not_empty=True, desc="Входной параметр: дата снимка (строка YYYY-MM-DD)")
@InstanceOfChecker("tables", expected_class=list, required=True, desc="Входной параметр: список имён таблиц для очистки")
class DeleteSnapshotProgressAction(BaseTransactionAction):
    """
    Удаляет все записи с заданной snapshot_date из указанных таблиц.
    После удаления снимков также удаляет из таблицы issues те записи,
    у которых не осталось ни одной записи ни в одной из таблиц расширений
    (сирот). Это гарантирует целостность данных.
    """

    @IntFieldChecker("deleted_total", min_value=0, desc="Результат: общее количество удалённых записей")
    @IntFieldChecker("orphans_deleted", min_value=0, desc="Результат: количество удалённых сирот из issues")
    def _handleAspect(self, ctx: TransactionContext, params: dict, result: dict) -> dict:
        conn = ctx.connection
        cur = conn.cursor()
        snapshot_date_str = params["snapshot_date"]
        tables = params["tables"]
        schema = params.get("schema", "youtrack")  # можно передать, если нужно

        try:
            snapshot_date = date.fromisoformat(snapshot_date_str)
        except ValueError:
            raise ValueError(f"Неверный формат даты: {snapshot_date_str}")

        total_deleted = 0
        for table in tables:
            delete_sql = sql.SQL("DELETE FROM {}.{} WHERE snapshot_date = %s").format(
                sql.Identifier(schema),
                sql.Identifier(table)
            )
            cur.execute(delete_sql, (snapshot_date,))
            deleted_in_table = cur.rowcount
            total_deleted += deleted_in_table
            logger.info(f"Удалено {deleted_in_table} записей из таблицы {schema}.{table} за {snapshot_date}")

        # Удаляем сирот из issues (записи, которые не имеют связей ни в одной из таблиц расширений)
        # Строим динамическое условие: NOT EXISTS для каждой таблицы расширений
        conditions = []
        for table in tables:
            conditions.append(
                sql.SQL("NOT EXISTS (SELECT 1 FROM {}.{} t WHERE t.key = i.key)").format(
                    sql.Identifier(schema),
                    sql.Identifier(table)
                )
            )
        # Объединяем условия через AND
        where_clause = sql.SQL(" AND ").join(conditions)

        delete_orphans_sql = sql.SQL("DELETE FROM {}.issues i WHERE {}").format(
            sql.Identifier(schema),
            where_clause
        )
        cur.execute(delete_orphans_sql)
        orphans_deleted = cur.rowcount
        if orphans_deleted > 0:
            logger.info(f"Удалено {orphans_deleted} сирот из таблицы {schema}.issues")

        return {"deleted_total": total_deleted, "orphans_deleted": orphans_deleted}