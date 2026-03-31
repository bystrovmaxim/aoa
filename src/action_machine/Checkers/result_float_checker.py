# src/action_machine/checkers/result_float_checker.py
"""
Чекер для числовых полей (int/float) результата аспекта и функция-декоратор result_float.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Модуль содержит два компонента:

1. **ResultFloatChecker** — класс чекера. Проверяет, что поле результата
   является числом (int или float) и лежит в заданном диапазоне.
   Создаётся машиной из CheckerMeta при выполнении аспекта.

2. **result_float** — функция-декоратор. Применяется к методу-аспекту
   и записывает метаданные чекера в атрибут ``_checker_meta`` метода.
   MetadataBuilder собирает эти метаданные в ClassMetadata.checkers.

═══════════════════════════════════════════════════════════════════════════════
ИСПОЛЬЗОВАНИЕ КАК ДЕКОРАТОР
═══════════════════════════════════════════════════════════════════════════════

    @regular_aspect("Расчёт")
    @result_float("total", required=True, min_value=0.0)
    async def calculate(self, params, state, box, connections):
        return {"total": 1500.0}

═══════════════════════════════════════════════════════════════════════════════
ИСПОЛЬЗОВАНИЕ МАШИНОЙ
═══════════════════════════════════════════════════════════════════════════════

    checker = ResultFloatChecker("total", min_value=0.0)
    checker.check({"total": 1500.0})  # OK

═══════════════════════════════════════════════════════════════════════════════
ПАРАМЕТРЫ
═══════════════════════════════════════════════════════════════════════════════

    field_name : str — имя поля в словаре результата аспекта.
    required : bool — обязательно ли поле. По умолчанию True.
    min_value : float | None — минимально допустимое значение (включительно).
    max_value : float | None — максимально допустимое значение (включительно).

═══════════════════════════════════════════════════════════════════════════════
ОШИБКИ
═══════════════════════════════════════════════════════════════════════════════

    ValidationFieldError — значение не int и не float; значение вне диапазона.
"""

from typing import Any

from action_machine.core.exceptions import ValidationFieldError

from .result_field_checker import ResultFieldChecker
from .result_string_checker import _build_checker_meta


class ResultFloatChecker(ResultFieldChecker):
    """
    Проверяет, что значение является числом (int или float) и лежит в заданном диапазоне.

    Создаётся машиной из CheckerMeta при выполнении аспекта.

    Атрибуты:
        min_value : float | None — минимально допустимое значение (включительно).
        max_value : float | None — максимально допустимое значение (включительно).
    """

    def __init__(
        self,
        field_name: str,
        required: bool = True,
        min_value: float | None = None,
        max_value: float | None = None,
    ):
        """
        Инициализирует чекер.

        Аргументы:
            field_name: имя поля в словаре результата аспекта.
            required: обязательно ли поле. По умолчанию True.
            min_value: минимально допустимое значение (включительно).
            max_value: максимально допустимое значение (включительно).
        """
        super().__init__(field_name, required)
        self.min_value = min_value
        self.max_value = max_value

    def _get_extra_params(self) -> dict[str, Any]:
        """
        Возвращает дополнительные параметры числового чекера.

        Эти параметры сохраняются в CheckerMeta.extra_params при сборке
        метаданных и передаются в конструктор при создании экземпляра
        машиной в ActionProductMachine._apply_checkers().

        Возвращает:
            dict с ключами min_value, max_value.
        """
        return {
            "min_value": self.min_value,
            "max_value": self.max_value,
        }

    def _validate_number(self, value: Any) -> float:
        """
        Проверяет, что значение является числом (int или float), и возвращает его.

        Аргументы:
            value: значение для проверки.

        Возвращает:
            value как число.

        Исключения:
            ValidationFieldError: если value не int и не float.
        """
        if not isinstance(value, (int, float)):
            raise ValidationFieldError(
                f"Поле '{self.field_name}' должно быть числом, получен {type(value).__name__}"
            )
        return value

    def _check_range(self, value: float) -> None:
        """
        Проверяет, что число находится в допустимом диапазоне.

        Аргументы:
            value: значение для проверки.

        Исключения:
            ValidationFieldError: если число вне диапазона.
        """
        if self.min_value is not None and value < self.min_value:
            raise ValidationFieldError(
                f"Поле '{self.field_name}' должно быть не меньше {self.min_value}"
            )
        if self.max_value is not None and value > self.max_value:
            raise ValidationFieldError(
                f"Поле '{self.field_name}' должно быть не больше {self.max_value}"
            )

    def _check_type_and_constraints(self, value: Any) -> None:
        """
        Проверяет тип (int или float) и применяет ограничения диапазона.

        Аргументы:
            value: значение для проверки (гарантированно не None).

        Исключения:
            ValidationFieldError: при нарушении типа или диапазона.
        """
        num_value = self._validate_number(value)
        self._check_range(num_value)


# ═════════════════════════════════════════════════════════════════════════════
# Функция-декоратор
# ═════════════════════════════════════════════════════════════════════════════


def result_float(
    field_name: str,
    required: bool = True,
    min_value: float | None = None,
    max_value: float | None = None,
) -> Any:
    """
    Декоратор метода-аспекта. Объявляет числовое поле (int/float) в результате аспекта.

    Записывает метаданные чекера в атрибут ``_checker_meta`` метода.
    MetadataBuilder собирает эти метаданные в ClassMetadata.checkers.
    Машина создаёт экземпляр ResultFloatChecker из CheckerMeta
    и вызывает checker.check(result_dict) при выполнении аспекта.

    Аргументы:
        field_name: имя поля в словаре результата аспекта.
        required: обязательно ли поле. По умолчанию True.
        min_value: минимально допустимое значение (включительно).
        max_value: максимально допустимое значение (включительно).

    Возвращает:
        Декоратор, записывающий _checker_meta в метод.

    Пример:
        @regular_aspect("Расчёт")
        @result_float("total", required=True, min_value=0.0)
        async def calculate(self, params, state, box, connections):
            return {"total": 1500.0}
    """
    checker = ResultFloatChecker(
        field_name=field_name,
        required=required,
        min_value=min_value,
        max_value=max_value,
    )
    meta = _build_checker_meta(checker)

    def decorator(func: Any) -> Any:
        if not hasattr(func, "_checker_meta"):
            func._checker_meta = []
        func._checker_meta.append(meta)
        return func

    return decorator
