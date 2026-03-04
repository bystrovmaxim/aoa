# Файл: YouTrackMCP/FetchIssuesFromYouTrackAction.py
"""
Действие для загрузки задач из YouTrack и передачи их в список кортежей (контекст, сейвер).

Требования:
- Документирование всех классов.
- Документирование всех методов.
- Текст исключений писать на русском.
"""
import time
import requests
from typing import List, Dict, Any, Optional, Tuple

from ActionEngine.BaseSimpleAction import BaseSimpleAction
from ActionEngine.Context import Context
from ActionEngine.CheckRoles import CheckRoles
from ActionEngine.StringFieldChecker import StringFieldChecker
from ActionEngine.IntFieldChecker import IntFieldChecker
from ActionEngine.InstanceOfChecker import InstanceOfChecker
from ActionEngine.TransactionContext import TransactionContext
from ActionEngine.Exceptions import HandleException


@CheckRoles(CheckRoles.ANY)
@StringFieldChecker("base_url")
@StringFieldChecker("token")
@StringFieldChecker("project_id", required=False, not_empty=True)
@IntFieldChecker("page_size", required=True, min_value=1, max_value=500)
@InstanceOfChecker("savers", expected_class=list, required=True)
class FetchIssuesFromYouTrackAction(BaseSimpleAction):
    """
    Загружает задачи из YouTrack (все или только указанного проекта) постранично
    и для каждой страницы вызывает все переданные сейверы с их контекстами.

    Параметр savers должен быть списком кортежей (context, saver), где:
        - context: экземпляр Context (или TransactionContext) – будет передан в saver.run
        - saver: объект, имеющий метод run(context, params)
    """

    # Максимальное количество страниц для защиты от бесконечного цикла
    MAX_PAGES = 10000

    def __init__(self):
        super().__init__()

    def _fetch_page(
        self,
        base_url: str,
        token: str,
        query: str,
        page_size: int,
        skip: int
    ) -> tuple[List[Dict], int, Optional[str]]:
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

        fields = (
            "id,idReadable,summary,description,created,updated,resolved,"
            "customFields(id,projectCustomField(field(name)),value(name,login,fullName,minutes,text,presentation)),"
            "links(direction,linkType(name),issues(idReadable,summary))"
        )

        req_params = {
            "fields": fields,
            "$top": page_size,
            "$skip": skip
        }
        if query:
            req_params["query"] = query

        try:
            response = requests.get(
                f"{base_url}/api/issues",
                headers=headers,
                params=req_params,
                timeout=30
            )
        except requests.exceptions.RequestException as e:
            return [], 0, f"Ошибка соединения: {e}"

        if response.status_code != 200:
            return [], 0, f"HTTP {response.status_code}: {response.text}"

        issues = response.json()
        if not isinstance(issues, list):
            return [], 0, "Некорректный формат ответа: ожидался список"

        return issues, len(issues), None

    def _handleAspect(
        self,
        ctx: Context,
        params: Dict[str, Any],
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Основной аспект: организует цикл пагинации и для каждой страницы вызывает все сейверы.

        Параметры:
            params: должен содержать:
                - base_url (str)
                - token (str)
                - page_size (int)
                - savers (List[Tuple[Context, Any]]) – список кортежей (контекст, сейвер)
                - project_id (str, опционально)
        Возвращает статистику: {'total_issues': int, 'pages': int}
        """
        base_url = params["base_url"]
        token = params["token"]
        page_size = params["page_size"]
        project_id = params.get("project_id")
        savers = params.get("savers", [])

        if not isinstance(savers, list):
            raise TypeError("Параметр 'savers' должен быть списком кортежей (контекст, сейвер)")

        query = f'project: {project_id}' if project_id else ''
        skip = 0
        pages = 0
        total_issues = 0

        while True:
            if pages >= self.MAX_PAGES:
                raise HandleException(f"Превышено максимальное количество страниц ({self.MAX_PAGES}). Возможно, зацикливание.")

            issues, count, error = self._fetch_page(base_url, token, query, page_size, skip)
            if error:
                raise HandleException(error)

            if count == 0:
                break

            sub_params = {
                "issues": issues,
                "first_page": (skip == 0)
            }

            # Вызываем каждый сейвер с его контекстом
            for saver_ctx, saver in savers:
                saver.run(saver_ctx, sub_params)

            total_issues += count
            pages += 1
            print(f"✅ Загружено и передано сейверам {total_issues} задач...")

            if count < page_size:
                break
            skip += page_size
            time.sleep(0.2)

        print(f"🎉 Всего обработано {total_issues} задач за {pages} страниц(ы)")
        return {"total_issues": total_issues, "pages": pages}