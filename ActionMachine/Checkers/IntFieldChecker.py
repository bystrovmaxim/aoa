# ActionMachine/Checkers/IntFieldChecker.py
"""
Чекер для целочисленных полей.
"""

from typing import Any, Optional
from .BaseFieldChecker import BaseFieldChecker
from ActionMachine.Core.Exceptions import ValidationFieldException


class IntFieldChecker(BaseFieldChecker):
    """
    Проверяет, что значение является целым числом и лежит в заданном диапазоне.
    """

    def __init__(
        self,
        field_name: str,
        desc: str,
        required: bool = True,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None
    ):
        """
        Параметры:
            field_name: имя поля.
            desc: описание чекера (обязательно).
            required: обязательно ли поле.
            min_value: минимально допустимое значение (включительно).
            max_value: максимально допустимое значение (включительно).
        """
        super().__init__(field_name, required, desc)
        self.min_value = min_value
        self.max_value = max_value

    def _validate_int(self, value: Any) -> int:
        """
        Проверяет, что значение является целым числом, и возвращает его.

        Аргументы:
            value: значение для проверки.

        Возвращает:
            value как int.

        Исключения:
            ValidationFieldException: если value не int.
        """
        if not isinstance(value, int):
            raise ValidationFieldException(
                f"Параметр '{self.field_name}' должен быть целым числом, получен {type(value).__name__}"
            )
        return value

    def _check_range(self, value: int) -> None:
        """
        Проверяет, что целое число находится в допустимом диапазоне.

        Аргументы:
            value: значение для проверки.

        Исключения:
            ValidationFieldException: если число вне диапазона.
        """
        if self.min_value is not None and value < self.min_value:
            raise ValidationFieldException(
                f"Параметр '{self.field_name}' должен быть не меньше {self.min_value}"
            )
        if self.max_value is not None and value > self.max_value:
            raise ValidationFieldException(
                f"Параметр '{self.field_name}' должен быть не больше {self.max_value}"
            )

    def _check_type_and_constraints(self, value: Any) -> None:
        """
        Проверяет тип и применяет ограничения.
        """
        int_value = self._validate_int(value)
        self._check_range(int_value)
