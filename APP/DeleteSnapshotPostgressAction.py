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
    Таблицы должны находиться в схеме, переданной через контекст? 
    Но схема известна только на уровне серверного действия, поэтому будем передавать её как параметр.
    """
    
    @IntFieldChecker("deleted_total", min_value=0, desc="Результат: общее количество удалённых записей")
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
            total_deleted += cur.rowcount
            logger.info(f"Удалено {cur.rowcount} записей из таблицы {schema}.{table} за {snapshot_date}")

        return {"deleted_total": total_deleted}