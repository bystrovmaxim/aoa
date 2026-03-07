# APP/FindIssuesNeedingHistoryUpdateAction.py
from typing import List, Optional
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
@IntFieldChecker("page_size", required=True, min_value=1, max_value=10000, desc="Размер страницы для пагинации")
@IntFieldChecker("since_timestamp_ms", required=True, desc="Начальная дата в миллисекундах (задачи, обновлённые после неё)")
class FindIssuesNeedingHistoryUpdateAction(BaseSimpleAction):
    """
    Получает из YouTrack список ключей задач, обновлённых после указанной даты.
    Использует поисковый запрос с фильтром по дате обновления.
    Поддерживает пагинацию через параметры $top и $skip.
    Возвращает список ключей в поле "issue_keys".
    """

    def _fetch_page(self, base_url: str, token: str, since_ms: int, page_size: int, skip: int) -> List[str]:
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        # Преобразуем миллисекунды в дату для запроса (формат YYYY-MM-DD)
        since_dt = datetime.utcfromtimestamp(since_ms / 1000.0)
        date_str = since_dt.strftime("%Y-%m-%d")
        query = f"updated: {date_str} .. *"
        params = {
            "query": query,
            "fields": "idReadable",
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
        # Извлекаем ключи
        keys = [item.get("idReadable") for item in data if item.get("idReadable")]
        return keys

    def _handleAspect(self, ctx: Context, params: dict, result: dict) -> dict:
        base_url = params["base_url"]
        token = params["token"]
        page_size = params["page_size"]
        since_ms = params["since_timestamp_ms"]

        all_keys = []
        skip = 0
        while True:
            page_keys = self._fetch_page(base_url, token, since_ms, page_size, skip)
            if not page_keys:
                break
            all_keys.extend(page_keys)
            if len(page_keys) < page_size:
                break
            skip += page_size

        logger.info(f"Найдено {len(all_keys)} задач, обновлённых после {datetime.utcfromtimestamp(since_ms/1000.0).date()}")
        return {"issue_keys": all_keys}