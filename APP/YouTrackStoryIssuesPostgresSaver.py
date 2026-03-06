# APP/YouTrackStoryIssuesPostgresSaver.py
from typing import Any, Dict, List
from datetime import date
import logging
import json
from collections import defaultdict

from psycopg2 import sql
import psycopg2

from ActionEngine import (
    BaseTransactionAction,
    requires_connection_type,
    TransactionContext,
    InstanceOfChecker,
    StringFieldChecker,
    IntFieldChecker,
    HandleException)

from .IYouTrackIssuesSaver import IYouTrackIssuesSaver

logger = logging.getLogger(__name__)


@requires_connection_type(psycopg2.extensions.connection, desc="Требуется соединение с PostgreSQL")
@InstanceOfChecker("headers", expected_class=list, required=True, desc="Входной параметр: заголовки столбцов (список)")
@InstanceOfChecker("rows", expected_class=list, required=True, desc="Входной параметр: строки данных (список списков)")
@StringFieldChecker("snapshot_date", required=True, not_empty=True, desc="Входной параметр: дата снимка (строка YYYY-MM-DD)")
class YouTrackStoryIssuesPostgresSaver(BaseTransactionAction, IYouTrackIssuesSaver):
    """
    Сохраняет снимки историй (пользовательские и технические) в таблицу user_tech_stories.
    Перед вставкой проверяет наличие задачи в таблице issues и при необходимости создаёт/обновляет запись.
    Вставляет только специфичные для историй поля (общие поля хранятся в issues).
    Параметры должны содержать 'headers', 'rows' и 'snapshot_date'.
    При конфликте (key, snapshot_date) выполняет обновление всех полей.

    Возвращает детальную статистику:
        inserted (int): общее количество вставленных/обновлённых строк
        inserted_by_type (dict): количество по каждому типу задачи
        skipped (int): количество пропущенных строк (без key)
        skipped_by_type (dict): количество пропущенных по каждому типу
    """

    TABLE_NAME = "user_tech_stories"
    CLASS_ISSUE = "user_tech_stories"

    SPECIFIC_FIELDS = [
        "updated", "date_resolved", "assignee_login", "assignee_name", "assignee_fullname",
        "status", "plan_start", "plan_finish", "fact_forecast_start", "fact_forecast_finish",
        "customer", "sprints", "imported_at"
    ]

    def __init__(self):
        super().__init__()

    def _ensure_issue_record(self, cur, row_dict: Dict[str, Any]) -> None:
        key = row_dict.get("key")
        if not key:
            raise HandleException("Отсутствует поле 'key' в данных (нельзя создать запись в issues)")

        issue_values = {
            "key": key,
            "id": row_dict.get("id"),
            "title": row_dict.get("title"),
            "description": row_dict.get("description"),
            "created": row_dict.get("created"),
            "parent_key": row_dict.get("parent_key"),
            "type_issue": row_dict.get("type"),
            "class_issue": self.CLASS_ISSUE
        }

        insert_sql = sql.SQL("""
            INSERT INTO youtrack.issues (key, id, title, description, created, parent_key, type_issue, class_issue)
            VALUES (%(key)s, %(id)s, %(title)s, %(description)s, %(created)s, %(parent_key)s, %(type_issue)s, %(class_issue)s)
            ON CONFLICT (key) DO UPDATE SET
                id = EXCLUDED.id,
                title = EXCLUDED.title,
                description = EXCLUDED.description,
                created = EXCLUDED.created,
                parent_key = EXCLUDED.parent_key,
                type_issue = EXCLUDED.type_issue,
                class_issue = EXCLUDED.class_issue
        """)
        cur.execute(insert_sql, issue_values)

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

        # Инициализируем счётчики
        inserted_by_type = defaultdict(int)
        skipped_by_type = defaultdict(int)
        inserted_total = 0
        skipped_total = 0

        if not rows:
            logger.info(f"Нет данных для вставки в {self.TABLE_NAME} за {snapshot_date}")
            return {
                "inserted": 0,
                "inserted_by_type": {},
                "skipped": 0,
                "skipped_by_type": {}
            }

        cur = conn.cursor()

        try:
            # Преобразуем строки в список словарей
            rows_dicts = [dict(zip(headers, row)) for row in rows]

            # Разделяем на валидные (с key) и невалидные
            valid_rows_dicts = []
            for row_dict in rows_dicts:
                row_type = row_dict.get("type", "unknown")
                if not row_dict.get("key"):
                    # Логируем пропущенную строку подробно
                    logger.warning(f"Пропущена строка (отсутствует key) в {self.TABLE_NAME}: {json.dumps(row_dict, ensure_ascii=False, default=str)}")
                    skipped_total += 1
                    skipped_by_type[row_type] += 1
                else:
                    valid_rows_dicts.append(row_dict)

            if not valid_rows_dicts:
                logger.warning(f"Нет валидных строк для вставки в {self.TABLE_NAME}")
                return {
                    "inserted": 0,
                    "inserted_by_type": {},
                    "skipped": skipped_total,
                    "skipped_by_type": dict(skipped_by_type)
                }

            # 1. Обеспечиваем наличие записей в issues
            for row_dict in valid_rows_dicts:
                self._ensure_issue_record(cur, row_dict)

            # 2. Вставка в таблицу расширения (только специфичные поля)
            specific_headers = [h for h in headers if h in self.SPECIFIC_FIELDS]
            if not specific_headers:
                logger.warning(f"Нет специфичных полей для вставки в {self.TABLE_NAME}")
                return {
                    "inserted": 0,
                    "inserted_by_type": {},
                    "skipped": skipped_total,
                    "skipped_by_type": dict(skipped_by_type)
                }

            # Группируем валидные строки по типу для подсчёта
            for row_dict in valid_rows_dicts:
                row_type = row_dict.get("type", "unknown")
                inserted_by_type[row_type] += 1

            # Подготавливаем данные для executemany
            specific_values_list = []
            for row_dict in valid_rows_dicts:
                values = [row_dict.get(h) for h in specific_headers]
                specific_values_list.append(values + [snapshot_date, row_dict["key"]])

            columns = specific_headers + ["snapshot_date", "key"]
            insert_sql = sql.SQL(
                "INSERT INTO youtrack.{} ({}) VALUES ({}) ON CONFLICT (key, snapshot_date) DO UPDATE SET {}"
            ).format(
                sql.Identifier(self.TABLE_NAME),
                sql.SQL(', ').join(map(sql.Identifier, columns)),
                sql.SQL(', ').join([sql.Placeholder()] * len(columns)),
                sql.SQL(', ').join(
                    sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(col), sql.Identifier(col))
                    for col in specific_headers
                )
            )

            cur.executemany(insert_sql, specific_values_list)
            inserted_total = len(valid_rows_dicts)

        except Exception as e:
            raise HandleException(f"Ошибка при работе с PostgreSQL: {e}")

        logger.info(f"В {self.TABLE_NAME} за {snapshot_date}: вставлено/обновлено {inserted_total}, пропущено {skipped_total}")
        if skipped_by_type:
            logger.info(f"Пропущено по типам: {dict(skipped_by_type)}")

        return {
            "inserted": inserted_total,
            "inserted_by_type": dict(inserted_by_type),
            "skipped": skipped_total,
            "skipped_by_type": dict(skipped_by_type)
        }