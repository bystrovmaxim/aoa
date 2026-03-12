# ActionMachine/Checkers/IntFieldChecker.py
"""
Чекер для целочисленных полей.

Требования:
- Документирование всех классов.
- Документирование всех методов.
- Текст исключений писать на русском.
"""
from typing import Any, Optional
from .BaseFieldChecker import BaseFieldChecker
from ActionMachine.Core.Exceptions import ValidationFieldException

class IntFieldChecker(BaseFieldChecker):
    """
    Проверяет, что значение является целым числом и лежит в заданном диапазоне.
    """

    def __init__(self,
                 field_name: str,
                 desc: str,
                 required: bool = True,
                 min_value: Optional[int] = None,
                 max_value: Optional[int] = None):
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

    def _check_type_and_constraints(self, value: Any) -> None:
        """
        Проверяет, что value является int и при необходимости входит в диапазон.
        """
        if not isinstance(value, int):
            raise ValidationFieldException(
                f"Параметр '{self.field_name}' должен быть целым числом, получен {type(value).__name__}"
            )

        if self.min_value is not None and value < self.min_value:
            raise ValidationFieldException(
                f"Параметр '{self.field_name}' должен быть не меньше {self.min_value}"
            )

        if self.max_value is not None and value > self.max_value:
            raise ValidationFieldException(
                f"Параметр '{self.field_name}' должен быть не больше {self.max_value}"
            )