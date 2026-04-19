# src/action_machine/intents/checkers/result_float_checker.py
"""
Numeric result-field checker (int/float) — :class:`FieldFloatChecker`.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Validates that a result field is numeric (``int`` or ``float``) and inside optional
inclusive range bounds. Runtime creates checker instances from snapshot metadata.
For the ``@result_float`` decorator, see ``result_float_decorator``.

═══════════════════════════════════════════════════════════════════════════════
USAGE BY RUNTIME
═══════════════════════════════════════════════════════════════════════════════

    checker = FieldFloatChecker("total", min_value=0.0)
    checker.check({"total": 1500.0})  # OK

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Accepts ``int`` and ``float`` values.
- Applies inclusive bound checks when ``min_value`` / ``max_value`` are set.
- Reuses required/non-null handling from ``BaseFieldChecker``.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Raises ``ValidationFieldError`` when value is non-numeric or outside range.
- Python treats ``bool`` as ``int``; therefore ``True``/``False`` pass type check.

AI-CORE-BEGIN
ROLE: Numeric checker implementation for aspect result fields.
CONTRACT: Validate numeric values; snapshot hydration matches ``result_float`` metadata.
INVARIANTS: Deterministic metadata shape and inclusive bound enforcement.
FLOW: snapshot -> FieldFloatChecker -> check(result_dict).
AI-CORE-END
"""

from typing import Any

from action_machine.intents.checkers.result_field_checker import BaseFieldChecker
from action_machine.model.exceptions import ValidationFieldError


class FieldFloatChecker(BaseFieldChecker):
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
