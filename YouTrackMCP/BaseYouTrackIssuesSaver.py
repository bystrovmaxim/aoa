# Файл: YouTrackMCP/BaseYouTrackIssuesSaver.py
"""
Базовый класс для сохранятелей задач YouTrack с простыми стратегиями.
"""
from abc import abstractmethod
from typing import Any, Dict, List, Set, Optional

from ActionEngine.BaseTransactionAction import BaseTransactionAction
from ActionEngine.TransactionContext import TransactionContext
from ActionEngine.Exceptions import ValidationFieldException
from ActionEngine.InstanceOfChecker import InstanceOfChecker


@InstanceOfChecker("issues", expected_class=list, required=True)
class BaseYouTrackIssuesSaver(BaseTransactionAction):
    """
    Базовый класс для сохранятелей, работающих с задачами YouTrack.
    Предоставляет методы для чтения полей задачи и две стратегии извлечения данных.
    Конкретные наследники должны установить атрибут _strategy (список типов карточек)
    и могут переопределить get_strategy() при необходимости.
    В _preHandleAspect:
      - получает список задач issues из params,
      - для каждой задачи определяет тип карточки (через _get_custom_field_display),
      - если тип присутствует в стратегии (self.get_strategy()) и соответствует одной из стратегий,
        вызывает соответствующую стратегию и добавляет результат в общий массив.
    """

    def __init__(self):
        super().__init__()
        self._strategy: List[str] = []  # по умолчанию пусто – ничего не обрабатываем

    def get_strategy(self) -> List[str]:
        """
        Возвращает список типов карточек, которые должен обрабатывать данный сейвер.
        Может быть переопределён в наследнике, если стратегия вычисляется динамически.
        """
        return self._strategy

    # ----------------------------------------------------------------------
    # Методы чтения полей задачи (примитивы)
    # ----------------------------------------------------------------------

    def _get_field(self, issue: Dict[str, Any], field_name: str) -> Any:
        """
        Возвращает значение стандартного поля задачи.
        Для поля reporter возвращает имя или логин автора.
        """
    
        return issue.get(field_name)

    def _get_parent_id(self, issue: Dict[str, Any]) -> Optional[str]:
        """
        Возвращает идентификатор родительской задачи (idReadable) или None.
        Родитель ищется в связях (links) как элемент с linkType.name == "Subtask" и direction == "INWARD".
        """
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

    def _get_custom_field(self, issue: Dict[str, Any], field_name: str) -> Any:
        """
        Возвращает **сырое** значение кастомного поля.
        Если поле не найдено, возвращает None.
        """
        for cf in issue.get("customFields", []):
            name = cf.get("projectCustomField", {}).get("field", {}).get("name")
            if name == field_name:
                return cf.get("value")
        return None

    def _extract_custom_value(self, raw_value: Any) -> Any:
        """
        Преобразует сырое значение кастомного поля в читаемое представление.
        Для словарей пытается извлечь name, login, fullName, minutes, presentation.
        Если ничего не подошло, возвращает строковое представление словаря.
        Для прочих типов возвращает raw_value как есть.
        """
        if isinstance(raw_value, dict):
            for key in ("name", "login", "fullName", "minutes", "presentation"):
                if key in raw_value:
                    return raw_value[key]
            return str(raw_value)
        return raw_value

    def _get_custom_field_display(self, issue: Dict[str, Any], field_name: str) -> Any:
        """
        Возвращает обработанное (читаемое) значение кастомного поля.
        """
        raw = self._get_custom_field(issue, field_name)
        return self._extract_custom_value(raw)

    # ----------------------------------------------------------------------
    # Специализированный метод для пользовательских полей (с разбивкой на три колонки)
    # ----------------------------------------------------------------------

    def _get_user_field(self, issue: Dict[str, Any], field_name: str) -> Dict[str, Optional[str]]:
        """
        Извлекает информацию о пользователе по заданному кастомному полю.
        Возвращает словарь с ключами 'Login', 'Name', 'FullName'.
        Если поле не найдено или не является пользовательским, все значения None.
        """
        result = {"Login": None, "Name": None, "FullName": None}
        raw = self._get_custom_field(issue, field_name)
        if isinstance(raw, dict):
            result["Login"] = raw.get("login")
            result["Name"] = raw.get("name")
            result["FullName"] = raw.get("fullName")
        return result

    # ----------------------------------------------------------------------
    # Специализированный метод для поля "Единый спринт"
    # ----------------------------------------------------------------------

    def _get_sprint_field(self, issue: Dict[str, Any]) -> str:
        """
        Возвращает строку с именами спринтов через запятую.
        Использует сырое значение, так как требуется особая обработка списка.
        """
        raw = self._get_custom_field(issue, "Единый спринт")
        if raw is None:
            return ""
        if isinstance(raw, list):
            names = []
            for item in raw:
                if isinstance(item, dict) and "name" in item:
                    names.append(item["name"])
            return ", ".join(names)
        return str(self._extract_custom_value(raw))

    # ----------------------------------------------------------------------
    # Стратегии извлечения данных
    # ----------------------------------------------------------------------

    def _user_story_strategy(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """
        Извлекает данные для пользовательской или технической истории.
        """
        row = {}

        # Основные поля
        row["ID"] = self._get_field(issue, "id")
        row["Key"] = self._get_field(issue, "idReadable")
        row["Title"] = self._get_field(issue, "summary")
        row["Description"] = self._get_field(issue, "description")
        row["Created"] = self._get_field(issue, "created")
        row["Updated"] = self._get_field(issue, "updated")
        row["Date_Resolved"] = self._get_field(issue, "resolved")
        row["ParentID"] = self._get_parent_id(issue)

        # Пользовательские поля (исполнитель, приемщик)
        assignee = self._get_user_field(issue, "Assignee")
        row["Assignee_Login"] = assignee["Login"]
        row["Assignee_Name"] = assignee["Name"]
        row["Assignee_FullName"] = assignee["FullName"]

        # Остальные кастомные поля
        row["Type"] = self._get_custom_field_display(issue, "_Тип карточки")
        row["Status"] = self._get_custom_field_display(issue, "_Статус истории")
        row["Plan_Start"] = self._get_custom_field_display(issue, "_План начало")
        row["Plan_Finish"] = self._get_custom_field_display(issue, "_План конец")
        row["Fact_Forecast_Start"] = self._get_custom_field_display(issue, "_Прогноз начало")
        row["Fact_Forecast_Finish"] = self._get_custom_field_display(issue, "_Прогноз конец")
        row["Customer"] = self._get_custom_field_display(issue, "Приемщик")
        row["Sprints"] = self._get_sprint_field(issue)

        return row

    def _task_item_strategy(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """
        Извлекает данные для задач (разработка, аналитика, инциденты, работа вместо системы).
        """
        row = {}

        # Основные поля
        row["ID"] = self._get_field(issue, "id")
        row["Key"] = self._get_field(issue, "idReadable")
        row["Title"] = self._get_field(issue, "summary")
        row["Description"] = self._get_field(issue, "description")
        row["Created"] = self._get_field(issue, "created")
        row["Updated"] = self._get_field(issue, "updated")
        row["Date_Resolved"] = self._get_field(issue, "resolved")
        row["ParentID"] = self._get_parent_id(issue)

        # Исполнитель
        assignee = self._get_user_field(issue, "Assignee")
        row["Assignee_Login"] = assignee["Login"]
        row["Assignee_Name"] = assignee["Name"]
        row["Assignee_FullName"] = assignee["FullName"]

        # Тестер
        tester = self._get_user_field(issue, "_Тестер")
        row["Tester_Login"] = tester["Login"]
        row["Tester_Name"] = tester["Name"]
        row["Tester_FullName"] = tester["FullName"]

        # Остальные кастомные поля
        row["Type"] = self._get_custom_field_display(issue, "_Тип карточки")
        row["Status"] = self._get_custom_field_display(issue, "_Статус задачи")
        row["Story_points"] = self._get_custom_field_display(issue, "_Story points")
        row["Priority"] = self._get_custom_field_display(issue, "_Приоритет")
        row["Subcomponent"] = self._get_custom_field_display(issue, "subcomponent")
        row["Sprints"] = self._get_sprint_field(issue)

        return row

    # ----------------------------------------------------------------------
    # Аспекты
    # ----------------------------------------------------------------------

    def _preHandleAspect(
        self,
        ctx: TransactionContext,
        params: Dict[str, Any],
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Предварительная обработка:
          - Получает список задач issues из params.
          - Преобразует стратегию (self.get_strategy()) в множество.
          - Проходит по всем задачам, определяет тип карточки через _get_custom_field_display.
          - Если тип входит в стратегию и соответствует одной из стратегий,
            вызывает соответствующую стратегию и добавляет результат.
        """
        issues = params.get("issues", [])
        strategy_set = set(self.get_strategy())

        flat_rows = []

        for issue in issues:
            issue_type = self._get_custom_field_display(issue, "_Тип карточки")
            if issue_type not in strategy_set:
                continue

            if issue_type in ("Пользовательская история", "Техническая история"):
                row = self._user_story_strategy(issue)
                flat_rows.append(row)
            elif issue_type in ("Разработка", "Аналитика и проектирование",
                                "Решение инцидентов", "Работа вместо системы"):
                row = self._task_item_strategy(issue)
                flat_rows.append(row)

        page_num = "первая" if params.get("first_page") else "очередная"
        print(f"📊 {self.__class__.__name__}: на {page_num} странице обработано {len(flat_rows)} записей из {len(issues)} (стратегии: {sorted(strategy_set)})")

        if not flat_rows:
            return {"headers": [], "rows": []}

        # Собираем все возможные ключи
        all_keys: Set[str] = set()
        for row in flat_rows:
            all_keys.update(row.keys())
        headers = sorted(all_keys)

        rows = []
        for row in flat_rows:
            rows.append([row.get(key) for key in headers])

        return {"headers": headers, "rows": rows}

    @abstractmethod
    def _handleAspect(
        self,
        ctx: TransactionContext,
        params: Dict[str, Any],
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Основной аспект бизнес-логики.
        Должен быть реализован в наследнике. Ожидает, что result содержит
        'headers' и 'rows', полученные из _preHandleAspect.
        """
        pass