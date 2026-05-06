# src/action_machine/intents/checkers/result_float_decorator.py
"""
``result_float`` — attach numeric (int/float) field checker metadata to aspect methods.

Includes :class:`FieldFloatChecker`, which validates ``int`` / ``float`` values with
optional inclusive ``min_value`` / ``max_value`` bounds.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Decorator that appends metadata to ``method._checker_meta``. Inspector collects
snapshots; runtime builds :class:`FieldFloatChecker` and runs ``checker.check(result_dict)``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    @result_float(...)
          |
          v
    method._checker_meta append
          |
          v
    ``CheckerGraphNode`` graph node metadata
          |
          v
    runtime creates FieldFloatChecker
          |
          v
    checker.check(result_dict)

═══════════════════════════════════════════════════════════════════════════════
USAGE
═══════════════════════════════════════════════════════════════════════════════

    @regular_aspect("Calculate")
    @result_float("total", required=True, min_value=0.0)
    async def calculate(self, params, state, box, connections):
        return {"total": 1500.0}

    checker = FieldFloatChecker("total", min_value=0.0)
    checker.check({"total": 1500.0})  # OK
"""

from __future__ import annotations

from typing import Any

from action_machine.exceptions.validation_field_error import ValidationFieldError


class FieldFloatChecker:
    """
    Checker for numeric values (int/float) with optional range constraints.

    Self-contained implementation; runtime uses the usual constructor kwargs and ``.check(result_dict)``.
    """

    __slots__ = ("field_name", "max_value", "min_value", "required")

    def __init__(
        self,
        field_name: str,
        required: bool = True,
        min_value: float | None = None,
        max_value: float | None = None,
    ) -> None:
        self.field_name = field_name
        self.required = required
        self.min_value = min_value
        self.max_value = max_value

    def _get_extra_params(self) -> dict[str, Any]:
        """Return checker constructor params for snapshot serialization / tests."""
        return {
            "min_value": self.min_value,
            "max_value": self.max_value,
        }

    def check(self, result: dict[str, Any]) -> None:
        """Validate one numeric field in ``result``."""
        value = result.get(self.field_name)
        if value is None:
            if self.required:
                raise ValidationFieldError(
                    f"Missing required parameter: '{self.field_name}'",
                    field=self.field_name,
                )
            return
        num_value = self._validate_number(value)
        self._check_range(num_value)

    def _validate_number(self, value: Any) -> int | float:
        """
        Validate numeric type and return value.

        Args:
            value: value to validate.

        Returns:
            Numeric value.

        Raises:
            ValidationFieldError: if value is not ``int`` or ``float``.
        """
        if not isinstance(value, (int, float)):
            raise ValidationFieldError(f"Field '{self.field_name}' must be numeric, got {type(value).__name__}")
        return value

    def _check_range(self, value: int | float) -> None:
        """
        Validate that number is within configured inclusive bounds.

        Args:
            value: numeric value to validate.

        Raises:
            ValidationFieldError: if value is outside allowed range.
        """
        if self.min_value is not None and value < self.min_value:
            raise ValidationFieldError(f"Field '{self.field_name}' must be greater than or equal to {self.min_value}")
        if self.max_value is not None and value > self.max_value:
            raise ValidationFieldError(f"Field '{self.field_name}' must be less than or equal to {self.max_value}")


def result_float(
    field_name: str,
    required: bool = True,
    min_value: float | None = None,
    max_value: float | None = None,
) -> Any:
    """
    Decorator for aspect methods declaring a numeric result field.

    Writes checker metadata to method attribute ``_checker_meta``.
    Inspector/builder flow collects metadata into checker snapshots, then
    runtime creates ``FieldFloatChecker`` and calls ``checker.check(result_dict)``.

    Args:
        field_name: field name in aspect result dictionary.
        required: whether field is required.
        min_value: minimum allowed value (inclusive).
        max_value: maximum allowed value (inclusive).

    Returns:
        Decorator function that appends checker metadata to method.

    Example:
        @regular_aspect("Calculate")
        @result_float("total", required=True, min_value=0.0)
        async def calculate(self, params, state, box, connections):
            return {"total": 1500.0}
    """
    meta: dict[str, Any] = {
        "checker_class": FieldFloatChecker,
        "field_name": field_name,
        "required": required,
        "min_value": min_value,
        "max_value": max_value,
    }

    def decorator(func: Any) -> Any:
        if not hasattr(func, "_checker_meta"):
            func._checker_meta = []
        func._checker_meta.append(meta)
        return func

    return decorator
