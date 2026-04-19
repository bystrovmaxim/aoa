# src/action_machine/intents/checkers/result_bool_decorator.py
"""
``result_bool`` — attach strict-boolean field checker metadata to aspect methods.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Decorator that appends metadata to ``method._checker_meta``. Inspector collects
snapshots; runtime builds :class:`~action_machine.intents.checkers.result_bool_checker.FieldBoolChecker`
and runs ``checker.check(result_dict)``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    @result_bool(...)
            |
            v
    method._checker_meta append
            |
            v
    CheckerIntentInspector snapshot
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

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Boolean checker decorator for aspect methods.
CONTRACT: Write ``_checker_meta`` row for FieldBoolChecker snapshot replay.
INVARIANTS: Metadata keys match FieldBoolChecker constructor / snapshot hydration.
FLOW: decorator -> _checker_meta -> inspector -> runtime check.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from typing import Any

from action_machine.intents.checkers.result_bool_checker import FieldBoolChecker


def result_bool(
    field_name: str,
    required: bool = True,
) -> Any:
    """
    Decorator for an aspect method. Declares a boolean field in the aspect result.

    Writes checker metadata to the method attribute ``_checker_meta``.
    MetadataBuilder collects this metadata into checker snapshot (GraphCoordinator.get_checkers).
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
