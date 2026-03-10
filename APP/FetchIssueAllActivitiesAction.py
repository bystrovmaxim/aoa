# APP/FetchIssueAllActivitiesAction.py (исправленная версия)
from typing import Any, Dict, List, Optional
from datetime import datetime
import requests
import logging

from ActionEngine import (
    BaseSimpleAction,
    Context,
    StringFieldChecker,
    IntFieldChecker,
    InstanceOfChecker,
    HandleException)

logger = logging.getLogger(__name__)


@StringFieldChecker("base_url", required=True, desc="URL YouTrack")
@StringFieldChecker("token", required=True, desc="Токен доступа")
@StringFieldChecker("issue_id", required=True, desc="Внутренний ID задачи в YouTrack")
@IntFieldChecker("from_timestamp_ms", required=False, desc="Начальная дата в миллисекундах (опционально)")
@InstanceOfChecker("categories", expected_class=list, required=False, desc="Список категорий активностей (опционально)")
class FetchIssueAllActivitiesAction(BaseSimpleAction):
    """
    Получает все активности задачи из YouTrack по её внутреннему ID.
    Возвращает список сырых активностей (без фильтрации) в виде словарей.
    """

    def _ms_to_datetime(self, ms: int) -> datetime:
        return datetime.utcfromtimestamp(ms / 1000.0)

    def _fetch_activities(self, base_url: str, token: str, issue_id: str, from_ms: Optional[int], categories: Optional[List[str]]) -> List[Dict]:
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        params = {
            "fields": (
                "id,timestamp,"
                "author(login,name,fullName),"
                "field(id,name),"
                "targetMember,"
                "added(id,name,login,fullName,minutes,text,presentation),"
                "removed(id,name,login,fullName,minutes,text,presentation),"
                "category(id,name),"
                "comment(text),"
                "attachment(id,name)"
            )
        }
        if from_ms is not None:
            params["start"] = from_ms

        # Ключевое исправление: передаём список, а не строку через запятую
        if categories:
            params["categories"] = categories   # requests сам преобразует в &categories=val1&categories=val2

        url = f"{base_url}/api/issues/{issue_id}/activities"
        logger.debug(f"Запрос к YouTrack: {url} с params {params}")
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=60)
        except requests.exceptions.RequestException as e:
            raise HandleException(f"Ошибка соединения для {issue_id}: {e}")

        if resp.status_code != 200:
            raise HandleException(f"HTTP {resp.status_code} для {issue_id}: {resp.text}")

        data = resp.json()
        if not isinstance(data, list):
            raise HandleException("Неожиданный формат ответа от YouTrack")

        logger.debug(f"Получено {len(data)} активностей для задачи {issue_id}")
        return data

    @IntFieldChecker("count", min_value=0, desc="Количество полученных активностей")
    def _handleAspect(self, ctx: Context, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        base_url = params["base_url"]
        token = params["token"]
        issue_id = params["issue_id"]
        from_ms = params.get("from_timestamp_ms")
        categories = params.get("categories")

        activities = self._fetch_activities(base_url, token, issue_id, from_ms, categories)

        for act in activities:
            if "timestamp" in act:
                act["timestamp_datetime"] = self._ms_to_datetime(act["timestamp"])

        return {
            "activities": activities,
            "count": len(activities)
        }