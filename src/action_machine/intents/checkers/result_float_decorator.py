# src/action_machine/intents/checkers/result_float_decorator.py
"""
``result_float`` — attach numeric (int/float) field checker metadata to aspect methods.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Decorator that appends metadata to ``method._checker_meta``. Inspector collects
snapshots; runtime builds :class:`~action_machine.intents.checkers.result_float_checker.FieldFloatChecker`
and runs ``checker.check(result_dict)``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    @result_float(...)
          |
          v
    method._checker_meta append
          |
          v
    CheckerIntentInspector snapshot
          |
          v
    runtime creates FieldFloatChecker
          |
          v
    checker.check(result_dict)

═══════════════════════════════════════════════════════════════════════════════
USAGE
═══════════════════════════════════════════════════════════════════════════════

    @regular_aspect("Calculate")
    @result_float("total", required=True, min_value=0.0)
    async def calculate(self, params, state, box, connections):
        return {"total": 1500.0}

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Numeric checker decorator for aspect methods.
CONTRACT: Write ``_checker_meta`` row for FieldFloatChecker snapshot replay.
INVARIANTS: Metadata keys match FieldFloatChecker constructor / snapshot hydration.
FLOW: decorator -> _checker_meta -> inspector -> runtime check.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from typing import Any

from action_machine.intents.checkers.result_float_checker import FieldFloatChecker


def result_float(
    field_name: str,
    required: bool = True,
    min_value: float | None = None,
    max_value: float | None = None,
) -> Any:
    """
    Decorator for aspect methods declaring a numeric result field.

    Writes checker metadata to method attribute ``_checker_meta``.
    Inspector/builder flow collects metadata into checker snapshots, then
    runtime creates ``FieldFloatChecker`` and calls ``checker.check(result_dict)``.

    Args:
        field_name: field name in aspect result dictionary.
        required: whether field is required.
        min_value: minimum allowed value (inclusive).
        max_value: maximum allowed value (inclusive).

    Returns:
        Decorator function that appends checker metadata to method.

    Example:
        @regular_aspect("Calculate")
        @result_float("total", required=True, min_value=0.0)
        async def calculate(self, params, state, box, connections):
            return {"total": 1500.0}
    """
    meta: dict[str, Any] = {
        "checker_class": FieldFloatChecker,
        "field_name": field_name,
        "required": required,
        "min_value": min_value,
        "max_value": max_value,
    }

    def decorator(func: Any) -> Any:
        if not hasattr(func, "_checker_meta"):
            func._checker_meta = []
        func._checker_meta.append(meta)
        return func

    return decorator
