# APP/YouTrackIssuesParser.py
from typing import Any, Dict, List, Optional
from datetime import datetime, date

from ActionEngine import BaseSimpleAction, Context, InstanceOfChecker

@InstanceOfChecker("issues", expected_class=list)
class YouTrackIssuesParser(BaseSimpleAction):
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
        return datetime.utcfromtimestamp(ms / 1000.0) if ms else None

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
                return None
        return None

    @staticmethod
    def _get_field(issue: Dict, name: str) -> Any:
        return issue.get(name)

    @staticmethod
    def _get_project(issue: Dict) -> Dict[str, Optional[str]]:
        proj = issue.get("project")
        if isinstance(proj, dict):
            return {
                "project_id": proj.get("id"),
                "project_name": proj.get("name")
            }
        return {"project_id": None, "project_name": None}

    @staticmethod
    def _get_parent_id(issue: Dict) -> Optional[str]:
        for link in issue.get("links") or []:
            lt = link.get("linkType", {}).get("name")
            if lt == "Subtask" and link.get("direction") == "INWARD":
                issues = link.get("issues")
                if issues and isinstance(issues, list) and issues:
                    return issues[0].get("idReadable")
        return None

    # ----- Кастомные поля -----
    @staticmethod
    def _get_custom_field(issue: Dict, field_name: str) -> Any:
        for cf in issue.get("customFields") or []:
            name = cf.get("projectCustomField", {}).get("field", {}).get("name")
            if name == field_name:
                return cf.get("value")
        return None

    @staticmethod
    def _extract_custom_value(raw: Any) -> Any:
        if isinstance(raw, dict):
            for key in ("name", "login", "fullName", "minutes", "presentation"):
                if key in raw:
                    return raw[key]
            return str(raw)
        return raw

    @classmethod
    def _get_custom_field_display(cls, issue: Dict, field_name: str) -> Any:
        return cls._extract_custom_value(cls._get_custom_field(issue, field_name))

    @classmethod
    def _get_user_field(cls, issue: Dict, field_name: str) -> Dict:
        res = {"Login": None, "Name": None, "FullName": None}
        raw = cls._get_custom_field(issue, field_name)
        if isinstance(raw, dict):
            res["Login"] = raw.get("login")
            res["Name"] = raw.get("name")
            res["FullName"] = raw.get("fullName")
        return res

    @classmethod
    def _get_sprint_field(cls, issue: Dict) -> str:
        raw = cls._get_custom_field(issue, "Единый спринт")
        if raw is None:
            return ""
        if isinstance(raw, list):
            names = [item.get("name") for item in raw if isinstance(item, dict) and item.get("name")]
            return ", ".join(names)
        return str(cls._extract_custom_value(raw))

    # ----- Стратегии для разных типов -----
    @classmethod
    def _user_story_strategy(cls, issue: Dict) -> Dict[str, Any]:
        row = {}
        row["key"] = cls._get_field(issue, "idReadable")
        row["id"] = cls._get_field(issue, "id")
        row["title"] = cls._get_field(issue, "summary")
        row["description"] = cls._get_field(issue, "description")
        row["created"] = cls._ms_to_datetime(cls._get_field(issue, "created"))
        row["updated"] = cls._ms_to_datetime(cls._get_field(issue, "updated"))
        row["date_resolved"] = cls._ms_to_datetime(cls._get_field(issue, "resolved"))
        row["parent_key"] = cls._get_parent_id(issue)

        proj = cls._get_project(issue)
        row["project_id"] = proj["project_id"]
        row["project_name"] = proj["project_name"]
        # project_code не заполняем, он вычислится в БД

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
    def _task_item_strategy(cls, issue: Dict) -> Dict[str, Any]:
        row = {}
        row["key"] = cls._get_field(issue, "idReadable")
        row["id"] = cls._get_field(issue, "id")
        row["title"] = cls._get_field(issue, "summary")
        row["description"] = cls._get_field(issue, "description")
        row["created"] = cls._ms_to_datetime(cls._get_field(issue, "created"))
        row["updated"] = cls._ms_to_datetime(cls._get_field(issue, "updated"))
        row["date_resolved"] = cls._ms_to_datetime(cls._get_field(issue, "resolved"))
        row["parent_key"] = cls._get_parent_id(issue)

        proj = cls._get_project(issue)
        row["project_id"] = proj["project_id"]
        row["project_name"] = proj["project_name"]
        # project_code не заполняем

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

    @InstanceOfChecker("by_type", expected_class=dict)
    def _handleAspect(self, ctx: Context, params: Dict, result: Dict) -> Dict:
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