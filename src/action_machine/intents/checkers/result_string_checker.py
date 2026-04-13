# src/action_machine/intents/checkers/result_string_checker.py
"""
String result-field checker and ``result_string`` decorator.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The module exposes two components:

1. **ResultStringChecker**: validates that a result field is a string and
   satisfies configured rules: ``not_empty``, ``min_length``, ``max_length``.
   Runtime creates checker instances from checker snapshot entries.

2. **result_string**: decorator for aspect methods that appends checker
   metadata to method attribute ``_checker_meta``. Inspector/builder flow
   collects metadata into checker snapshots consumed by runtime.

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
    runtime creates ResultStringChecker
           |
           v
    checker.check(result_dict)

═══════════════════════════════════════════════════════════════════════════════
USAGE AS DECORATOR
═══════════════════════════════════════════════════════════════════════════════

    @regular_aspect("Validation")
    @result_string("name", required=True, min_length=3)
    async def validate(self, params, state, box, connections):
        return {"name": "John"}

Decorator order with ``@regular_aspect`` is not significant: each decorator
writes different metadata onto the same function object.

═══════════════════════════════════════════════════════════════════════════════
USAGE BY RUNTIME
═══════════════════════════════════════════════════════════════════════════════

    # ActionProductMachine._apply_checkers() creates checker instance:
    checker = ResultStringChecker("name", required=True, min_length=3)
    checker.check({"name": "John"})  # OK

═══════════════════════════════════════════════════════════════════════════════
PARAMETERS
═══════════════════════════════════════════════════════════════════════════════

    field_name : str — field name in aspect result dictionary.
    required : bool — whether field is required. Default ``True``.
    min_length : int | None — minimum allowed string length.
    max_length : int | None — maximum allowed string length.
    not_empty : bool — if ``True``, empty string is rejected.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Accepts only ``str`` values.
- Applies ``not_empty`` check before length checks.
- Applies inclusive length bounds when configured.
- Reuses required/non-null handling from ``ResultFieldChecker``.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Raises ``ValidationFieldError`` when value is not string, empty under
  ``not_empty=True``, or outside length limits.


AI-CORE-BEGIN
ROLE: String checker module for aspect result fields.
CONTRACT: Validate string values and expose metadata via ``result_string`` decorator.
INVARIANTS: Deterministic metadata shape and ordered string constraints.
FLOW: decorator metadata -> checker snapshot -> runtime checker execution.
AI-CORE-END
"""

from typing import Any

from action_machine.intents.checkers.result_field_checker import ResultFieldChecker
from action_machine.model.exceptions import ValidationFieldError


class ResultStringChecker(ResultFieldChecker):
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


# ═════════════════════════════════════════════════════════════════════════════
# Decorator function
# ═════════════════════════════════════════════════════════════════════════════


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
    runtime creates ``ResultStringChecker`` and calls ``checker.check(result_dict)``.

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
    checker = ResultStringChecker(
        field_name=field_name,
        required=required,
        min_length=min_length,
        max_length=max_length,
        not_empty=not_empty,
    )
    meta = _build_checker_meta(checker)

    def decorator(func: Any) -> Any:
        if not hasattr(func, "_checker_meta"):
            func._checker_meta = []
        func._checker_meta.append(meta)
        return func

    return decorator


# ═════════════════════════════════════════════════════════════════════════════
# Helper metadata builder
# ═════════════════════════════════════════════════════════════════════════════


def _build_checker_meta(checker: ResultFieldChecker) -> dict[str, Any]:
    """
    Build checker metadata dictionary for ``_checker_meta``.

    Contains all parameters required for snapshot entry creation and runtime
    checker instantiation.

    Args:
        checker: checker instance with configured parameters.

    Returns:
        Dictionary with keys ``checker_class``, ``field_name``, ``required``,
        plus checker-specific extra parameters.
    """
    result: dict[str, Any] = {
        "checker_class": type(checker),
        "field_name": checker.field_name,
        "required": checker.required,
    }
    result.update(checker._get_extra_params())
    return result
