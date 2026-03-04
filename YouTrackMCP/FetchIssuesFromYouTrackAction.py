import time
import requests
from typing import List, Dict, Any, Optional

from ActionEngine.BaseSimpleAction import BaseSimpleAction
from ActionEngine.Context import Context
from ActionEngine.CheckRoles import CheckRoles
from ActionEngine.StringFieldChecker import StringFieldChecker
from ActionEngine.IntFieldChecker import IntFieldChecker
from ActionEngine.InstanceOfChecker import InstanceOfChecker
from ActionEngine.Exceptions import HandleException
from .YouTrackIssuesParser import YouTrackIssuesParser
from .IYouTrackIssuesSaver import IYouTrackIssuesSaver


@CheckRoles(CheckRoles.ANY)
@StringFieldChecker("base_url")
@StringFieldChecker("token")
@IntFieldChecker("page_size", required=True, min_value=1, max_value=500)
@InstanceOfChecker("savers", expected_class=list, required=True)
class FetchIssuesFromYouTrackAction(BaseSimpleAction):
    """
    Загружает задачи из YouTrack постранично.
    Параметр savers должен быть списком кортежей (context, saver, card_types).
    Для каждой страницы парсит задачи через YouTrackIssuesParser и передаёт
    соответствующие подмножества каждому saver'у.
    """

    MAX_PAGES = 10000

    def _fetch_page(self, base_url: str, token: str, query: str, page_size: int, skip: int):
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
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

    def _handleAspect(self, ctx: Context, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        base_url = params["base_url"]
        token = params["token"]
        page_size = params["page_size"]
        project_id = params.get("project_id")
        savers = params.get("savers", [])   # список кортежей (context, saver, card_types)

        if not savers:
            raise HandleException("Список saver'ов пуст")

        query = f'project: {project_id}' if project_id else ''
        skip = 0
        pages = 0
        total_issues = 0

        # Создаём парсер (stateless, можно один на все страницы)
        parser = YouTrackIssuesParser()
        # Контекст для парсера – фиктивный, т.к. парсер не использует соединение
        dummy_ctx = Context()

        while True:
            if pages >= self.MAX_PAGES:
                raise HandleException(f"Превышено максимальное количество страниц ({self.MAX_PAGES})")

            issues, count, error = self._fetch_page(base_url, token, query, page_size, skip)
            if error:
                raise HandleException(error)
            if count == 0:
                break

            # Парсим задачи через действие
            parse_result = parser.run(dummy_ctx, {"issues": issues})
            by_type = parse_result.get("by_type", {})

            # Для каждого saver'а собираем данные по его типам
            for saver_ctx, saver, card_types in savers:
                if not isinstance(saver, IYouTrackIssuesSaver):
                    raise TypeError(f"Объект {saver} не реализует интерфейс IYouTrackIssuesSaver")

                # Собираем все строки для указанных типов
                all_rows = []
                for typ in card_types:
                    all_rows.extend(by_type.get(typ, []))

                if not all_rows:
                    continue  # для этого saver'а нет данных на странице

                # Объединяем заголовки (все возможные ключи)
                headers = sorted(set().union(*(row.keys() for row in all_rows)))
                data_rows = [[row.get(h) for h in headers] for row in all_rows]

                sub_params = {
                    "headers": headers,
                    "rows": data_rows,
                    "first_page": (skip == 0)
                }
                saver.run(saver_ctx, sub_params)

            total_issues += count
            pages += 1
            print(f"✅ Загружено и передано saver'ам {total_issues} задач...")

            if count < page_size:
                break
            skip += page_size
            time.sleep(0.2)

        print(f"🎉 Всего обработано {total_issues} задач за {pages} страниц(ы)")
        return {"total_issues": total_issues, "pages": pages}