# src/action_machine/intents/checkers/result_int_checker.py
"""
Integer result-field checker and ``result_int`` decorator.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The module exposes two components:

1. **ResultIntChecker**: validates that a result field is an integer and
   satisfies optional inclusive range limits. Runtime creates checker instances
   from checker snapshot entries.

2. **result_int**: decorator for aspect methods that appends checker metadata
   to method attribute ``_checker_meta``. Inspector/builder flow collects this
   metadata into checker snapshots used by runtime.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    @result_int(...)
         |
         v
    method._checker_meta append
         |
         v
    CheckerIntentInspector snapshot
         |
         v
    runtime creates ResultIntChecker
         |
         v
    checker.check(result_dict)

═══════════════════════════════════════════════════════════════════════════════
USAGE AS DECORATOR
═══════════════════════════════════════════════════════════════════════════════

    @regular_aspect("Count")
    @result_int("count", required=True, min_value=0, max_value=100)
    async def count_items(self, params, state, box, connections):
        return {"count": 42}

═══════════════════════════════════════════════════════════════════════════════
USAGE BY RUNTIME
═══════════════════════════════════════════════════════════════════════════════

    checker = ResultIntChecker("count", min_value=0)
    checker.check({"count": 42})  # OK

═══════════════════════════════════════════════════════════════════════════════
PARAMETERS
═══════════════════════════════════════════════════════════════════════════════

    field_name : str — field name in aspect result dictionary.
    required : bool — whether field is required. Default ``True``.
    min_value : int | None — minimum allowed value (inclusive).
    max_value : int | None — maximum allowed value (inclusive).

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Accepts only ``int`` values by ``isinstance(value, int)`` rule.
- Applies inclusive range checks when bounds are configured.
- Reuses required/non-null policy from ``ResultFieldChecker``.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Raises ``ValidationFieldError`` when value is not integer or violates bounds.
- Python treats ``bool`` as subclass of ``int``; bool values pass type check.


AI-CORE-BEGIN
ROLE: Integer checker module for aspect result fields.
CONTRACT: Validate integer values and expose metadata via ``result_int`` decorator.
INVARIANTS: Deterministic metadata shape and inclusive bound enforcement.
FLOW: decorator metadata -> checker snapshot -> runtime checker execution.
AI-CORE-END
"""

from typing import Any

from action_machine.intents.checkers.result_field_checker import ResultFieldChecker
from action_machine.intents.checkers.result_string_checker import _build_checker_meta
from action_machine.model.exceptions import ValidationFieldError


class ResultIntChecker(ResultFieldChecker):
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
    Decorator for aspect methods declaring integer result field.

    Writes checker metadata to method attribute ``_checker_meta``.
    Inspector/builder flow collects metadata into checker snapshots, then
    runtime creates ``ResultIntChecker`` and calls ``checker.check(result_dict)``.

    Args:
        field_name: field name in aspect result dictionary.
        required: whether field is required.
        min_value: minimum allowed value (inclusive).
        max_value: maximum allowed value (inclusive).

    Returns:
        Decorator function that appends checker metadata to method.

    Example:
        @regular_aspect("Count")
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
