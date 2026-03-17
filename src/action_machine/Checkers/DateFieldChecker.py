# ActionMachine/Checkers/DateFieldChecker.py
"""
Чекер для полей с датой/временем.

Проверяет, что значение является объектом datetime или строкой в заданном формате,
и опционально проверяет диапазон дат.
"""

from datetime import datetime
from typing import Any

from action_machine.Core.Exceptions import ValidationFieldError

from .BaseFieldChecker import BaseFieldChecker


class DateFieldChecker(BaseFieldChecker):
    """
    Проверяет, что значение является датой/временем.

    Принимает либо объект datetime, либо строку в указанном формате.
    Дополнительно можно задать минимальную и максимальную дату.
    """

    def __init__(
        self,
        field_name: str,
        desc: str,
        required: bool = True,
        format: str | None = None,
        min_date: datetime | None = None,
        max_date: datetime | None = None,
    ):
        """
        Инициализирует чекер.

        Аргументы:
            field_name: имя поля.
            desc: описание чекера (обязательно).
            required: обязательно ли поле.
            format: формат строки даты (обязателен, если ожидается строка).
            min_date: минимально допустимая дата.
            max_date: максимально допустимая дата.
        """
        super().__init__(field_name, required, desc)
        self.format = format
        self.min_date = min_date
        self.max_date = max_date

    def _parse_string(self, value: str) -> datetime:
        """
        Парсит строку в datetime согласно заданному формату.

        Аргументы:
            value: строка для парсинга.

        Возвращает:
            Объект datetime.

        Исключения:
            ValidationFieldException: если формат не задан или строка не соответствует формату.
        """
        if not self.format:
            raise ValidationFieldError(
                f"Поле '{self.field_name}': для строкового ввода требуется указать формат даты"
            )
        try:
            return datetime.strptime(value, self.format)
        except ValueError:
            raise ValidationFieldError(
                f"Поле '{self.field_name}' должно быть строкой даты, соответствующей формату '{self.format}'"
            )

    def _check_range(self, dt: datetime) -> None:
        """
        Проверяет, что дата находится в заданном диапазоне.

        Аргументы:
            dt: объект datetime для проверки.

        Исключения:
            ValidationFieldException: если дата вне допустимого диапазона.
        """
        if self.min_date is not None and dt < self.min_date:
            raise ValidationFieldError(
                f"Поле '{self.field_name}' должно быть не меньше {self.min_date.isoformat()}"
            )
        if self.max_date is not None and dt > self.max_date:
            raise ValidationFieldError(
                f"Поле '{self.field_name}' должно быть не больше {self.max_date.isoformat()}"
            )

    def _check_type_and_constraints(self, value: Any) -> None:
        """
        Проверяет тип значения и, если это строка, преобразует в datetime,
        затем применяет проверку диапазона.

        Аргументы:
            value: значение для проверки.

        Исключения:
            ValidationFieldException: при несоответствии типа или нарушении диапазона.
        """
        if isinstance(value, str):
            dt = self._parse_string(value)
        elif isinstance(value, datetime):
            dt = value
        else:
            raise ValidationFieldError(
                f"Поле '{self.field_name}' должен быть объектом datetime или строкой, получен {type(value).__name__}"
            )
        self._check_range(dt)
