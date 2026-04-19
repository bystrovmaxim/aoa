# src/action_machine/intents/checkers/result_string_decorator.py
"""
``result_string`` — attach string field checker metadata to aspect methods.

Includes :class:`FieldStringChecker`, which validates string values with optional
``not_empty``, ``min_length``, and ``max_length`` constraints.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Decorator for aspect methods that appends checker metadata to
``method._checker_meta``. The inspector/builder collects it into checker
snapshots; runtime instantiates :class:`FieldStringChecker` and runs
``checker.check(result_dict)``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    @result_string(...)
           |
           v
    method._checker_meta append
           |
           v
    CheckerIntentInspector snapshot
           |
           v
    runtime creates FieldStringChecker
           |
           v
    checker.check(result_dict)

═══════════════════════════════════════════════════════════════════════════════
USAGE
═══════════════════════════════════════════════════════════════════════════════

Decorator order with ``@regular_aspect`` is not significant: each decorator
writes different metadata onto the same function object.

    @regular_aspect("Validation")
    @result_string("name", required=True, min_length=3)
    async def validate(self, params, state, box, connections):
        return {"name": "John"}

    checker = FieldStringChecker("name", required=True, min_length=3)
    checker.check({"name": "John"})  # OK

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: String checker implementation and decorator for aspect methods.
CONTRACT: Metadata keys match FieldStringChecker constructor / snapshot hydration.
INVARIANTS: Ordered string constraints; deterministic metadata shape.
FLOW: decorator -> _checker_meta -> inspector -> runtime check.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from typing import Any

from action_machine.model.exceptions import ValidationFieldError


class FieldStringChecker:
    """
    Checker for string values with emptiness and length constraints.

    Self-contained implementation; runtime uses the usual constructor kwargs and ``.check(result_dict)``.
    """

    __slots__ = ("field_name", "max_length", "min_length", "not_empty", "required")

    def __init__(
        self,
        field_name: str,
        required: bool = True,
        min_length: int | None = None,
        max_length: int | None = None,
        not_empty: bool = False,
    ) -> None:
        self.field_name = field_name
        self.required = required
        self.min_length = min_length
        self.max_length = max_length
        self.not_empty = not_empty

    def _get_extra_params(self) -> dict[str, Any]:
        """Return checker constructor params for snapshot serialization / tests."""
        return {
            "min_length": self.min_length,
            "max_length": self.max_length,
            "not_empty": self.not_empty,
        }

    def check(self, result: dict[str, Any]) -> None:
        """Validate one string field in ``result``."""
        value = result.get(self.field_name)
        if value is None:
            if self.required:
                raise ValidationFieldError(
                    f"Missing required parameter: '{self.field_name}'",
                    field=self.field_name,
                )
            return
        str_value = self._validate_string_type(value)
        self._check_empty(str_value)
        self._check_length(str_value)

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
            raise ValidationFieldError(f"Parameter '{self.field_name}' must be a string, got {type(value).__name__}")
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


def result_string(
    field_name: str,
    required: bool = True,
    min_length: int | None = None,
    max_length: int | None = None,
    not_empty: bool = False,
) -> Any:
    """
    Decorator for aspect methods declaring string result field.

    Writes checker metadata to method attribute ``_checker_meta``.
    Inspector/builder flow collects metadata into checker snapshots, then
    runtime creates ``FieldStringChecker`` and calls ``checker.check(result_dict)``.

    Args:
        field_name: field name in aspect result dictionary.
        required: whether field is required.
        min_length: minimum allowed length (inclusive).
        max_length: maximum allowed length (inclusive).
        not_empty: if ``True``, empty string is rejected.

    Returns:
        Decorator function that appends checker metadata to method.

    Example:
        @regular_aspect("Validation")
        @result_string("validated_user", required=True, min_length=1)
        async def validate(self, params, state, box, connections):
            return {"validated_user": params.user_id}
    """
    meta: dict[str, Any] = {
        "checker_class": FieldStringChecker,
        "field_name": field_name,
        "required": required,
        "min_length": min_length,
        "max_length": max_length,
        "not_empty": not_empty,
    }

    def decorator(func: Any) -> Any:
        if not hasattr(func, "_checker_meta"):
            func._checker_meta = []
        func._checker_meta.append(meta)
        return func

    return decorator
