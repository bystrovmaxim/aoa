# src/action_machine/checkers/result_bool_checker.py
"""
Чекер для булевых полей результата аспекта и функция-декоратор result_bool.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Модуль содержит два компонента:

1. **ResultBoolChecker** — класс checkerа. Checks, что поле результата
   является булевым значением (True/False). Числа (0, 1), строки
   ("true", "false") и другие типы не принимаются — только точное
   isinstance(value, bool). Создаётся машиной из checker snapshot entry
   при выполнении аспекта.

2. **result_bool** — функция-декоратор. Применяется к methodу-аспекту
   и записывает метаданные checkerа в атрибут ``_checker_meta`` methodа.
   MetadataBuilder собирает эти метаданные в checker snapshot (GateCoordinator.get_checkers).

═══════════════════════════════════════════════════════════════════════════════
USAGE КАК ДЕКОРАТОР
═══════════════════════════════════════════════════════════════════════════════

    @regular_aspect("Check")
    @result_bool("is_valid", required=True)
    async def validate(self, params, state, box, connections):
        return {"is_valid": True}

═══════════════════════════════════════════════════════════════════════════════
USAGE МАШИНОЙ
═══════════════════════════════════════════════════════════════════════════════

    checker = ResultBoolChecker("is_valid")
    checker.check({"is_valid": True})  # OK

═══════════════════════════════════════════════════════════════════════════════
PARAMETERS
═══════════════════════════════════════════════════════════════════════════════

    field_name : str — имя поля в словаре результата аспекта.
    required : bool — required ли поле. По умолчанию True.

Дополнительных parameters нет — наследует _get_extra_params от базового
класса ResultFieldChecker, который возвращает пустой словарь.

═══════════════════════════════════════════════════════════════════════════════
ERRORS
═══════════════════════════════════════════════════════════════════════════════

    ValidationFieldError — значение не bool.


AI-CORE-BEGIN
ROLE: module result_bool_checker
CONTRACT: Keep runtime behavior unchanged; decorators/inspectors expose metadata consumed by coordinator/machine.
INVARIANTS: Validate declarations early and provide deterministic metadata shape.
FLOW: declarations -> inspector snapshot -> coordinator cache -> runtime usage.
AI-CORE-END
"""

from typing import Any

from action_machine.core.exceptions import ValidationFieldError

from .result_field_checker import ResultFieldChecker
from .result_string_checker import _build_checker_meta


class ResultBoolChecker(ResultFieldChecker):
    """
    Checks, что значение является булевым (True/False).

    Числа (0, 1), строки ("true", "false") и другие типы не принимаются —
    только точное isinstance(value, bool).

    Создаётся машиной из checker snapshot entry при выполнении аспекта.
    Дополнительных parameters нет, поэтому _get_extra_params не переопределяется
    и возвращает пустой словарь из базового класса.
    """

    def _check_type_and_constraints(self, value: Any) -> None:
        """
        Checks, что value является булевым значением (True или False).

        Числа (0, 1), строки ("true", "false") и другие типы не принимаются —
        только точное isinstance(value, bool).

        Args:
            value: значение для проверки (гарантированно не None).

        Raises:
            ValidationFieldError: если value не bool.
        """
        if not isinstance(value, bool):
            raise ValidationFieldError(
                f"Parameter '{self.field_name}' must be boolean, got {type(value).__name__}"
            )


# ═════════════════════════════════════════════════════════════════════════════
# Decorator function
# ═════════════════════════════════════════════════════════════════════════════


def result_bool(
    field_name: str,
    required: bool = True,
) -> Any:
    """
    Decorator for an aspect method. Declares a boolean field in the aspect result.

    Writes checker metadata to the method attribute ``_checker_meta``.
    MetadataBuilder collects this metadata into checker snapshot (GateCoordinator.get_checkers).
    The machine creates a ResultBoolChecker instance from checker snapshot entry and calls
    checker.check(result_dict) when the aspect executes.

    Args:
        field_name: the field name in the aspect result dict.
        required: whether the field is required. Defaults to True.

    Returns:
        A decorator that writes _checker_meta to the method.

    Example:
        @regular_aspect("Validation")
        @result_bool("is_valid", required=True)
        async def validate(self, params, state, box, connections):
            return {"is_valid": True}
    """
    checker = ResultBoolChecker(
        field_name=field_name,
        required=required,
    )
    meta = _build_checker_meta(checker)

    def decorator(func: Any) -> Any:
        if not hasattr(func, "_checker_meta"):
            func._checker_meta = []
        func._checker_meta.append(meta)
        return func

    return decorator
