# src/action_machine/intents/checkers/result_float_checker.py
"""
Numeric result-field checker (int/float) and ``result_float`` decorator.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The module exposes two components:

1. **ResultFloatChecker**: validates that a result field is numeric
   (``int`` or ``float``) and inside optional inclusive range bounds.
   Runtime creates checker instances from snapshot metadata.

2. **result_float**: decorator for aspect methods that appends checker metadata
   to method attribute ``_checker_meta``. Inspector/builder flow collects this
   metadata into checker snapshots used by runtime.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    @result_float(...)
          |
          v
    method._checker_meta append
          |
          v
    CheckerIntentInspector snapshot
          |
          v
    runtime creates ResultFloatChecker
          |
          v
    checker.check(result_dict)

═══════════════════════════════════════════════════════════════════════════════
USAGE AS DECORATOR
═══════════════════════════════════════════════════════════════════════════════

    @regular_aspect("Calculate")
    @result_float("total", required=True, min_value=0.0)
    async def calculate(self, params, state, box, connections):
        return {"total": 1500.0}

═══════════════════════════════════════════════════════════════════════════════
USAGE BY RUNTIME
═══════════════════════════════════════════════════════════════════════════════

    checker = ResultFloatChecker("total", min_value=0.0)
    checker.check({"total": 1500.0})  # OK

═══════════════════════════════════════════════════════════════════════════════
PARAMETERS
═══════════════════════════════════════════════════════════════════════════════

    field_name : str — field name in aspect result dictionary.
    required : bool — whether field is required. Default ``True``.
    min_value : float | None — minimum allowed value (inclusive).
    max_value : float | None — maximum allowed value (inclusive).

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Accepts ``int`` and ``float`` values.
- Applies inclusive bound checks when ``min_value`` / ``max_value`` are set.
- Reuses required/non-null handling from ``ResultFieldChecker``.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Raises ``ValidationFieldError`` when value is non-numeric or outside range.
- Python treats ``bool`` as ``int``; therefore ``True``/``False`` pass type check.


AI-CORE-BEGIN
ROLE: Numeric checker module for aspect result fields.
CONTRACT: Validate numeric values and expose metadata via ``result_float`` decorator.
INVARIANTS: Deterministic metadata shape and inclusive bound enforcement.
FLOW: decorator metadata -> checker snapshot -> runtime checker execution.
AI-CORE-END
"""

from typing import Any

from action_machine.intents.checkers.result_field_checker import ResultFieldChecker
from action_machine.intents.checkers.result_string_checker import _build_checker_meta
from action_machine.model.exceptions import ValidationFieldError


class ResultFloatChecker(ResultFieldChecker):
    """
    Checker for numeric values (int/float) with optional range constraints.
    """

    def __init__(
        self,
        field_name: str,
        required: bool = True,
        min_value: float | None = None,
        max_value: float | None = None,
    ):
        """
        Initialize numeric checker.

        Args:
            field_name: field name in aspect result dictionary.
            required: whether field is required.
            min_value: minimum allowed value (inclusive).
            max_value: maximum allowed value (inclusive).
        """
        super().__init__(field_name, required)
        self.min_value = min_value
        self.max_value = max_value

    def _get_extra_params(self) -> dict[str, Any]:
        """
        Return checker constructor params for snapshot serialization.

        Returns:
            Dict with ``min_value`` and ``max_value``.
        """
        return {
            "min_value": self.min_value,
            "max_value": self.max_value,
        }

    def _validate_number(self, value: Any) -> float:
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
            raise ValidationFieldError(
                f"Field '{self.field_name}' must be numeric, got {type(value).__name__}"
            )
        return value

    def _check_range(self, value: float) -> None:
        """
        Validate that number is within configured inclusive bounds.

        Args:
            value: numeric value to validate.

        Raises:
            ValidationFieldError: if value is outside allowed range.
        """
        if self.min_value is not None and value < self.min_value:
            raise ValidationFieldError(
                f"Field '{self.field_name}' must be greater than or equal to {self.min_value}"
            )
        if self.max_value is not None and value > self.max_value:
            raise ValidationFieldError(
                f"Field '{self.field_name}' must be less than or equal to {self.max_value}"
            )

    def _check_type_and_constraints(self, value: Any) -> None:
        """
        Validate numeric type and range constraints.

        Args:
            value: value to validate (guaranteed non-None by base checker).

        Raises:
            ValidationFieldError: on type or range violation.
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
    Decorator for aspect methods declaring a numeric result field.

    Writes checker metadata to method attribute ``_checker_meta``.
    Inspector/builder flow collects metadata into checker snapshots, then
    runtime creates ``ResultFloatChecker`` and calls ``checker.check(result_dict)``.

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
