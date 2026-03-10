# APP/FetchIssueAllActivitiesAction.py
from typing import Any, Dict, List, Optional
from datetime import datetime
import requests
import logging
from dataclasses import dataclass, asdict

from ActionEngine import (
    BaseSimpleAction,
    Context,
    StringFieldChecker,
    IntFieldChecker,
    InstanceOfChecker,
    HandleException)

logger = logging.getLogger(__name__)


# ---- Вспомогательная функция для извлечения отображаемого значения ----

def extract_display_value(data: Any) -> Any:
    """
    Извлекает отображаемое значение из поля added/removed.
    Для статусов, пользователей и т.п. возвращает name/login.
    Для чисел/строк возвращает как есть.
    """
    if data is None:
        return None
    if isinstance(data, dict):
        # Приоритет: name -> login -> fullName -> value -> presentation -> str(data)
        return data.get("name") or data.get("login") or data.get("fullName") or data.get("value") or data.get("presentation") or str(data)
    if isinstance(data, list):
        # Для списков (например, множественные поля) обрабатываем каждый элемент
        return [extract_display_value(item) for item in data]
    # Простой тип
    return data


# ---- Модели активностей (типизированные) ----

@dataclass
class ActivityBase:
    """Базовые поля, общие для всех активностей."""
    id: str
    timestamp: int
    timestamp_datetime: datetime
    author: Dict[str, Any]
    category: Dict[str, Any]
    type: str


@dataclass
class IssueCreatedActivity(ActivityBase):
    field: Dict[str, Any]
    added: List[Any]
    removed: List[Any]
    targetMember: Optional[str] = None


@dataclass
class LinksActivity(ActivityBase):
    field: Dict[str, Any]
    added: List[Dict[str, Any]]
    removed: List[Dict[str, Any]]
    targetMember: Optional[str] = None


@dataclass
class CustomFieldActivity(ActivityBase):
    field: Dict[str, Any]
    added: Any               # сырое значение
    removed: Any              # сырое значение
    added_value: Any = None   # нормализованное отображаемое значение
    removed_value: Any = None # нормализованное отображаемое значение
    targetMember: Optional[str] = None


@dataclass
class CommentActivity(ActivityBase):
    field: Dict[str, Any]
    comment: Dict[str, Any]
    added: List[Dict[str, Any]]
    removed: List[Dict[str, Any]]
    targetMember: Optional[str] = None


@dataclass
class AttachmentActivity(ActivityBase):
    field: Dict[str, Any]
    added: List[Dict[str, Any]]
    removed: List[Dict[str, Any]]
    targetMember: Optional[str] = None


# ---- Парсер активностей ----

def parse_activity(raw: Dict[str, Any]) -> Dict[str, Any]:
    activity_type = raw.get("$type")
    if not activity_type:
        raise HandleException(f"Активность без поля $type: {raw}")

    common = {
        "id": raw.get("id"),
        "timestamp": raw.get("timestamp"),
        "timestamp_datetime": datetime.utcfromtimestamp(raw["timestamp"] / 1000.0) if raw.get("timestamp") else None,
        "author": raw.get("author", {}),
        "category": raw.get("category", {}),
        "type": activity_type,
    }

    if activity_type == "IssueCreatedActivityItem":
        obj = IssueCreatedActivity(
            **common,
            field=raw.get("field", {}),
            added=raw.get("added", []),
            removed=raw.get("removed", []),
            targetMember=raw.get("targetMember"),
        )
    elif activity_type == "LinksActivityItem":
        obj = LinksActivity(
            **common,
            field=raw.get("field", {}),
            added=raw.get("added", []),
            removed=raw.get("removed", []),
            targetMember=raw.get("targetMember"),
        )
    elif activity_type == "CustomFieldActivityItem":
        added_raw = raw.get("added")
        removed_raw = raw.get("removed")
        obj = CustomFieldActivity(
            **common,
            field=raw.get("field", {}),
            added=added_raw,
            removed=removed_raw,
            added_value=extract_display_value(added_raw),
            removed_value=extract_display_value(removed_raw),
            targetMember=raw.get("targetMember"),
        )
    elif activity_type == "CommentActivityItem":
        obj = CommentActivity(
            **common,
            field=raw.get("field", {}),
            comment=raw.get("comment", {}),
            added=raw.get("added", []),
            removed=raw.get("removed", []),
            targetMember=raw.get("targetMember"),
        )
    elif activity_type == "AttachmentActivityItem":
        obj = AttachmentActivity(
            **common,
            field=raw.get("field", {}),
            added=raw.get("added", []),
            removed=raw.get("removed", []),
            targetMember=raw.get("targetMember"),
        )
    else:
        raise HandleException(
            f"Неизвестный тип активности: {activity_type}\n"
            f"Полное содержимое: {raw}\n"
            "Требуется добавить поддержку этого типа в FetchIssueAllActivitiesAction."
        )

    return asdict(obj)


