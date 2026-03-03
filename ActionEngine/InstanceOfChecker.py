# Файл: ActionEngine/InstanceOfChecker.py
"""
Чекер для проверки, что значение является экземпляром указанного класса (или его подкласса).

Требования:
- Документирование всех классов.
- Документирование всех методов.
- Текст исключений писать на русском.
"""
from typing import Any, Type, Union
from .BaseFieldChecker import BaseFieldChecker
from .Exceptions import ValidationFieldException


class InstanceOfChecker(BaseFieldChecker):
    """
    Проверяет, что значение является экземпляром указанного класса (или одного из классов, если передан кортеж).
    """

    def __init__(
        self,
        field_name: str,
        expected_class: Union[Type, tuple],
        required: bool = True
    ):
        """
        Параметры:
            field_name: имя поля.
            expected_class: класс (или кортеж классов), которым должно соответствовать значение.
            required: является ли поле обязательным.
        """
        super().__init__(field_name, required)
        self.expected_class = expected_class

    def _check_type_and_constraints(self, value: Any) -> None:
        """
        Проверяет, что value является экземпляром ожидаемого класса (или одного из классов).
        """
        if not isinstance(value, self.expected_class):
            if isinstance(self.expected_class, tuple):
                names = ', '.join(cls.__name__ for cls in self.expected_class)
                raise ValidationFieldException(
                    f"Параметр '{self.field_name}' должен быть экземпляром одного из классов: {names}, "
                    f"получен {type(value).__name__}"
                )
            else:
                raise ValidationFieldException(
                    f"Параметр '{self.field_name}' должен быть экземпляром класса {self.expected_class.__name__}, "
                    f"получен {type(value).__name__}"
                )