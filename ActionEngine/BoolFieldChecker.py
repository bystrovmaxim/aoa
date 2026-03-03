# Файл: ActionEngine/BoolFieldChecker.py
"""
Чекер для булевых полей.

Требования:
- Документирование всех методов.
- Текст исколючений писать на русском.
"""
from typing import Any
from .BaseFieldChecker import BaseFieldChecker
from .Exceptions import ValidationFieldException

class BoolFieldChecker(BaseFieldChecker):
    """
    Проверяет, что значение является булевым (bool).
    Обязательность поля проверяется в базовом классе.
    """

    def _check_type_and_constraints(self, value: Any) -> None:
        """
        Проверяет, что значение имеет тип bool.
        Если нет – выбрасывает ValidationFieldException с русскоязычным сообщением.
        """
        if not isinstance(value, bool):
            raise ValidationFieldException(
                f"Параметр '{self.field_name}' должен быть булевым (True/False), получен {type(value).__name__}"
            )