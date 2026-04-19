# src/action_machine/intents/checkers/result_int_checker.py
"""
Integer result-field checker (:class:`FieldIntChecker`).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Validates that a result field is an integer and satisfies optional inclusive
range limits. Runtime creates checker instances from checker snapshot entries.
For the ``@result_int`` decorator, see ``result_int_decorator``.

═══════════════════════════════════════════════════════════════════════════════
USAGE BY RUNTIME
═══════════════════════════════════════════════════════════════════════════════

    checker = FieldIntChecker("count", min_value=0)
    checker.check({"count": 42})  # OK

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Accepts only ``int`` values by ``isinstance(value, int)`` rule.
- Applies inclusive range checks when bounds are configured.
- Reuses required/non-null policy from ``BaseFieldChecker``.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Raises ``ValidationFieldError`` when value is not integer or violates bounds.
- Python treats ``bool`` as subclass of ``int``; bool values pass type check.

AI-CORE-BEGIN
ROLE: Integer checker implementation for aspect result fields.
CONTRACT: Validate integer values; snapshot hydration matches ``result_int`` metadata.
INVARIANTS: Deterministic metadata shape and inclusive bound enforcement.
FLOW: snapshot -> FieldIntChecker -> check(result_dict).
AI-CORE-END
"""

from typing import Any

from action_machine.intents.checkers.result_field_checker import BaseFieldChecker
from action_machine.model.exceptions import ValidationFieldError


class FieldIntChecker(BaseFieldChecker):
    """
    Checker for integer values with optional range constraints.
    """

    def __init__(
        self,
        field_name: str,
        required: bool = True,
        min_value: int | None = None,
        max_value: int | None = None,
    ):
        """
        Initialize integer checker.

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

    def _validate_int(self, value: Any) -> int:
        """
        Validate integer type and return value.

        Args:
            value: value to validate.

        Returns:
            Integer value.

        Raises:
            ValidationFieldError: if value is not ``int``.
        """
        if not isinstance(value, int):
            raise ValidationFieldError(
                f"Parameter '{self.field_name}' must be an integer, got {type(value).__name__}"
            )
        return value

    def _check_range(self, value: int) -> None:
        """
        Validate that integer is within configured inclusive bounds.

        Args:
            value: integer value to validate.

        Raises:
            ValidationFieldError: if value is outside allowed range.
        """
        if self.min_value is not None and value < self.min_value:
            raise ValidationFieldError(
                f"Parameter '{self.field_name}' must be greater than or equal to {self.min_value}"
            )
        if self.max_value is not None and value > self.max_value:
            raise ValidationFieldError(
                f"Parameter '{self.field_name}' must be less than or equal to {self.max_value}"
            )

    def _check_type_and_constraints(self, value: Any) -> None:
        """
        Validate integer type and range constraints.

        Args:
            value: value to validate (guaranteed non-None by base checker).

        Raises:
            ValidationFieldError: on type or range violation.
        """
        int_value = self._validate_int(value)
        self._check_range(int_value)
