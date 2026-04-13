# src/action_machine/checkers/result_int_checker.py
"""
Чекер для целочисленных полей результата аспекта и функция-декоратор result_int.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Модуль содержит два компонента:

1. **ResultIntChecker** — класс checkerа. Checks, что поле результата
   является целым числом (int) и лежит в заданном диапазоне.
   Создаётся машиной из checker snapshot entry при выполнении аспекта.

2. **result_int** — функция-декоратор. Применяется к methodу-аспекту
   и записывает метаданные checkerа в атрибут ``_checker_meta`` methodа.
   MetadataBuilder собирает эти метаданные в checker snapshot (GateCoordinator.get_checkers).

═══════════════════════════════════════════════════════════════════════════════
USAGE КАК ДЕКОРАТОР
═══════════════════════════════════════════════════════════════════════════════

    @regular_aspect("Подсчёт")
    @result_int("count", required=True, min_value=0, max_value=100)
    async def count_items(self, params, state, box, connections):
        return {"count": 42}

═══════════════════════════════════════════════════════════════════════════════
USAGE МАШИНОЙ
═══════════════════════════════════════════════════════════════════════════════

    checker = ResultIntChecker("count", min_value=0)
    checker.check({"count": 42})  # OK

═══════════════════════════════════════════════════════════════════════════════
PARAMETERS
═══════════════════════════════════════════════════════════════════════════════

    field_name : str — имя поля в словаре результата аспекта.
    required : bool — required ли поле. По умолчанию True.
    min_value : int | None — минимально допустимое значение (включительно).
    max_value : int | None — максимально допустимое значение (включительно).

═══════════════════════════════════════════════════════════════════════════════
ERRORS
═══════════════════════════════════════════════════════════════════════════════

    ValidationFieldError — значение не int; значение вне диапазона.


AI-CORE-BEGIN
ROLE: module result_int_checker
CONTRACT: Keep runtime behavior unchanged; decorators/inspectors expose metadata consumed by coordinator/machine.
INVARIANTS: Validate declarations early and provide deterministic metadata shape.
FLOW: declarations -> inspector snapshot -> coordinator cache -> runtime usage.
AI-CORE-END
"""

from typing import Any

from action_machine.core.exceptions import ValidationFieldError

from .result_field_checker import ResultFieldChecker
from .result_string_checker import _build_checker_meta


class ResultIntChecker(ResultFieldChecker):
    """
    Checks, что значение является целым числом и лежит в заданном диапазоне.

    Создаётся машиной из checker snapshot entry при выполнении аспекта.

    Атрибуты:
        min_value : int | None — минимально допустимое значение (включительно).
        max_value : int | None — максимально допустимое значение (включительно).
    """

    def __init__(
        self,
        field_name: str,
        required: bool = True,
        min_value: int | None = None,
        max_value: int | None = None,
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
        Returns дополнительные параметры целочисленного checkerа.

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

    def _validate_int(self, value: Any) -> int:
        """
        Checks, что значение является целым числом, и возвращает его.

        Args:
            value: значение для проверки.

        Returns:
            value как int.

        Raises:
            ValidationFieldError: если value не int.
        """
        if not isinstance(value, int):
            raise ValidationFieldError(
                f"Параметр '{self.field_name}' должен быть целым числом, got {type(value).__name__}"
            )
        return value

    def _check_range(self, value: int) -> None:
        """
        Checks, что целое число находится в допустимом диапазоне.

        Args:
            value: значение для проверки.

        Raises:
            ValidationFieldError: если число вне диапазона.
        """
        if self.min_value is not None and value < self.min_value:
            raise ValidationFieldError(
                f"Параметр '{self.field_name}' должен быть не меньше {self.min_value}"
            )
        if self.max_value is not None and value > self.max_value:
            raise ValidationFieldError(
                f"Параметр '{self.field_name}' должен быть не больше {self.max_value}"
            )

    def _check_type_and_constraints(self, value: Any) -> None:
        """
        Checks тип (int) и применяет ограничения диапазона.

        Args:
            value: значение для проверки (гарантированно не None).

        Raises:
            ValidationFieldError: при нарушении типа или диапазона.
        """
        int_value = self._validate_int(value)
        self._check_range(int_value)


# ═════════════════════════════════════════════════════════════════════════════
# Decorator function
# ═════════════════════════════════════════════════════════════════════════════


def result_int(
    field_name: str,
    required: bool = True,
    min_value: int | None = None,
    max_value: int | None = None,
) -> Any:
    """
    Декоратор methodа-аспекта. Объявляет целочисленное поле в результате аспекта.

    Записывает метаданные checkerа в атрибут ``_checker_meta`` methodа.
    MetadataBuilder собирает эти метаданные в checker snapshot (GateCoordinator.get_checkers).
    Машина создаёт экземпляр ResultIntChecker из checker snapshot entry
    и вызывает checker.check(result_dict) при выполнении аспекта.

    Args:
        field_name: имя поля в словаре результата аспекта.
        required: required ли поле. По умолчанию True.
        min_value: минимально допустимое значение (включительно).
        max_value: максимально допустимое значение (включительно).

    Returns:
        Декоратор, записывающий _checker_meta в method.

    Пример:
        @regular_aspect("Подсчёт")
        @result_int("count", required=True, min_value=0, max_value=1000)
        async def count_items(self, params, state, box, connections):
            return {"count": 42}
    """
    checker = ResultIntChecker(
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
