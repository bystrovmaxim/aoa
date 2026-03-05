# ActionEngine/Checkers/StringFieldChecker.py
"""
Чекер для строковых полей.

Требования:
- Документирование всех классов.
- Документирование всех методов.
- Текст исколючений писать на русском.
"""
from typing import Any, Optional
from .BaseFieldChecker import BaseFieldChecker
from ActionEngine.Core.Exceptions import ValidationFieldException

class StringFieldChecker(BaseFieldChecker):
    """
    Проверяет, что значение является строкой и удовлетворяет дополнительным условиям:
    - not_empty: строка не должна быть пустой (после проверки типа).
    - min_length: минимальная длина строки.
    - max_length: максимальная длина строки.
    """

    def __init__(self,
                 field_name: str,
                 required: bool = True,
                 min_length: Optional[int] = None,
                 max_length: Optional[int] = None,
                 not_empty: bool = False,
                 desc: str = None):
        """
        Параметры:
            field_name: имя поля.
            required: обязательно ли поле.
            min_length: минимальная допустимая длина строки (включительно).
            max_length: максимальная допустимая длина строки (включительно).
            not_empty: если True, строка не может быть пустой (len>0).
        """
        super().__init__(field_name, required, desc)
        self.min_length = min_length
        self.max_length = max_length
        self.not_empty = not_empty

    def _check_type_and_constraints(self, value: Any) -> None:
        """
        Проверяет, что значение является строкой, и если заданы ограничения – применяет их.
        При нарушении выбрасывает ValidationFieldException с русскоязычным сообщением.
        """
        if not isinstance(value, str):
            raise ValidationFieldException(
                f"Параметр '{self.field_name}' должен быть строкой, получен {type(value).__name__}"
            )

        if self.not_empty and len(value) == 0:
            raise ValidationFieldException(f"Параметр '{self.field_name}' не может быть пустым")

        if self.min_length is not None and len(value) < self.min_length:
            raise ValidationFieldException(
                f"Длина параметра '{self.field_name}' должна быть не меньше {self.min_length}"
            )

        if self.max_length is not None and len(value) > self.max_length:
            raise ValidationFieldException(
                f"Длина параметра '{self.field_name}' должна быть не больше {self.max_length}"
            )