from typing import List, Dict, Optional
from datetime import datetime
import requests
import logging

from ActionEngine import (
    BaseSimpleAction,
    Context,
    StringFieldChecker,
    IntFieldChecker,
    HandleException)

logger = logging.getLogger(__name__)


@StringFieldChecker("base_url", required=True, desc="URL YouTrack")
@StringFieldChecker("token", required=True, desc="Токен доступа")
@IntFieldChecker("page_size", required=True, min_value=1, max_value=10000, desc="Размер страницы")
@IntFieldChecker("since_timestamp_ms", required=True, desc="Начальная дата в миллисекундах")
@StringFieldChecker("project_code", required=False, not_empty=True, desc="Код проекта (опционально)")
class FindIssuesNeedingHistoryUpdateAction(BaseSimpleAction):
    """
    Получает из YouTrack список внутренних ID задач, обновлённых после указанной даты.
    Возвращает список словарей с полем 'id' (внутренний ID).
    """

    def _fetch_page(self, base_url: str, token: str, since_ms: int, page_size: int, skip: int, project_code: Optional[str]) -> List[Dict[str, str]]:
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        since_dt = datetime.utcfromtimestamp(since_ms / 1000.0)
        date_str = since_dt.strftime("%Y-%m-%d")
        query = f"updated: {date_str} .. *"
        if project_code:
            query = f"project: {project_code} and {query}"
        params = {
            "query": query,
            "fields": "id",
            "$top": page_size,
            "$skip": skip
        }
        url = f"{base_url}/api/issues"
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=60)
        except Exception as e:
            raise HandleException(f"Ошибка при запросе списка задач: {e}")
        if resp.status_code != 200:
            raise HandleException(f"HTTP {resp.status_code}: {resp.text}")
        data = resp.json()
        if not isinstance(data, list):
            raise HandleException("Неожиданный формат ответа от YouTrack")
        result = []
        for item in data:
            if item.get("id"):
                result.append({"id": item["id"]})
        return result

    def _handleAspect(self, ctx: Context, params: dict, result: dict) -> dict:
        base_url = params["base_url"]
        token = params["token"]
        page_size = params["page_size"]
        since_ms = params["since_timestamp_ms"]
        project_code = params.get("project_code")

        all_issues = []
        skip = 0
        while True:
            page = self._fetch_page(base_url, token, since_ms, page_size, skip, project_code)
            if not page:
                break
            all_issues.extend(page)
            if len(page) < page_size:
                break
            skip += page_size

        logger.info(f"Найдено {len(all_issues)} задач, обновлённых после {datetime.utcfromtimestamp(since_ms/1000.0).date()}")
        return {"issues": all_issues}