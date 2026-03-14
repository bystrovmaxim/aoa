# ActionMachine/Checkers/StringFieldChecker.py
"""
Чекер для строковых полей.

Проверяет, что значение является строкой и удовлетворяет условиям:
- not_empty: строка не пустая.
- min_length: минимальная длина.
- max_length: максимальная длина.
"""

from typing import Any, Optional
from .BaseFieldChecker import BaseFieldChecker
from ActionMachine.Core.Exceptions import ValidationFieldException


class StringFieldChecker(BaseFieldChecker):
    """
    Проверяет, что значение является строкой и соответствует заданным ограничениям.
    """

    def __init__(
        self,
        field_name: str,
        desc: str,
        required: bool = True,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        not_empty: bool = False
    ):
        """
        Инициализирует чекер.

        Аргументы:
            field_name: имя поля.
            desc: описание чекера (обязательно).
            required: обязательно ли поле.
            min_length: минимальная допустимая длина строки (включительно).
            max_length: максимальная допустимая длина строки (включительно).
            not_empty: если True, строка не может быть пустой (len>0).
        """
        super().__init__(field_name, required, desc)
        self.min_length = min_length
        self.max_length = max_length
        self.not_empty = not_empty

    def _validate_string_type(self, value: Any) -> str:
        """
        Проверяет, что значение является строкой, и возвращает его.

        Аргументы:
            value: проверяемое значение.

        Возвращает:
            Значение, приведённое к строке.

        Исключения:
            ValidationFieldException: если value не строка.
        """
        if not isinstance(value, str):
            raise ValidationFieldException(
                f"Параметр '{self.field_name}' должен быть строкой, получен {type(value).__name__}"
            )
        return value

    def _check_empty(self, value: str) -> None:
        """
        Проверяет, что строка не пустая (если установлен флаг not_empty).

        Аргументы:
            value: строка для проверки.

        Исключения:
            ValidationFieldException: если строка пуста.
        """
        if self.not_empty and len(value) == 0:
            raise ValidationFieldException(f"Параметр '{self.field_name}' не может быть пустым")

    def _check_length(self, value: str) -> None:
        """
        Проверяет длину строки на соответствие min_length и max_length.

        Аргументы:
            value: строка для проверки.

        Исключения:
            ValidationFieldException: если длина вне допустимого диапазона.
        """
        if self.min_length is not None and len(value) < self.min_length:
            raise ValidationFieldException(
                f"Длина параметра '{self.field_name}' должна быть не меньше {self.min_length}"
            )
        if self.max_length is not None and len(value) > self.max_length:
            raise ValidationFieldException(
                f"Длина параметра '{self.field_name}' должна быть не больше {self.max_length}"
            )

    def _check_type_and_constraints(self, value: Any) -> None:
        """
        Выполняет полную проверку: тип, пустоту (если требуется), длину.

        Аргументы:
            value: значение для проверки.
        """
        str_value = self._validate_string_type(value)
        self._check_empty(str_value)
        self._check_length(str_value)
