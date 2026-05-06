# src/action_machine/intents/checkers/result_bool_decorator.py
"""
``result_bool`` — attach strict-boolean field checker metadata to aspect methods.

Includes :class:`FieldBoolChecker`, which validates that a result field is strictly
boolean (``True``/``False``). Numeric values, strings, and other types are rejected.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Decorator that appends metadata to ``method._checker_meta``. Inspector collects
snapshots; runtime builds :class:`FieldBoolChecker` and runs ``checker.check(result_dict)``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    @result_bool(...)
            |
            v
    method._checker_meta append
            |
            v
    ``CheckerGraphNode`` facet metadata
            |
            v
    runtime creates FieldBoolChecker
            |
            v
    checker.check(result_dict)

═══════════════════════════════════════════════════════════════════════════════
USAGE
═══════════════════════════════════════════════════════════════════════════════

    @regular_aspect("Validate")
    @result_bool("is_valid", required=True)
    async def validate(self, params, state, box, connections):
        return {"is_valid": True}

    checker = FieldBoolChecker("is_valid")
    checker.check({"is_valid": True})  # OK
"""

from __future__ import annotations

from typing import Any

from action_machine.exceptions.validation_field_error import ValidationFieldError


class FieldBoolChecker:
    """
    Checker for strict boolean result values.

    Accepts only ``True`` / ``False`` values; no coercion from other types.

    Self-contained implementation; runtime uses ``(field_name, required=...)`` and ``.check(result_dict)``.
    """

    __slots__ = ("field_name", "required")

    def __init__(self, field_name: str, required: bool = True) -> None:
        self.field_name = field_name
        self.required = required

    def check(self, result: dict[str, Any]) -> None:
        """Validate one boolean field in ``result`` (same contract as other field checkers)."""
        value = result.get(self.field_name)
        if value is None:
            if self.required:
                raise ValidationFieldError(
                    f"Missing required parameter: '{self.field_name}'",
                    field=self.field_name,
                )
            return
        if not isinstance(value, bool):
            raise ValidationFieldError(f"Parameter '{self.field_name}' must be boolean, got {type(value).__name__}")


def result_bool(
    field_name: str,
    required: bool = True,
) -> Any:
    """
    Decorator for an aspect method. Declares a boolean field in the aspect result.

    Writes checker metadata to the method attribute ``_checker_meta``.
    Regular aspects wire ``_checker_meta`` into ``CheckerGraphNode`` rows when the interchange graph is built.
    The machine creates a FieldBoolChecker instance from checker snapshot entry and calls
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
    meta: dict[str, Any] = {
        "checker_class": FieldBoolChecker,
        "field_name": field_name,
        "required": required,
    }

    def decorator(func: Any) -> Any:
        if not hasattr(func, "_checker_meta"):
            func._checker_meta = []
        func._checker_meta.append(meta)
        return func

    return decorator