# ---- Основное действие ----

@StringFieldChecker("base_url", required=True)
@StringFieldChecker("token", required=True)
@StringFieldChecker("issue_id", required=True)
@IntFieldChecker("from_timestamp_ms", required=False)
@InstanceOfChecker("categories", expected_class=list, required=False)
@InstanceOfChecker("custom_field_names", expected_class=list, required=False)
class FetchIssueAllActivitiesAction(BaseSimpleAction):

    def _fetch_activities(self, base_url: str, token: str, issue_id: str,
                          from_ms: Optional[int], categories: Optional[List[str]]) -> List[Dict]:
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        params = {
            "fields": (
                "id,timestamp,"
                "author(login,name,fullName),"
                "field(id,name),"
                "targetMember,"
                "added(id,name,login,fullName,minutes,text,presentation,$type),"
                "removed(id,name,login,fullName,minutes,text,presentation,$type),"
                "category(id,name),"
                "comment(text),"
                "attachment(id,name),"
                "$type"
            )
        }
        if from_ms is not None:
            params["start"] = from_ms
        if categories:
            params["categories"] = categories

        url = f"{base_url}/api/issues/{issue_id}/activities"
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=60)
        except requests.exceptions.RequestException as e:
            raise HandleException(f"Ошибка соединения для {issue_id}: {e}")

        if resp.status_code != 200:
            raise HandleException(f"HTTP {resp.status_code} для {issue_id}: {resp.text}")

        data = resp.json()
        if not isinstance(data, list):
            raise HandleException("Неожиданный формат ответа от YouTrack")

        return data

    @IntFieldChecker("count", min_value=0)
    def _handleAspect(self, ctx: Context, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        base_url = params["base_url"]
        token = params["token"]
        issue_id = params["issue_id"]
        from_ms = params.get("from_timestamp_ms")
        categories = params.get("categories")
        custom_field_names = params.get("custom_field_names")

        raw_activities = self._fetch_activities(base_url, token, issue_id, from_ms, categories)

        # Фильтр по именам кастомных полей
        if custom_field_names is not None:
            filtered = []
            for act in raw_activities:
                cat = act.get("category", {})
                cat_id = cat.get("id") if isinstance(cat, dict) else None
                if cat_id == "CustomFieldCategory":
                    field = act.get("field")
                    field_name = field.get("name") if isinstance(field, dict) else None
                    if field_name in custom_field_names:
                        filtered.append(act)
                else:
                    filtered.append(act)
            raw_activities = filtered

        typed_activities = []
        for act in raw_activities:
            try:
                typed = parse_activity(act)
                typed_activities.append(typed)
            except Exception as e:
                logger.error(f"Ошибка парсинга активности для задачи {issue_id}: {e}")
                raise

        return {
            "activities": typed_activities,
            "count": len(typed_activities)
        }