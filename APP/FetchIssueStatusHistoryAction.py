# APP/FetchIssueStatusHistoryAction.py
from typing import Any, Dict, List, Optional
from datetime import datetime
import requests
import logging
import re
import json

from ActionEngine import (
    BaseSimpleAction,
    Context,
    StringFieldChecker,
    IntFieldChecker,
    HandleException)

logger = logging.getLogger(__name__)


@StringFieldChecker("base_url", required=True, desc="URL YouTrack")
@StringFieldChecker("token", required=True, desc="Токен доступа")
@StringFieldChecker("issue_id", required=True, desc="Внутренний ID задачи в YouTrack")
@IntFieldChecker("from_timestamp_ms", required=False, desc="Начальная дата в миллисекундах (опционально)")
class FetchIssueStatusHistoryAction(BaseSimpleAction):
    """
    Получает историю изменений статуса задачи из YouTrack по её внутреннему ID.
    Возвращает список событий, каждое содержит:
        - issue_id (str)
        - timestamp (datetime)
        - author_login (str or None)
        - old_status (str or None)
        - new_status (str or None)
    """

    # Расширенный набор возможных имён полей статуса
    STATUS_FIELD_NAMES = {
        "Статус задачи", "Статус истории", "State", "status", "Status",
        "_Статус задачи", "_Статус истории", "State", "Состояние"
    }

    def _ms_to_datetime(self, ms: int) -> datetime:
        return datetime.utcfromtimestamp(ms / 1000.0)

    def _fetch_activities(self, base_url: str, token: str, issue_id: str, from_ms: Optional[int]) -> List[Dict]:
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        params = {
            "fields": (
                "id,timestamp,"
                "author(login),"
                "field(id,name),"
                "targetMember,"
                "added(id,name,login,fullName,minutes,text,presentation),"
                "removed(id,name,login,fullName,minutes,text,presentation),"
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
            raise HandleException(f"Ошибка соединения для {issue_id}: {e}")

        if resp.status_code != 200:
            raise HandleException(f"HTTP {resp.status_code} для {issue_id}: {resp.text}")

        data = resp.json()
        if not isinstance(data, list):
            raise HandleException("Неожиданный формат ответа от YouTrack")

        # Логируем первые несколько активностей для отладки
        for i, act in enumerate(data[:5]):
            logger.debug(f"Activity {i}: {json.dumps(act, ensure_ascii=False)}")

        logger.debug(f"Получено {len(data)} активностей для задачи {issue_id}")
        return data

    def _extract_field_name(self, activity: Dict) -> Optional[str]:
        """Извлекает имя поля из активности."""
        # Пробуем получить из поля field
        field = activity.get("field")
        if field and isinstance(field, dict):
            return field.get("name")
        # Пробуем из targetMember
        target_member = activity.get("targetMember", "")
        if target_member:
            # Парсим как раньше
            match = re.match(r"^__CUSTOM_FIELD__[_!](.+)_\d+$", target_member)
            if match:
                return match.group(1)
        return None

    def _extract_status_value(self, data) -> Optional[str]:
        if data is None:
            return None
        if isinstance(data, list):
            if len(data) > 0 and isinstance(data[0], dict):
                # Пробуем name, потом value, потом presentation
                return data[0].get("name") or data[0].get("value") or data[0].get("presentation")
            return None
        if isinstance(data, dict):
            return data.get("name") or data.get("value") or data.get("presentation")
        if isinstance(data, str):
            return data
        return str(data)

    def _extract_status_events(self, activities: List[Dict], issue_id: str) -> List[Dict]:
        events = []
        for act in activities:
            field_name = self._extract_field_name(act)
            if not field_name or field_name not in self.STATUS_FIELD_NAMES:
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
                "issue_id": issue_id,
                "timestamp": dt,
                "author_login": author_login,
                "old_status": old_val,
                "new_status": new_val,
            })
        events.sort(key=lambda e: e["timestamp"])
        logger.debug(f"Из них событий изменения статуса: {len(events)}")
        return events

    @IntFieldChecker("count", min_value=0, desc="Количество полученных событий")
    def _handleAspect(self, ctx: Context, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        base_url = params["base_url"]
        token = params["token"]
        issue_id = params["issue_id"]
        from_ms = params.get("from_timestamp_ms")

        activities = self._fetch_activities(base_url, token, issue_id, from_ms)
        events = self._extract_status_events(activities, issue_id)

        return {
            "events": events,
            "count": len(events)
        }