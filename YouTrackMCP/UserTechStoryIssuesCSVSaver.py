# Файл: YouTrackMCP/UserTechStoryIssuesCSVSaver.py
"""
Сохранятель для пользовательских и технических историй в CSV.

Требования:
- Документирование всех классов.
- Документирование всех методов.
- Текст исключений писать на русском.
"""
from typing import Any, Dict, List

from ActionEngine.TransactionContext import TransactionContext
from ActionEngine.Exceptions import ValidationFieldException
from .BaseIssuesCSVSaver import BaseIssuesCSVSaver


class UserTechStoryIssuesCSVSaver(BaseIssuesCSVSaver):
    """
    Сохранятель для задач типа "Пользовательская история" и "Техническая история".
    В _preHandleAspect фильтрует входящий список задач, оставляя только нужные,
    преобразует их в плоские словари и возвращает заголовки и строки для записи в CSV.
    """

    # Типы задач, которые обрабатывает данный сохранятель
    _ALLOWED_TYPES = {"Пользовательская история", "Техническая история"}

    def _extract_flat_row(self, issue: Dict) -> Dict[str, Any]:
        """
        Преобразует задачу (словарь из API YouTrack) в плоский словарь,
        где ключи — имена полей (включая кастомные), значения — примитивы.
        """
        row = {
            "id": issue.get("id"),
            "idReadable": issue.get("idReadable"),
            "summary": issue.get("summary"),
            "description": issue.get("description"),
            "created": issue.get("created"),
            "updated": issue.get("updated"),
            "resolved": issue.get("resolved"),
        }

        for cf in issue.get("customFields", []):
            field_name = cf.get("projectCustomField", {}).get("field", {}).get("name")
            if not field_name:
                continue

            value_obj = cf.get("value")
            if isinstance(value_obj, dict):
                if "name" in value_obj:
                    value = value_obj["name"]
                elif "login" in value_obj:
                    value = value_obj["login"]
                elif "fullName" in value_obj:
                    value = value_obj["fullName"]
                elif "minutes" in value_obj:
                    value = value_obj["minutes"]
                elif "presentation" in value_obj:
                    value = value_obj["presentation"]
                else:
                    value = str(value_obj)
            else:
                value = value_obj

            row[field_name] = value

        return row

    def _preHandleAspect(
        self,
        ctx: TransactionContext,
        params: Dict[str, Any],
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Аспект предварительной обработки.

        Ожидает, что params содержит ключ 'issues' со списком задач.
        Фильтрует задачи по типу карточки (поле '_Тип карточки'),
        преобразует подходящие в плоские словари и возвращает
        словарь с ключами 'headers' (список колонок) и 'rows' (список строк).
        Если подходящих задач нет, возвращает пустые списки.
        """
        issues = params.get("issues", [])
        if not isinstance(issues, list):
            raise ValidationFieldException("Параметр 'issues' должен быть списком")

        # Сначала отфильтруем задачи по типу
        filtered = []
        for issue in issues:
            issue_type = None
            # Ищем поле _Тип карточки
            for cf in issue.get("customFields", []):
                field_name = cf.get("projectCustomField", {}).get("field", {}).get("name")
                if field_name == "_Тип карточки":
                    value_obj = cf.get("value")
                    if isinstance(value_obj, dict):
                        issue_type = value_obj.get("name")
                    else:
                        issue_type = value_obj
                    break
            if issue_type in self._ALLOWED_TYPES:
                filtered.append(issue)

        if not filtered:
            # Нет подходящих задач
            return {"headers": [], "rows": []}

        # Преобразуем каждую задачу в плоскую строку
        rows_data = [self._extract_flat_row(issue) for issue in filtered]

        # Заголовки — ключи первого словаря (все строки должны иметь одинаковые ключи)
        # Предполагаем, что структура задач одинакова
        headers = list(rows_data[0].keys())
        rows = [list(row.values()) for row in rows_data]

        return {"headers": headers, "rows": rows}