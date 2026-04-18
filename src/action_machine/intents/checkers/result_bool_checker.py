# src/action_machine/intents/checkers/result_bool_checker.py
"""
Boolean result-field checker and ``result_bool`` decorator.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The module exposes two components:

1. **ResultBoolChecker**: validates that a result field is strictly boolean
   (``True``/``False``). Numeric values (``0``, ``1``), strings
   (``"true"``, ``"false"``), and other types are rejected.
   Instances are created by runtime from checker snapshot entries.

2. **result_bool**: decorator for aspect methods that writes checker metadata
   to method attribute ``_checker_meta``. Inspector/builder flow collects this
   metadata into checker snapshots used at runtime.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    @result_bool("is_valid")
            |
            v
    method._checker_meta append
            |
            v
    CheckerIntentInspector snapshot
            |
            v
    runtime creates ResultBoolChecker
            |
            v
    checker.check(result_dict)

═══════════════════════════════════════════════════════════════════════════════
USAGE AS DECORATOR
═══════════════════════════════════════════════════════════════════════════════

    @regular_aspect("Validate")
    @result_bool("is_valid", required=True)
    async def validate(self, params, state, box, connections):
        return {"is_valid": True}

═══════════════════════════════════════════════════════════════════════════════
USAGE BY RUNTIME
═══════════════════════════════════════════════════════════════════════════════

    checker = ResultBoolChecker("is_valid")
    checker.check({"is_valid": True})  # OK

═══════════════════════════════════════════════════════════════════════════════
PARAMETERS
═══════════════════════════════════════════════════════════════════════════════

    field_name : str — field name in aspect result dictionary.
    required : bool — whether field is required. Default ``True``.

No additional parameters are defined; ``_get_extra_params`` from
``ResultFieldChecker`` returns an empty dictionary.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Accepts only ``bool`` values.
- Reuses base required/None handling from ``ResultFieldChecker``.
- Checker metadata shape is consistent with other ``result_*`` decorators.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Raises ``ValidationFieldError`` when value is not ``bool``.
- Type check is strict: bool subclasses/compatible values are not coerced.


AI-CORE-BEGIN
ROLE: Boolean checker module for aspect result fields.
CONTRACT: Validate strict bool values and expose metadata via ``result_bool`` decorator.
INVARIANTS: Deterministic metadata shape and strict ``isinstance(value, bool)`` checks.
FLOW: decorator metadata -> checker snapshot -> runtime checker execution.
AI-CORE-END
"""

from typing import Any

from action_machine.intents.checkers.result_field_checker import ResultFieldChecker
from action_machine.intents.checkers.result_string_checker import _build_checker_meta
from action_machine.model.exceptions import ValidationFieldError


class ResultBoolChecker(ResultFieldChecker):
    """
    Checker for strict boolean result values.

    Accepts only ``True`` / ``False`` values; no coercion from other types.
    """

    def _check_type_and_constraints(self, value: Any) -> None:
        """
        Validate that ``value`` is a strict boolean.

        Args:
            value: value to validate (guaranteed non-None by base checker).

        Raises:
            ValidationFieldError: if ``value`` is not ``bool``.
        """
        if not isinstance(value, bool):
            raise ValidationFieldError(
                f"Parameter '{self.field_name}' must be boolean, got {type(value).__name__}"
            )


# ═════════════════════════════════════════════════════════════════════════════
# Decorator function
# ═════════════════════════════════════════════════════════════════════════════


def result_bool(
    field_name: str,
    required: bool = True,
) -> Any:
    """
    Decorator for an aspect method. Declares a boolean field in the aspect result.

    Writes checker metadata to the method attribute ``_checker_meta``.
    MetadataBuilder collects this metadata into checker snapshot (GraphCoordinator.get_checkers).
    The machine creates a ResultBoolChecker instance from checker snapshot entry and calls
    checker.check(result_dict) when the aspect executes.

    Args:
        field_name: the field name in the aspect result dict.
        required: whether the field is required. Defaults to True.

    Returns:
        A decorator that writes _checker_meta to the method.

    Example:
        @regular_aspect("Validation")
        @result_bool("is_valid", required=True)
        async def validate(self, params, state, box, connections):
            return {"is_valid": True}
    """
    checker = ResultBoolChecker(
        field_name=field_name,
        required=required,
    )
    meta = _build_checker_meta(checker)

    def decorator(func: Any) -> Any:
        if not hasattr(func, "_checker_meta"):
            func._checker_meta = []
        func._checker_meta.append(meta)
        return func

    return decorator
