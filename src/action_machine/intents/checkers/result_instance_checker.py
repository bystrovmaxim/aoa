# src/action_machine/intents/checkers/result_instance_checker.py
"""
Instance-type result checker and ``result_instance`` decorator.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The module provides two components:

1. **ResultInstanceChecker**: validates that a result field is an instance
   of one expected class (or one class from an expected tuple). Runtime creates
   checker instances from checker snapshot entries.

2. **result_instance**: decorator for aspect methods that appends checker
   metadata to method attribute ``_checker_meta``. Inspector/builder flow
   collects metadata into checker snapshots consumed by runtime.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    @result_instance(...)
            |
            v
    method._checker_meta append
            |
            v
    CheckerIntentInspector snapshot
            |
            v
    runtime creates ResultInstanceChecker
            |
            v
    checker.check(result_dict)

═══════════════════════════════════════════════════════════════════════════════
USAGE AS DECORATOR
═══════════════════════════════════════════════════════════════════════════════

    @regular_aspect("Get user")
    @result_instance("user", User, required=True)
    async def get_user(self, params, state, box, connections):
        return {"user": User(id=1, name="John")}

═══════════════════════════════════════════════════════════════════════════════
USAGE BY RUNTIME
═══════════════════════════════════════════════════════════════════════════════

    checker = ResultInstanceChecker("user", User)
    checker.check({"user": User(id=1, name="John")})  # OK

═══════════════════════════════════════════════════════════════════════════════
PARAMETERS
═══════════════════════════════════════════════════════════════════════════════

    field_name : str — field name in aspect result dictionary.
    expected_class : type | tuple[type, ...] — expected class (or class tuple).
    required : bool — whether field is required. Default ``True``.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Uses ``isinstance`` semantics (supports inheritance).
- Supports one expected class or a tuple of accepted classes.
- Reuses required/non-null policy from ``ResultFieldChecker``.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Raises ``ValidationFieldError`` when value is not instance of expected class.
- Error message includes field name and actual type for diagnostics.


AI-CORE-BEGIN
ROLE: Instance-type checker module for aspect result fields.
CONTRACT: Validate instance membership and expose metadata via ``result_instance``.
INVARIANTS: Deterministic metadata shape and ``isinstance``-based checks.
FLOW: decorator metadata -> checker snapshot -> runtime checker execution.
AI-CORE-END
"""

from typing import Any

from action_machine.intents.checkers.result_field_checker import ResultFieldChecker
from action_machine.intents.checkers.result_string_checker import _build_checker_meta
from action_machine.model.exceptions import ValidationFieldError


class ResultInstanceChecker(ResultFieldChecker):
    """
    Checker validating instance membership against expected class spec.
    """

    def __init__(
        self,
        field_name: str,
        expected_class: type[Any] | tuple[type[Any], ...],
        required: bool = True,
    ) -> None:
        """
        Initialize instance checker.

        Args:
            field_name: field name in aspect result dictionary.
            expected_class: expected class or tuple of classes.
            required: whether field is required.
        """
        super().__init__(field_name, required)
        self.expected_class = expected_class

    def _get_extra_params(self) -> dict[str, Any]:
        """
        Return constructor params for snapshot serialization.

        Returns:
            Dictionary with ``expected_class`` key.
        """
        return {
            "expected_class": self.expected_class,
        }

    def _check_type_and_constraints(self, value: Any) -> None:
        """
        Validate that ``value`` is instance of expected class spec.

        Args:
            value: value to validate (guaranteed non-None by base checker).

        Raises:
            ValidationFieldError: if value is not instance of expected class.
        """
        if not isinstance(value, self.expected_class):
            if isinstance(self.expected_class, tuple):
                names = ", ".join(cls.__name__ for cls in self.expected_class)
                raise ValidationFieldError(
                    f"Field '{self.field_name}' must be an instance of one of: {names}, "
                    f"got {type(value).__name__}"
                )
            raise ValidationFieldError(
                f"Field '{self.field_name}' must be an instance of class {self.expected_class.__name__}, "
                f"got {type(value).__name__}"
            )


# ═════════════════════════════════════════════════════════════════════════════
# Decorator function
# ═════════════════════════════════════════════════════════════════════════════


def result_instance(
    field_name: str,
    expected_class: type[Any] | tuple[type[Any], ...],
    required: bool = True,
) -> Any:
    """
    Decorator for aspect methods declaring class-instance result field.

    Writes checker metadata to method attribute ``_checker_meta``.
    Inspector/builder flow collects metadata into checker snapshots, then
    runtime creates ``ResultInstanceChecker`` and calls ``checker.check(result_dict)``.

    Args:
        field_name: field name in aspect result dictionary.
        expected_class: expected class or tuple of classes.
        required: whether field is required.

    Returns:
        Decorator function that appends checker metadata to method.

    Example:
        @regular_aspect("Get user")
        @result_instance("user", User, required=True)
        async def get_user(self, params, state, box, connections):
            return {"user": User(id=1, name="John")}

        # Multiple accepted classes:
        @regular_aspect("Get data")
        @result_instance("data", (dict, list), required=True)
        async def get_data(self, params, state, box, connections):
            return {"data": {"key": "value"}}
    """
    checker = ResultInstanceChecker(
        field_name=field_name,
        expected_class=expected_class,
        required=required,
    )
    meta = _build_checker_meta(checker)

    def decorator(func: Any) -> Any:
        if not hasattr(func, "_checker_meta"):
            func._checker_meta = []
        func._checker_meta.append(meta)
        return func

    return decorator
