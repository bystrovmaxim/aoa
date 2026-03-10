from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

from ActionEngine import (
    BaseTransactionAction,
    requires_connection_type,
    TransactionContext,
    Context,
    StringFieldChecker,
    IntFieldChecker,
    HandleException)

import psycopg2
from .FetchIssueAllActivitiesAction import FetchIssueAllActivitiesAction

logger = logging.getLogger(__name__)


@requires_connection_type(psycopg2.extensions.connection)
@StringFieldChecker("base_url", required=True)
@StringFieldChecker("token", required=True)
@StringFieldChecker("issue_id", required=True)
@StringFieldChecker("status_field_name", required=True, not_empty=True)
@IntFieldChecker("last_timestamp_ms", required=True, desc="Максимальный timestamp уже обработанных событий (мс)")
class UpdateSingleIssueHistoryAction(BaseTransactionAction):
    """
    Обновляет историю статусов для одной задачи.
    Получает активности указанного поля статуса через FetchIssueAllActivitiesAction,
    начиная с last_timestamp_ms (если передан) или с максимальной даты из таблицы + 1 мс.
    Сохраняет новые события в issues_status_history.
    После обработки (даже если не было новых событий) обновляет поле last_activity_processed
    в таблице issues на текущее серверное время.
    Возвращает количество вставленных событий и количество полученных событий статуса.
    """

    INITIAL_STATUS = "Ожидание"

    def _add_initial_status_if_needed(self, events: List[Dict], issue_id: str, created: Optional[datetime]) -> List[Dict]:
        """Добавляет эмулированное начальное событие, если его нет."""
        if any(e["new_status"] == self.INITIAL_STATUS for e in events):
            return events
        if events:
            first = events[0]
            emulated = {
                "issue_id": issue_id,
                "timestamp": first["timestamp"],
                "author_login": first["author_login"],
                "old_status": None,
                "new_status": self.INITIAL_STATUS,
            }
            events.insert(0, emulated)
            logger.info(f"Добавлено эмулированное '{self.INITIAL_STATUS}' для {issue_id} на основе первого события")
            return events
        # Нет событий – эмуляция по времени создания задачи
        if created is None:
            created = datetime.utcnow()
        emulated = {
            "issue_id": issue_id,
            "timestamp": created,
            "author_login": None,
            "old_status": None,
            "new_status": self.INITIAL_STATUS,
        }
        events.append(emulated)
        logger.info(f"Добавлено эмулированное '{self.INITIAL_STATUS}' для {issue_id} по времени создания")
        return events

    @IntFieldChecker("inserted", min_value=0)
    @IntFieldChecker("events_fetched", min_value=0)
    def _handleAspect(self, ctx: TransactionContext, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        conn = ctx.connection
        cur = conn.cursor()

        base_url = params["base_url"]
        token = params["token"]
        issue_id = params["issue_id"]
        status_field = params["status_field_name"]
        last_timestamp_ms = params.get("last_timestamp_ms")

        # Проверяем существование задачи в issues и получаем дату создания
        cur.execute("SELECT created FROM youtrack.issues WHERE id = %s", (issue_id,))
        row = cur.fetchone()
        if not row:
            logger.warning(f"Задача {issue_id} отсутствует в issues. Обновление пропущено.")
            return {"inserted": 0, "events_fetched": 0, "skipped": True}
        created = row[0]

        from_ms = last_timestamp_ms
        
        # Получаем активности через FetchIssueAllActivitiesAction
        fetch_action = FetchIssueAllActivitiesAction()
        simple_ctx = Context(user=ctx.user, request=ctx.request, environment=ctx.environment)
        fetch_params = {
            "base_url": base_url,
            "token": token,
            "issue_id": issue_id,
            "from_timestamp_ms": from_ms,
            "categories": ["CustomFieldCategory"],
            "custom_field_names": [status_field],
        }
        try:
            fetch_result = fetch_action.run(simple_ctx, fetch_params)
            activities = fetch_result.get("activities", [])
        except Exception as e:
            raise HandleException(f"Ошибка получения активностей {issue_id}: {e}")

        # Преобразуем активности в события статуса, используя нормализованные added_value/removed_value
        events = []
        for act in activities:
            if act.get("type") != "CustomFieldActivityItem":
                continue
            ts = act.get("timestamp")
            if not ts:
                continue
            dt = datetime.utcfromtimestamp(ts / 1000.0)
            author = act.get("author", {})
            author_login = author.get("login")
            old_val = act.get("removed_value")
            new_val = act.get("added_value")
            events.append({
                "issue_id": issue_id,
                "timestamp": dt,
                "author_login": author_login,
                "old_status": old_val,
                "new_status": new_val,
            })
        events.sort(key=lambda e: e["timestamp"])
        events_fetched = len(events)

        # Эмуляция начального события, если это первая загрузка (from_ms == 0) и нет событий
        if from_ms == 0 and not events:
            events = self._add_initial_status_if_needed(events, issue_id, created)
            events_fetched = len(events)

        # Если событий нет, всё равно обновляем last_activity_processed
        if not events:
            logger.info(f"Для задачи {issue_id} нет новых событий статуса")
            cur.execute(
                "UPDATE youtrack.issues SET last_activity_processed = NOW() WHERE id = %s",
                (issue_id,)
            )
            return {"inserted": 0, "events_fetched": events_fetched}

        # Вставляем события
        inserted = 0
        for event in events:
            cur.execute(
                """
                INSERT INTO youtrack.issues_status_history
                    (issue_id, timestamp, author_login, old_status, new_status)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (issue_id, timestamp) DO NOTHING
                """,
                (event["issue_id"], event["timestamp"], event["author_login"],
                 event["old_status"], event["new_status"])
            )
            if cur.rowcount > 0:
                inserted += 1

        # Обновляем last_activity_processed
        cur.execute(
            "UPDATE youtrack.issues SET last_activity_processed = NOW() WHERE id = %s",
            (issue_id,)
        )

        logger.info(f"Задача {issue_id}: вставлено {inserted} из {events_fetched}")
        return {"inserted": inserted, "events_fetched": events_fetched}