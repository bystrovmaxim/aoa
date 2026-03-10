# APP/YouTrackTasksIssuesPostgresSaver.py
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


@requires_connection_type(psycopg2.extensions.connection)
@InstanceOfChecker("headers", expected_class=list, required=True)
@InstanceOfChecker("rows", expected_class=list, required=True)
@StringFieldChecker("snapshot_date", required=True, not_empty=True)
class YouTrackTasksIssuesPostgresSaver(BaseTransactionAction, IYouTrackIssuesSaver):
    """
    Сохраняет снимки задач в таблицу taskitems.
    Перед вставкой обновляет/создаёт запись в issues по полю id,
    включая поле last_update (дата последнего изменения задачи из YouTrack).
    """

    TABLE_NAME = "taskitems"
    CLASS_ISSUE = "taskitems"

    COMMON_FIELDS = [
        "title", "description", "created", "parent_key", "type_issue",
        "project_id", "project_name"
    ]

    SPECIFIC_FIELDS = [
        "updated", "date_resolved", "assignee_login", "assignee_name", "assignee_fullname",
        "tester_login", "tester_name", "tester_fullname", "status", "story_points",
        "priority", "subcomponent", "sprints", "imported_at"
    ]

    INSERT_COLUMNS = ["issue_id", "key", "snapshot_date"] + COMMON_FIELDS + SPECIFIC_FIELDS

    def __init__(self):
        super().__init__()

    def _ensure_issue_record(self, cur, row_dict: Dict[str, Any]) -> None:
        issue_id = row_dict.get("id")
        if not issue_id:
            raise HandleException("Отсутствует поле 'id' в данных (нельзя создать запись в issues)")

        issue_values = {
            "id": issue_id,
            "key": row_dict.get("key"),
            "title": row_dict.get("title"),
            "description": row_dict.get("description"),
            "created": row_dict.get("created"),
            "parent_key": row_dict.get("parent_key"),
            "type_issue": row_dict.get("type"),
            "class_issue": self.CLASS_ISSUE,
            "project_id": row_dict.get("project_id"),
            "project_name": row_dict.get("project_name"),
            "last_update": row_dict.get("updated")   # дата последнего изменения задачи в YouTrack
        }

        insert_sql = sql.SQL("""
            INSERT INTO youtrack.issues (
                id, key, title, description, created, parent_key, type_issue, class_issue,
                project_id, project_name, last_update
            ) VALUES (
                %(id)s, %(key)s, %(title)s, %(description)s, %(created)s, %(parent_key)s,
                %(type_issue)s, %(class_issue)s, %(project_id)s, %(project_name)s, %(last_update)s
            )
            ON CONFLICT (id) DO UPDATE SET
                key = EXCLUDED.key,
                title = EXCLUDED.title,
                description = EXCLUDED.description,
                created = EXCLUDED.created,
                parent_key = EXCLUDED.parent_key,
                type_issue = EXCLUDED.type_issue,
                class_issue = EXCLUDED.class_issue,
                project_id = EXCLUDED.project_id,
                project_name = EXCLUDED.project_name,
                last_update = EXCLUDED.last_update
        """)
        cur.execute(insert_sql, issue_values)

    def _handleAspect(self, ctx: TransactionContext, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
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
            rows_dicts = [dict(zip(headers, row)) for row in rows]

            valid_rows_dicts = []
            for row_dict in rows_dicts:
                row_type = row_dict.get("type", "unknown")
                if not row_dict.get("id") or not row_dict.get("key"):
                    logger.warning(f"Пропущена строка (отсутствует id или key) в {self.TABLE_NAME}: {json.dumps(row_dict, ensure_ascii=False, default=str)}")
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

            # 1. Обновляем/создаём записи в issues
            for row_dict in valid_rows_dicts:
                self._ensure_issue_record(cur, row_dict)

            # 2. Вставка в taskitems
            values_list = []
            for row_dict in valid_rows_dicts:
                values = [
                    row_dict["id"],
                    row_dict["key"],
                    snapshot_date,
                    row_dict.get("title"),
                    row_dict.get("description"),
                    row_dict.get("created"),
                    row_dict.get("parent_key"),
                    row_dict.get("type"),
                    row_dict.get("project_id"),
                    row_dict.get("project_name"),
                ]
                for field in self.SPECIFIC_FIELDS:
                    values.append(row_dict.get(field))
                values_list.append(values)

                row_type = row_dict.get("type", "unknown")
                inserted_by_type[row_type] += 1

            insert_sql = sql.SQL(
                "INSERT INTO youtrack.{} ({}) VALUES ({}) ON CONFLICT (issue_id, snapshot_date) DO UPDATE SET {}"
            ).format(
                sql.Identifier(self.TABLE_NAME),
                sql.SQL(', ').join(map(sql.Identifier, self.INSERT_COLUMNS)),
                sql.SQL(', ').join([sql.Placeholder()] * len(self.INSERT_COLUMNS)),
                sql.SQL(', ').join(
                    sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(col), sql.Identifier(col))
                    for col in self.COMMON_FIELDS + self.SPECIFIC_FIELDS
                )
            )

            cur.executemany(insert_sql, values_list)
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