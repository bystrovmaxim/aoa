# src/action_machine/intents/checkers/result_float_checker.py
"""
Чекер для числовых полей (int/float) результата аспекта и функция-декоратор result_float.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Модуль содержит два компонента:

1. **ResultFloatChecker** — класс checkerа. Checks, что поле результата
   является числом (int или float) и лежит в заданном диапазоне.
   Создаётся машиной из checker snapshot entry при выполнении аспекта.

2. **result_float** — функция-декоратор. Применяется к methodу-аспекту
   и записывает метаданные checkerа в атрибут ``_checker_meta`` methodа.
   MetadataBuilder собирает эти метаданные в checker snapshot (GateCoordinator.get_checkers).

═══════════════════════════════════════════════════════════════════════════════
USAGE КАК ДЕКОРАТОР
═══════════════════════════════════════════════════════════════════════════════

    @regular_aspect("Расчёт")
    @result_float("total", required=True, min_value=0.0)
    async def calculate(self, params, state, box, connections):
        return {"total": 1500.0}

═══════════════════════════════════════════════════════════════════════════════
USAGE МАШИНОЙ
═══════════════════════════════════════════════════════════════════════════════

    checker = ResultFloatChecker("total", min_value=0.0)
    checker.check({"total": 1500.0})  # OK

═══════════════════════════════════════════════════════════════════════════════
PARAMETERS
═══════════════════════════════════════════════════════════════════════════════

    field_name : str — имя поля в словаре результата аспекта.
    required : bool — required ли поле. По умолчанию True.
    min_value : float | None — минимально допустимое значение (включительно).
    max_value : float | None — максимально допустимое значение (включительно).

═══════════════════════════════════════════════════════════════════════════════
ERRORS
═══════════════════════════════════════════════════════════════════════════════

    ValidationFieldError — значение не int и не float; значение вне диапазона.


AI-CORE-BEGIN
ROLE: module result_float_checker
CONTRACT: Keep runtime behavior unchanged; decorators/inspectors expose metadata consumed by coordinator/machine.
INVARIANTS: Validate declarations early and provide deterministic metadata shape.
FLOW: declarations -> inspector snapshot -> coordinator cache -> runtime usage.
AI-CORE-END
"""

from typing import Any

from action_machine.intents.checkers.result_field_checker import ResultFieldChecker
from action_machine.intents.checkers.result_string_checker import _build_checker_meta
from action_machine.model.exceptions import ValidationFieldError


class ResultFloatChecker(ResultFieldChecker):
    """
    Checks, что значение является числом (int или float) и лежит в заданном диапазоне.

    Создаётся машиной из checker snapshot entry при выполнении аспекта.

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
        Инициализирует checker.

        Args:
            field_name: имя поля в словаре результата аспекта.
            required: required ли поле. По умолчанию True.
            min_value: минимально допустимое значение (включительно).
            max_value: максимально допустимое значение (включительно).
        """
        super().__init__(field_name, required)
        self.min_value = min_value
        self.max_value = max_value

    def _get_extra_params(self) -> dict[str, Any]:
        """
        Returns дополнительные параметры числового checkerа.

        Эти параметры сохраняются в snapshot-метаданных checkerа при сборке
        метаданных и передаются в конструктор при создании экземпляра
        машиной в ActionProductMachine._apply_checkers().

        Returns:
            dict с ключами min_value, max_value.
        """
        return {
            "min_value": self.min_value,
            "max_value": self.max_value,
        }

    def _validate_number(self, value: Any) -> float:
        """
        Checks, что значение является числом (int или float), и возвращает его.

        Args:
            value: значение для проверки.

        Returns:
            value как число.

        Raises:
            ValidationFieldError: если value не int и не float.
        """
        if not isinstance(value, (int, float)):
            raise ValidationFieldError(
                f"Поле '{self.field_name}' должно быть числом, got {type(value).__name__}"
            )
        return value

    def _check_range(self, value: float) -> None:
        """
        Checks, что число находится в допустимом диапазоне.

        Args:
            value: значение для проверки.

        Raises:
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
        Checks тип (int или float) и применяет ограничения диапазона.

        Args:
            value: значение для проверки (гарантированно не None).

        Raises:
            ValidationFieldError: при нарушении типа или диапазона.
        """
        num_value = self._validate_number(value)
        self._check_range(num_value)


# ═════════════════════════════════════════════════════════════════════════════
# Decorator function
# ═════════════════════════════════════════════════════════════════════════════


def result_float(
    field_name: str,
    required: bool = True,
    min_value: float | None = None,
    max_value: float | None = None,
) -> Any:
    """
    Декоратор methodа-аспекта. Объявляет числовое поле (int/float) в результате аспекта.

    Записывает метаданные checkerа в атрибут ``_checker_meta`` methodа.
    MetadataBuilder собирает эти метаданные в checker snapshot (GateCoordinator.get_checkers).
    Машина создаёт экземпляр ResultFloatChecker из checker snapshot entry
    и вызывает checker.check(result_dict) при выполнении аспекта.

    Args:
        field_name: имя поля в словаре результата аспекта.
        required: required ли поле. По умолчанию True.
        min_value: минимально допустимое значение (включительно).
        max_value: максимально допустимое значение (включительно).

    Returns:
        Декоратор, записывающий _checker_meta в method.

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
