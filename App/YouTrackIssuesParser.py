"""
Действие для парсинга задач YouTrack и группировки по типам карточек.
"""
from typing import Any, Dict, List, Optional
from datetime import datetime, date

from ActionEngine.BaseSimpleAction import BaseSimpleAction
from ActionEngine.Context import Context
from ActionEngine.InstanceOfChecker import InstanceOfChecker


class YouTrackIssuesParser(BaseSimpleAction):
    """
    Принимает список задач (issues) и возвращает словарь, где ключ – тип карточки,
    значение – список плоских словарей с данными задачи.
    """

    # Все возможные типы карточек
    STORY_TYPES = ["Пользовательская история", "Техническая история"]
    TASK_TYPES = [
        "Разработка",
        "Аналитика и проектирование",
        "Решение инцидентов",
        "Работа вместо системы"
    ]
    ALL_TYPES = STORY_TYPES + TASK_TYPES

    @staticmethod
    def _ms_to_datetime(ms: Optional[int]) -> Optional[datetime]:
        if ms is None:
            return None
        return datetime.utcfromtimestamp(ms / 1000.0)

    @staticmethod
    def _str_to_date(value: Optional[Any]) -> Optional[date]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return datetime.utcfromtimestamp(value / 1000.0).date()
        if isinstance(value, str):
            try:
                return datetime.strptime(value, "%Y-%m-%d").date()
            except ValueError:
                # Логирование можно добавить, но для простоты пропускаем
                return None
        return None

    @staticmethod
    def _get_field(issue: Dict[str, Any], field_name: str) -> Any:
        return issue.get(field_name)

    @staticmethod
    def _get_parent_id(issue: Dict[str, Any]) -> Optional[str]:
        links = issue.get("links")
        if links and isinstance(links, list):
            for link in links:
                link_type = link.get("linkType", {}).get("name")
                direction = link.get("direction")
                if link_type == "Subtask" and direction == "INWARD":
                    issues_list = link.get("issues")
                    if issues_list and isinstance(issues_list, list) and len(issues_list) > 0:
                        return issues_list[0].get("idReadable")
        return None

    @staticmethod
    def _get_custom_field(issue: Dict[str, Any], field_name: str) -> Any:
        for cf in issue.get("customFields", []):
            name = cf.get("projectCustomField", {}).get("field", {}).get("name")
            if name == field_name:
                return cf.get("value")
        return None

    @staticmethod
    def _extract_custom_value(raw_value: Any) -> Any:
        if isinstance(raw_value, dict):
            for key in ("name", "login", "fullName", "minutes", "presentation"):
                if key in raw_value:
                    return raw_value[key]
            return str(raw_value)
        return raw_value

    @classmethod
    def _get_custom_field_display(cls, issue: Dict[str, Any], field_name: str) -> Any:
        raw = cls._get_custom_field(issue, field_name)
        return cls._extract_custom_value(raw)

    @classmethod
    def _get_user_field(cls, issue: Dict[str, Any], field_name: str) -> Dict[str, Optional[str]]:
        result = {"Login": None, "Name": None, "FullName": None}
        raw = cls._get_custom_field(issue, field_name)
        if isinstance(raw, dict):
            result["Login"] = raw.get("login")
            result["Name"] = raw.get("name")
            result["FullName"] = raw.get("fullName")
        return result

    @classmethod
    def _get_sprint_field(cls, issue: Dict[str, Any]) -> str:
        raw = cls._get_custom_field(issue, "Единый спринт")
        if raw is None:
            return ""
        if isinstance(raw, list):
            names = []
            for item in raw:
                if isinstance(item, dict) and "name" in item:
                    names.append(item["name"])
            return ", ".join(names)
        return str(cls._extract_custom_value(raw))

    @classmethod
    def _user_story_strategy(cls, issue: Dict[str, Any]) -> Dict[str, Any]:
        row = {}
        row["key"] = cls._get_field(issue, "idReadable")
        row["id"] = cls._get_field(issue, "id")
        row["title"] = cls._get_field(issue, "summary")
        row["description"] = cls._get_field(issue, "description")
        row["created"] = cls._ms_to_datetime(cls._get_field(issue, "created"))
        row["updated"] = cls._ms_to_datetime(cls._get_field(issue, "updated"))
        row["date_resolved"] = cls._ms_to_datetime(cls._get_field(issue, "resolved"))
        row["parent_key"] = cls._get_parent_id(issue)

        assignee = cls._get_user_field(issue, "Assignee")
        row["assignee_login"] = assignee["Login"]
        row["assignee_name"] = assignee["Name"]
        row["assignee_fullname"] = assignee["FullName"]

        row["type"] = cls._get_custom_field_display(issue, "_Тип карточки")
        row["status"] = cls._get_custom_field_display(issue, "_Статус истории")
        row["plan_start"] = cls._str_to_date(cls._get_custom_field_display(issue, "_План начало"))
        row["plan_finish"] = cls._str_to_date(cls._get_custom_field_display(issue, "_План конец"))
        row["fact_forecast_start"] = cls._str_to_date(cls._get_custom_field_display(issue, "_Прогноз начало"))
        row["fact_forecast_finish"] = cls._str_to_date(cls._get_custom_field_display(issue, "_Прогноз конец"))
        row["customer"] = cls._get_custom_field_display(issue, "Приемщик")
        row["sprints"] = cls._get_sprint_field(issue)
        return row

    @classmethod
    def _task_item_strategy(cls, issue: Dict[str, Any]) -> Dict[str, Any]:
        row = {}
        row["key"] = cls._get_field(issue, "idReadable")
        row["id"] = cls._get_field(issue, "id")
        row["title"] = cls._get_field(issue, "summary")
        row["description"] = cls._get_field(issue, "description")
        row["created"] = cls._ms_to_datetime(cls._get_field(issue, "created"))
        row["updated"] = cls._ms_to_datetime(cls._get_field(issue, "updated"))
        row["date_resolved"] = cls._ms_to_datetime(cls._get_field(issue, "resolved"))
        row["parent_key"] = cls._get_parent_id(issue)

        assignee = cls._get_user_field(issue, "Assignee")
        row["assignee_login"] = assignee["Login"]
        row["assignee_name"] = assignee["Name"]
        row["assignee_fullname"] = assignee["FullName"]

        tester = cls._get_user_field(issue, "_Тестер")
        row["tester_login"] = tester["Login"]
        row["tester_name"] = tester["Name"]
        row["tester_fullname"] = tester["FullName"]

        row["type"] = cls._get_custom_field_display(issue, "_Тип карточки")
        row["status"] = cls._get_custom_field_display(issue, "_Статус задачи")
        sp = cls._get_custom_field_display(issue, "_Story points")
        try:
            row["story_points"] = float(sp) if sp is not None else None
        except (ValueError, TypeError):
            row["story_points"] = None
        row["priority"] = cls._get_custom_field_display(issue, "_Приоритет")
        row["subcomponent"] = cls._get_custom_field_display(issue, "subcomponent")
        row["sprints"] = cls._get_sprint_field(issue)
        return row

    @InstanceOfChecker("by_type", expected_class=dict)  # словарь с данными, сгруппированными по типам
    def _handleAspect(self, ctx: Context, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Основной аспект: получает список задач из params["issues"] и возвращает
        словарь by_type с данными, сгруппированными по типу карточки.
        """
        issues = params.get("issues", [])
        if not isinstance(issues, list):
            return {"by_type": {}}

        grouped = {t: [] for t in self.ALL_TYPES}
        for issue in issues:
            issue_type = self._get_custom_field_display(issue, "_Тип карточки")
            if issue_type not in self.ALL_TYPES:
                continue
            if issue_type in self.STORY_TYPES:
                row = self._user_story_strategy(issue)
            else:
                row = self._task_item_strategy(issue)
            grouped[issue_type].append(row)

        return {"by_type": grouped}