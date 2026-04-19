# src/action_machine/intents/checkers/field_string_checker.py
"""
String result-field checker (:class:`FieldStringChecker`).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Validates that a result field is a string and satisfies configured rules:
``not_empty``, ``min_length``, ``max_length``. Runtime creates checker instances
from checker snapshot entries. For the ``@result_string`` decorator, see
``result_string_decorator``.

═══════════════════════════════════════════════════════════════════════════════
USAGE BY RUNTIME
═══════════════════════════════════════════════════════════════════════════════

    # ActionProductMachine._apply_checkers() creates checker instance:
    checker = FieldStringChecker("name", required=True, min_length=3)
    checker.check({"name": "John"})  # OK

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Accepts only ``str`` values.
- Applies ``not_empty`` check before length checks.
- Applies inclusive length bounds when configured.
- Reuses required/non-null handling from ``BaseFieldChecker``.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Raises ``ValidationFieldError`` when value is not string, empty under
  ``not_empty=True``, or outside length limits.

AI-CORE-BEGIN
ROLE: String checker implementation for aspect result fields.
CONTRACT: Validate string values; snapshot hydration matches ``result_string`` metadata.
INVARIANTS: Deterministic metadata shape and ordered string constraints.
FLOW: snapshot -> FieldStringChecker -> check(result_dict).
AI-CORE-END
"""

from typing import Any

from action_machine.intents.checkers.base_field_checker import BaseFieldChecker
from action_machine.model.exceptions import ValidationFieldError


class FieldStringChecker(BaseFieldChecker):
    """
    Checker for string values with emptiness and length constraints.
    """

    def __init__(
        self,
        field_name: str,
        required: bool = True,
        min_length: int | None = None,
        max_length: int | None = None,
        not_empty: bool = False,
    ):
        """
        Initialize string checker.

        Args:
            field_name: field name in aspect result dictionary.
            required: whether field is required.
            min_length: minimum allowed length (inclusive).
            max_length: maximum allowed length (inclusive).
            not_empty: if ``True``, empty strings are rejected.
        """
        super().__init__(field_name, required)
        self.min_length = min_length
        self.max_length = max_length
        self.not_empty = not_empty

    def _get_extra_params(self) -> dict[str, Any]:
        """
        Return checker constructor params for snapshot serialization.

        Returns:
            Dict with ``min_length``, ``max_length``, and ``not_empty``.
        """
        return {
            "min_length": self.min_length,
            "max_length": self.max_length,
            "not_empty": self.not_empty,
        }

    def _validate_string_type(self, value: Any) -> str:
        """
        Validate that value is string and return it.

        Args:
            value: value to validate.

        Returns:
            String value.

        Raises:
            ValidationFieldError: if value is not string.
        """
        if not isinstance(value, str):
            raise ValidationFieldError(
                f"Parameter '{self.field_name}' must be a string, got {type(value).__name__}"
            )
        return value

    def _check_empty(self, value: str) -> None:
        """
        Validate non-empty constraint when ``not_empty=True``.

        Args:
            value: string value to validate.

        Raises:
            ValidationFieldError: if string is empty.
        """
        if self.not_empty and len(value) == 0:
            raise ValidationFieldError(f"Parameter '{self.field_name}' cannot be empty")

    def _check_length(self, value: str) -> None:
        """
        Validate string length bounds.

        Args:
            value: string value to validate.

        Raises:
            ValidationFieldError: if length is outside allowed range.
        """
        if self.min_length is not None and len(value) < self.min_length:
            raise ValidationFieldError(
                f"Length of parameter '{self.field_name}' must be greater than or equal to {self.min_length}"
            )
        if self.max_length is not None and len(value) > self.max_length:
            raise ValidationFieldError(
                f"Length of parameter '{self.field_name}' must be less than or equal to {self.max_length}"
            )

    def _check_type_and_constraints(self, value: Any) -> None:
        """
        Run full validation: type, emptiness, then length bounds.

        Args:
            value: value to validate (guaranteed non-None by base checker).

        Raises:
            ValidationFieldError: on any constraint violation.
        """
        str_value = self._validate_string_type(value)
        self._check_empty(str_value)
        self._check_length(str_value)
