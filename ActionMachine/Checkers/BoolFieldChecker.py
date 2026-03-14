# ActionMachine/Checkers/BoolFieldChecker.py
"""
Чекер для булевых полей.

Требования:
- Документирование всех классов.
- Документирование всех методов.
- Текст исключений писать на русском.
"""

from typing import Any
from .BaseFieldChecker import BaseFieldChecker
from ActionMachine.Core.Exceptions import ValidationFieldException


class BoolFieldChecker(BaseFieldChecker):
    """
    Проверяет, что значение является булевым (bool).
    Обязательность поля проверяется в базовом классе.
    """

    def __init__(self, field_name: str, desc: str, required: bool = True):
        """
        Параметры:
            field_name: имя поля.
            desc: описание чекера (обязательно).
            required: обязательно ли поле.
        """
        super().__init__(field_name, required, desc)

    def _check_type_and_constraints(self, value: Any) -> None:
        """
        Проверяет, что значение имеет тип bool.
        Если нет – выбрасывает ValidationFieldException с русскоязычным сообщением.
        """
        if not isinstance(value, bool):
            raise ValidationFieldException(
                f"Параметр '{self.field_name}' должен быть булевым (True/False), получен {type(value).__name__}"
            )
