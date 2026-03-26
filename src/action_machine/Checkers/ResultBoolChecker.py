"""
Чекер для булевых полей результата аспекта.

Назначение:
    Проверяет, что значение поля результата является булевым (True/False).

Использование:
    Применяется как декоратор к методам-аспектам:
        @regular_aspect("Проверка активности")
        @ResultBoolChecker("active", "Активен", required=True)
        async def check_active(self, ...):
            return {"active": True}
"""

from typing import Any

from action_machine.Core.Exceptions import ValidationFieldError

from .ResultFieldChecker import ResultFieldChecker


class ResultBoolChecker(ResultFieldChecker):
    """
    Проверяет, что значение является булевым (bool).
    Обязательность поля проверяется в базовом классе.
    """

    def __init__(self, field_name: str, desc: str, required: bool = True):
        """
        Инициализирует чекер.

        Аргументы:
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
            raise ValidationFieldError(
                f"Параметр '{self.field_name}' должен быть булевым (True/False), получен {type(value).__name__}"
            )