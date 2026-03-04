from typing import Any, Dict
from datetime import date
import logging

from psycopg2 import sql
import psycopg2

from ActionEngine.BaseTransactionAction import BaseTransactionAction
from ActionEngine.TransactionContext import TransactionContext
from ActionEngine.Exceptions import HandleException
from ActionEngine.requires_connection_type import requires_connection_type
from .IYouTrackIssuesSaver import IYouTrackIssuesSaver

logger = logging.getLogger(__name__)


@requires_connection_type(psycopg2.extensions.connection)
class YouTrackStoriyIssuesPostgresSaver(BaseTransactionAction, IYouTrackIssuesSaver):
    """
    Сохраняет снимки историй (пользовательские и технические) в таблицу user_tech_stories.
    """

    TABLE_NAME = "user_tech_stories"

    def __init__(self, snapshot_date: date):
        super().__init__()
        self.snapshot_date = snapshot_date

    def _handleAspect(
        self,
        ctx: TransactionContext,
        params: Dict[str, Any],
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        conn = ctx.connection
        if conn is None:
            raise ValueError("В контексте отсутствует открытое соединение")

        headers = params.get("headers")
        rows = params.get("rows")
        if headers is None or rows is None:
            raise ValueError("Параметры должны содержать 'headers' и 'rows'")

        if not rows:
            logger.info(f"Нет данных для вставки в {self.TABLE_NAME} за {self.snapshot_date}")
            return {"deleted": 0, "inserted": 0}

        cur = conn.cursor()
        deleted = 0

        try:
            # Удаление старых записей за эту дату
            delete_sql = sql.SQL("DELETE FROM youtrack.{} WHERE snapshot_date = %s").format(
                sql.Identifier(self.TABLE_NAME)
            )
            cur.execute(delete_sql, (self.snapshot_date,))
            deleted = cur.rowcount

            # Вставка новых
            columns = headers + ["snapshot_date"]
            values_list = [row + [self.snapshot_date] for row in rows]

            insert_sql = sql.SQL(
                "INSERT INTO youtrack.{} ({}) VALUES ({}) ON CONFLICT (key, snapshot_date) DO UPDATE SET {}"
            ).format(
                sql.Identifier(self.TABLE_NAME),
                sql.SQL(', ').join(map(sql.Identifier, columns)),
                sql.SQL(', ').join([sql.Placeholder()] * len(columns)),
                sql.SQL(', ').join(
                    sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(col), sql.Identifier(col))
                    for col in headers
                )
            )

            cur.executemany(insert_sql, values_list)

        except Exception as e:
            raise HandleException(f"Ошибка при работе с PostgreSQL: {e}")

        logger.info(f"Удалено {deleted}, вставлено {len(rows)} записей в {self.TABLE_NAME} за {self.snapshot_date}")
        return {"deleted": deleted, "inserted": len(rows)}