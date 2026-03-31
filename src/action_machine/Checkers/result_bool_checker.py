# src/action_machine/checkers/result_bool_checker.py
"""
Чекер для булевых полей результата аспекта.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет, что поле результата является булевым значением (True/False).
Числа (0, 1), строки ("true", "false") и другие типы не принимаются —
только точное isinstance(value, bool).

═══════════════════════════════════════════════════════════════════════════════
ДВОЙНОЕ ИСПОЛЬЗОВАНИЕ
═══════════════════════════════════════════════════════════════════════════════

1. Как декоратор метода-аспекта (порядок с @regular_aspect не важен):

    @regular_aspect("Проверка")
    @ResultBoolChecker("is_valid", required=True)
    async def validate(self, ...):
        return {"is_valid": True}

2. Как валидатор результата (вызывается машиной):

    checker = ResultBoolChecker("is_valid")
    checker.check({"is_valid": True})

═══════════════════════════════════════════════════════════════════════════════
ПАРАМЕТРЫ КОНСТРУКТОРА
═══════════════════════════════════════════════════════════════════════════════

    field_name : str — имя поля в словаре результата аспекта.
    required : bool — обязательно ли поле. По умолчанию True.

Дополнительных параметров нет — наследует _get_extra_params от базового
класса ResultFieldChecker, который возвращает пустой словарь.

═══════════════════════════════════════════════════════════════════════════════
ОШИБКИ
═══════════════════════════════════════════════════════════════════════════════

    ValidationFieldError — значение не bool.
"""

from typing import Any

from action_machine.core.exceptions import ValidationFieldError

from .result_field_checker import ResultFieldChecker


class ResultBoolChecker(ResultFieldChecker):
    """
    Проверяет, что значение является булевым (True/False).

    Поддерживает двойной режим: декоратор метода-аспекта и валидатор dict.
    Дополнительных параметров нет, поэтому _get_extra_params не переопределяется
    и возвращает пустой словарь из базового класса.
    """

    def __init__(
        self, field_name: str, required: bool = True
    ) -> None:
        """
        Инициализирует чекер.

        Аргументы:
            field_name: имя поля в словаре результата аспекта.
            required: является ли поле обязательным. По умолчанию True.
        """
        super().__init__(field_name, required)

    def _check_type_and_constraints(self, value: Any) -> None:
        """
        Проверяет, что value является булевым значением (True или False).

        Числа (0, 1), строки ("true", "false") и другие типы не принимаются —
        только точное isinstance(value, bool).

        Аргументы:
            value: значение для проверки (гарантированно не None).

        Исключения:
            ValidationFieldError: если value не bool.
        """
        if not isinstance(value, bool):
            raise ValidationFieldError(
                f"Параметр '{self.field_name}' должен быть булевым, получен {type(value).__name__}"
            )
