# src/action_machine/checkers/result_bool_checker.py
"""
Чекер для булевых полей результата аспекта и функция-декоратор result_bool.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Модуль содержит два компонента:

1. **ResultBoolChecker** — класс чекера. Проверяет, что поле результата
   является булевым значением (True/False). Числа (0, 1), строки
   ("true", "false") и другие типы не принимаются — только точное
   isinstance(value, bool). Создаётся машиной из CheckerMeta
   при выполнении аспекта.

2. **result_bool** — функция-декоратор. Применяется к методу-аспекту
   и записывает метаданные чекера в атрибут ``_checker_meta`` метода.
   MetadataBuilder собирает эти метаданные в ClassMetadata.checkers.

═══════════════════════════════════════════════════════════════════════════════
ИСПОЛЬЗОВАНИЕ КАК ДЕКОРАТОР
═══════════════════════════════════════════════════════════════════════════════

    @regular_aspect("Проверка")
    @result_bool("is_valid", required=True)
    async def validate(self, params, state, box, connections):
        return {"is_valid": True}

═══════════════════════════════════════════════════════════════════════════════
ИСПОЛЬЗОВАНИЕ МАШИНОЙ
═══════════════════════════════════════════════════════════════════════════════

    checker = ResultBoolChecker("is_valid")
    checker.check({"is_valid": True})  # OK

═══════════════════════════════════════════════════════════════════════════════
ПАРАМЕТРЫ
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
from .result_string_checker import _build_checker_meta


class ResultBoolChecker(ResultFieldChecker):
    """
    Проверяет, что значение является булевым (True/False).

    Числа (0, 1), строки ("true", "false") и другие типы не принимаются —
    только точное isinstance(value, bool).

    Создаётся машиной из CheckerMeta при выполнении аспекта.
    Дополнительных параметров нет, поэтому _get_extra_params не переопределяется
    и возвращает пустой словарь из базового класса.
    """

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


# ═════════════════════════════════════════════════════════════════════════════
# Функция-декоратор
# ═════════════════════════════════════════════════════════════════════════════


def result_bool(
    field_name: str,
    required: bool = True,
) -> Any:
    """
    Декоратор метода-аспекта. Объявляет булево поле в результате аспекта.

    Записывает метаданные чекера в атрибут ``_checker_meta`` метода.
    MetadataBuilder собирает эти метаданные в ClassMetadata.checkers.
    Машина создаёт экземпляр ResultBoolChecker из CheckerMeta
    и вызывает checker.check(result_dict) при выполнении аспекта.

    Аргументы:
        field_name: имя поля в словаре результата аспекта.
        required: обязательно ли поле. По умолчанию True.

    Возвращает:
        Декоратор, записывающий _checker_meta в метод.

    Пример:
        @regular_aspect("Проверка")
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
