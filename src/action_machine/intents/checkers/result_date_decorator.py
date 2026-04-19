# src/action_machine/intents/checkers/result_date_decorator.py
"""
``result_date`` — attach date/datetime field checker metadata to aspect methods.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Decorator that appends metadata to ``method._checker_meta``. Inspector collects
snapshots; runtime builds :class:`~action_machine.intents.checkers.field_date_checker.FieldDateChecker`
and runs ``checker.check(result_dict)``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    @result_date(...)
          |
          v
    method._checker_meta append
          |
          v
    CheckerIntentInspector snapshot
          |
          v
    runtime creates FieldDateChecker
          |
          v
    checker.check(result_dict)

═══════════════════════════════════════════════════════════════════════════════
USAGE
═══════════════════════════════════════════════════════════════════════════════

    @regular_aspect("Check date")
    @result_date("created_at", date_format="%Y-%m-%d")
    async def check_date(self, params, state, box, connections):
        return {"created_at": "2024-01-15"}

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Date checker decorator for aspect methods.
CONTRACT: Write ``_checker_meta`` row for FieldDateChecker snapshot replay.
INVARIANTS: Metadata keys match FieldDateChecker constructor / snapshot hydration.
FLOW: decorator -> _checker_meta -> inspector -> runtime check.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from action_machine.intents.checkers.field_date_checker import FieldDateChecker


def result_date(
    field_name: str,
    required: bool = True,
    date_format: str | None = None,
    min_date: datetime | None = None,
    max_date: datetime | None = None,
) -> Any:
    """
    Decorator for aspect methods declaring a date result field.

    Writes checker metadata to method attribute ``_checker_meta``.
    Inspector/builder flow collects metadata into checker snapshots, then
    runtime creates ``FieldDateChecker`` and calls ``checker.check(result_dict)``.

    Args:
        field_name: field name in aspect result dictionary.
        required: whether field is required.
        date_format: string date format (for example ``"%Y-%m-%d"``).
        min_date: minimum allowed date (inclusive).
        max_date: maximum allowed date (inclusive).

    Returns:
        Decorator function that appends checker metadata to method.

    Example:
        @regular_aspect("Check date")
        @result_date("created_at", date_format="%Y-%m-%d")
        async def check_date(self, params, state, box, connections):
            return {"created_at": "2024-01-15"}
    """
    meta: dict[str, Any] = {
        "checker_class": FieldDateChecker,
        "field_name": field_name,
        "required": required,
        "date_format": date_format,
        "min_date": min_date,
        "max_date": max_date,
    }

    def decorator(func: Any) -> Any:
        if not hasattr(func, "_checker_meta"):
            func._checker_meta = []
        func._checker_meta.append(meta)
        return func

    return decorator
