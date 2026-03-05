# Файл: ActionEngine/FloatFieldChecker.py
"""
Чекер для полей с плавающей точкой.

Требования:
- Документирование всех классов.
- Документирование всех методов.
- Текст исколючений писать на русском.
"""
from typing import Any, Optional
from .BaseFieldChecker import BaseFieldChecker
from ActionEngine.Core.Exceptions import ValidationFieldException

class FloatFieldChecker(BaseFieldChecker):
    """
    Проверяет, что значение является числом (int или float) и лежит в заданном диапазоне.
    Обязательность проверяется в базовом классе.
    """

    def __init__(self,
                 field_name: str,
                 required: bool = True,
                 min_value: Optional[float] = None,
                 max_value: Optional[float] = None,
                 desc: str = None):
        """
        Параметры:
            field_name: имя поля.
            required: обязательно ли поле.
            min_value: минимально допустимое значение (включительно).
            max_value: максимально допустимое значение (включительно).
        """
        super().__init__(field_name, required, desc)
        self.min_value = min_value
        self.max_value = max_value

    def _check_type_and_constraints(self, value: Any) -> None:
        """
        Проверяет, что значение является числом, и если заданы границы – что оно в пределах.
        """
        if not isinstance(value, (int, float)):
            raise ValidationFieldException(
                f"Параметр '{self.field_name}' должен быть числом, получен {type(value).__name__}"
            )

        if self.min_value is not None and value < self.min_value:
            raise ValidationFieldException(
                f"Параметр '{self.field_name}' должен быть не меньше {self.min_value}"
            )

        if self.max_value is not None and value > self.max_value:
            raise ValidationFieldException(
                f"Параметр '{self.field_name}' должен быть не больше {self.max_value}"
            )