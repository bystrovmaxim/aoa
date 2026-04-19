# src/action_machine/intents/checkers/result_string_decorator.py
"""
``result_string`` — attach string field checker metadata to aspect methods.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Decorator for aspect methods that appends checker metadata to
``method._checker_meta``. The inspector/builder collects it into checker
snapshots; runtime instantiates :class:`~action_machine.intents.checkers.field_string_checker.FieldStringChecker`
and runs ``checker.check(result_dict)``.

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

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: String checker decorator for aspect methods.
CONTRACT: Write ``_checker_meta`` row for FieldStringChecker snapshot replay.
INVARIANTS: Metadata keys match FieldStringChecker constructor / snapshot hydration.
FLOW: decorator -> _checker_meta -> inspector -> runtime check.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from typing import Any

from action_machine.intents.checkers.field_string_checker import FieldStringChecker


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
