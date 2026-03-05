import time
import requests
from typing import List, Dict, Any, Optional, Tuple

from ActionEngine.BaseSimpleAction import BaseSimpleAction
from ActionEngine.Context import Context
from ActionEngine.CheckRoles import CheckRoles
from ActionEngine.StringFieldChecker import StringFieldChecker
from ActionEngine.IntFieldChecker import IntFieldChecker
from ActionEngine.InstanceOfChecker import InstanceOfChecker
from ActionEngine.Exceptions import HandleException
from .YouTrackIssuesParser import YouTrackIssuesParser
from .IYouTrackIssuesSaver import IYouTrackIssuesSaver

@CheckRoles(CheckRoles.ANY, description="Доступен любому аутентифицированному пользователю")
@StringFieldChecker("base_url", description="Входной параметр: URL YouTrack (обязательная строка)")
@StringFieldChecker("token", description="Входной параметр: токен доступа (обязательная строка)")
@IntFieldChecker("page_size", required=True, min_value=1, max_value=500, description="Входной параметр: размер страницы (целое от 1 до 500)")
@InstanceOfChecker("savers", expected_class=list, required=True, description="Входной параметр: список кортежей (context, saver, card_types)")
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

    @IntFieldChecker("total_issues", min_value=0, description="Результат _handleAspect: общее количество загруженных задач")
    @IntFieldChecker("pages", min_value=0, description="Результат _handleAspect: количество обработанных страниц")
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

        parser = YouTrackIssuesParser()
        dummy_ctx = Context()

        # Кэш заголовков для каждого набора типов карточек
        headers_cache: Dict[Tuple[str, ...], List[str]] = {}

        while True:
            if pages >= self.MAX_PAGES:
                raise HandleException(f"Превышено максимальное количество страниц ({self.MAX_PAGES})")

            issues, count, error = self._fetch_page(base_url, token, query, page_size, skip)
            if error:
                raise HandleException(error)
            if count == 0:
                break

            parse_result = parser.run(dummy_ctx, {"issues": issues})
            by_type = parse_result.get("by_type", {})

            for saver_ctx, saver, card_types in savers:
                if not isinstance(saver, IYouTrackIssuesSaver):
                    raise TypeError(f"Объект {saver} не реализует интерфейс IYouTrackIssuesSaver")

                # Собираем все строки для указанных типов на текущей странице
                page_rows = []
                for typ in card_types:
                    page_rows.extend(by_type.get(typ, []))

                if not page_rows:
                    continue

                # Определяем ключ для кэша
                cache_key = tuple(sorted(card_types))

                # Если заголовки ещё не определены, вычисляем их по данным этой страницы
                if cache_key not in headers_cache:
                    all_keys = set()
                    for row in page_rows:
                        all_keys.update(row.keys())
                    headers_cache[cache_key] = sorted(all_keys)

                headers = headers_cache[cache_key]

                # Преобразуем строки в списки значений в порядке headers
                data_rows = []
                for row in page_rows:
                    data_rows.append([row.get(h) for h in headers])

                sub_params = {
                    "headers": headers,
                    "rows": data_rows,
                }
                if "snapshot_date" in params:
                    sub_params["snapshot_date"] = params["snapshot_date"]

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