# src/action_machine/intents/checkers/result_int_decorator.py
"""
``result_int`` — attach integer field checker metadata to aspect methods.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Decorator that appends metadata to ``method._checker_meta``. Inspector collects
snapshots; runtime builds :class:`~action_machine.intents.checkers.field_int_checker.FieldIntChecker`
and runs ``checker.check(result_dict)``.

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
    runtime creates FieldIntChecker
         |
         v
    checker.check(result_dict)

═══════════════════════════════════════════════════════════════════════════════
USAGE
═══════════════════════════════════════════════════════════════════════════════

    @regular_aspect("Count")
    @result_int("count", required=True, min_value=0, max_value=100)
    async def count_items(self, params, state, box, connections):
        return {"count": 42}

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Integer checker decorator for aspect methods.
CONTRACT: Write ``_checker_meta`` row for FieldIntChecker snapshot replay.
INVARIANTS: Metadata keys match FieldIntChecker constructor / snapshot hydration.
FLOW: decorator -> _checker_meta -> inspector -> runtime check.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from typing import Any

from action_machine.intents.checkers.field_int_checker import FieldIntChecker


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
    runtime creates ``FieldIntChecker`` and calls ``checker.check(result_dict)``.

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
    meta: dict[str, Any] = {
        "checker_class": FieldIntChecker,
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
