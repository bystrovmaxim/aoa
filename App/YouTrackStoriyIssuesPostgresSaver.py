from typing import Any, Dict
from datetime import date
import logging

from psycopg2 import sql
import psycopg2

from ActionEngine.BaseTransactionAction import BaseTransactionAction
from ActionEngine.TransactionContext import TransactionContext
from ActionEngine.Exceptions import HandleException
from ActionEngine.requires_connection_type import requires_connection_type
from ActionEngine.InstanceOfChecker import InstanceOfChecker
from ActionEngine.StringFieldChecker import StringFieldChecker
from ActionEngine.IntFieldChecker import IntFieldChecker
from .IYouTrackIssuesSaver import IYouTrackIssuesSaver

logger = logging.getLogger(__name__)


@requires_connection_type(psycopg2.extensions.connection, description="Требуется соединение с PostgreSQL")
@InstanceOfChecker("headers", expected_class=list, required=True, description="Входной параметр: заголовки столбцов (список)")
@InstanceOfChecker("rows", expected_class=list, required=True, description="Входной параметр: строки данных (список списков)")
@StringFieldChecker("snapshot_date", required=True, not_empty=True, description="Входной параметр: дата снимка (строка YYYY-MM-DD)")
class YouTrackStoriyIssuesPostgresSaver(BaseTransactionAction, IYouTrackIssuesSaver):
    """
    Сохраняет снимки историй (пользовательские и технические) в таблицу user_tech_stories.
    Параметры должны содержать 'headers', 'rows' и 'snapshot_date'.
    При конфликте (key, snapshot_date) выполняет обновление всех полей.
    """

    TABLE_NAME = "user_tech_stories"

    def __init__(self):
        super().__init__()

    @IntFieldChecker("inserted", min_value=0, description="Результат _handleAspect: количество вставленных или обновлённых записей")
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
        snapshot_date_str = params.get("snapshot_date")

        try:
            snapshot_date = date.fromisoformat(snapshot_date_str)
        except ValueError:
            raise HandleException(f"Неверный формат snapshot_date: {snapshot_date_str}, ожидается YYYY-MM-DD")

        if not rows:
            logger.info(f"Нет данных для вставки в {self.TABLE_NAME} за {snapshot_date}")
            return {"inserted": 0}

        cur = conn.cursor()

        try:
            # Вставка с обновлением при конфликте
            columns = headers + ["snapshot_date"]
            values_list = [row + [snapshot_date] for row in rows]

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

        logger.info(f"Вставлено/обновлено {len(rows)} записей в {self.TABLE_NAME} за {snapshot_date}")
        return {"inserted": len(rows)}