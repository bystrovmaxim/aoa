# APP/FetchIssueStatusHistoryAction.py (актуальная версия с эмуляцией и созданием заглушки)
from typing import Any, Dict, List, Optional
from datetime import datetime
import requests
import logging
import urllib.parse
import re

from psycopg2 import sql
import psycopg2

from ActionEngine import (
    BaseTransactionAction,
    requires_connection_type,
    TransactionContext,
    StringFieldChecker,
    IntFieldChecker,
    InstanceOfChecker,
    HandleException)

logger = logging.getLogger(__name__)


@StringFieldChecker("base_url", required=True, desc="URL YouTrack")
@StringFieldChecker("token", required=True, desc="Токен доступа")
@StringFieldChecker("issue_id", required=True, desc="Идентификатор задачи")
@IntFieldChecker("from_timestamp_ms", required=False, desc="Начальная дата в миллисекундах (опционально)")
class FetchIssueStatusHistoryAction(BaseTransactionAction):
    """
    Получает историю изменений статуса задачи из YouTrack и сохраняет
    в таблицу issue_status_history.
    При первой загрузке (from_timestamp_ms=None) автоматически добавляет
    эмулированное событие 'Ожидание', если в истории его нет.
    Если есть реальные события, эмуляция создаётся на основе первого события.
    Если реальных событий нет, эмуляция создаётся по времени создания задачи.
    """

    TARGET_MEMBER_RE = re.compile(r"^__CUSTOM_FIELD__[_!](.+)_\d+$")
    STATUS_FIELD_NAMES = {
        "Статус задачи", "Статус истории", "State", "status",
        "_Статус задачи", "_Статус истории",
    }
    INITIAL_STATUS = "Ожидание"

    def _ms_to_datetime(self, ms: int) -> datetime:
        return datetime.utcfromtimestamp(ms / 1000.0)

    def _parse_field_name_from_target_member(self, target_member: str) -> Optional[str]:
        if not target_member:
            return None
        match = self.TARGET_MEMBER_RE.match(target_member)
        if match:
            return match.group(1)
        return None

    def _fetch_activities(self, base_url: str, token: str, issue_id: str, from_ms: Optional[int]) -> List[Dict]:
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        params = {
            "fields": (
                "id,timestamp,"
                "author(login),"
                "targetMember,"
                "added(name,$type),"
                "removed(name,$type),"
                "category(id,name)"
            ),
            "categories": "CustomFieldCategory",
        }
        if from_ms is not None:
            params["start"] = from_ms

        url = f"{base_url}/api/issues/{issue_id}/activities"
        logger.debug(f"Запрос к YouTrack: {url}")
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=60)
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка соединения для {issue_id}: {e}")
            raise HandleException(f"Ошибка соединения с YouTrack: {e}")

        if resp.status_code != 200:
            logger.error(f"HTTP {resp.status_code} для {issue_id}: {resp.text}")
            raise HandleException(f"HTTP {resp.status_code}: {resp.text}")

        data = resp.json()
        if not isinstance(data, list):
            raise HandleException("Неожиданный формат ответа от YouTrack")

        logger.debug(f"Получено {len(data)} активностей для задачи {issue_id}")
        return data

    def _extract_status_value(self, data) -> Optional[str]:
        if data is None:
            return None
        if isinstance(data, list):
            if len(data) > 0 and isinstance(data[0], dict):
                return data[0].get("name")
            return None
        if isinstance(data, dict):
            return data.get("name") or data.get("value")
        return str(data)

    def _extract_status_events(self, activities: List[Dict], issue_id: str) -> List[Dict]:
        events = []
        for act in activities:
            target_member = act.get("targetMember", "")
            field_name = self._parse_field_name_from_target_member(target_member)
            if field_name not in self.STATUS_FIELD_NAMES:
                continue
            ts = act.get("timestamp")
            if not ts:
                continue
            dt = self._ms_to_datetime(ts)
            author = act.get("author", {})
            author_login = author.get("login") if isinstance(author, dict) else None
            old_val = self._extract_status_value(act.get("removed"))
            new_val = self._extract_status_value(act.get("added"))
            events.append({
                "key": issue_id,
                "timestamp": dt,
                "author_login": author_login,
                "old_status": old_val,
                "new_status": new_val,
            })
        events.sort(key=lambda e: e["timestamp"])
        logger.debug(f"Из них событий изменения статуса: {len(events)}")
        return events

    def _add_initial_status_if_needed(self, cur, events: List[Dict], issue_id: str) -> List[Dict]:
        """
        Добавляет эмулированное событие 'Ожидание', если его нет в истории.
        Если events не пуст, эмулирует на основе первого реального события.
        Если events пуст, пытается взять время создания задачи из таблицы issues.
        """
        # Если уже есть событие с нужным статусом – ничего не делаем
        if any(e["new_status"] == self.INITIAL_STATUS for e in events):
            return events

        # Если есть реальные события, эмулируем на основе самого раннего
        if events:
            first = events[0]
            emulated = {
                "key": first["key"],
                "timestamp": first["timestamp"],
                "author_login": first["author_login"],
                "old_status": None,
                "new_status": self.INITIAL_STATUS,
            }
            events.insert(0, emulated)
            logger.info(f"Добавлено эмулированное событие '{self.INITIAL_STATUS}' для задачи {first['key']} на основе первого события")
            return events

        # Если реальных событий нет, пробуем создать эмуляцию по времени создания задачи
        cur.execute("SELECT created FROM youtrack.issues WHERE key = %s", (issue_id,))
        row = cur.fetchone()
        if row and row[0]:
            created = row[0]
            emulated = {
                "key": issue_id,
                "timestamp": created,
                "author_login": None,
                "old_status": None,
                "new_status": self.INITIAL_STATUS,
            }
            events.append(emulated)
            logger.info(f"Добавлено эмулированное событие '{self.INITIAL_STATUS}' для задачи {issue_id} по времени создания")
        else:
            logger.warning(f"Не удалось создать эмуляцию для задачи {issue_id}: отсутствует дата создания")
        return events

    @IntFieldChecker("inserted", min_value=0, desc="Количество вставленных записей")
    def _handleAspect(self, ctx: TransactionContext, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        conn = ctx.connection
        cur = conn.cursor()

        base_url = params["base_url"]
        token = params["token"]
        issue_id = params["issue_id"]
        from_ms = params.get("from_timestamp_ms")

        # Убеждаемся, что задача существует в issues (создаём заглушку при необходимости)
        cur.execute("SELECT 1 FROM youtrack.issues WHERE key = %s", (issue_id,))
        if not cur.fetchone():
            logger.warning(f"Задача {issue_id} отсутствует в issues. Создаём запись-заглушку.")
            cur.execute("""
                INSERT INTO youtrack.issues (key, id, title, description, created, parent_key, type_issue, class_issue)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (issue_id, None, None, None, None, None, None, 'unknown'))

        activities = self._fetch_activities(base_url, token, issue_id, from_ms)
        events = self._extract_status_events(activities, issue_id)

        # Эмуляцию добавляем только при полной загрузке (from_ms is None)
        if from_ms is None:
            events = self._add_initial_status_if_needed(cur, events, issue_id)

        if not events:
            logger.debug(f"Нет событий статуса для задачи {issue_id}")
            return {"inserted": 0}

        inserted = 0
        for event in events:
            cur.execute(
                """
                INSERT INTO youtrack.issue_status_history
                    (key, timestamp, author_login, old_status, new_status)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (key, timestamp) DO NOTHING
                """,
                (event["key"], event["timestamp"], event["author_login"], event["old_status"], event["new_status"]),
            )
            if cur.rowcount > 0:
                inserted += 1

        logger.info(f"Для задачи {issue_id} вставлено {inserted} новых записей")
        return {"inserted": inserted}