# src/action_machine/intents/checkers/result_instance_decorator.py
"""
``result_instance`` — attach isinstance-based field checker metadata to aspect methods.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Decorator that appends metadata to ``method._checker_meta``. Inspector collects
snapshots; runtime builds :class:`~action_machine.intents.checkers.field_instance_checker.FieldInstanceChecker`
and runs ``checker.check(result_dict)``.

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
    runtime creates FieldInstanceChecker
            |
            v
    checker.check(result_dict)

═══════════════════════════════════════════════════════════════════════════════
USAGE
═══════════════════════════════════════════════════════════════════════════════

    @regular_aspect("Get user")
    @result_instance("user", User, required=True)
    async def get_user(self, params, state, box, connections):
        return {"user": User(id=1, name="John")}

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Instance checker decorator for aspect methods.
CONTRACT: Write ``_checker_meta`` row for FieldInstanceChecker snapshot replay.
INVARIANTS: Metadata keys match FieldInstanceChecker constructor / snapshot hydration.
FLOW: decorator -> _checker_meta -> inspector -> runtime check.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from typing import Any

from action_machine.intents.checkers.field_instance_checker import FieldInstanceChecker


def result_instance(
    field_name: str,
    expected_class: type[Any] | tuple[type[Any], ...],
    required: bool = True,
) -> Any:
    """
    Decorator for aspect methods declaring class-instance result field.

    Writes checker metadata to method attribute ``_checker_meta``.
    Inspector/builder flow collects metadata into checker snapshots, then
    runtime creates ``FieldInstanceChecker`` and calls ``checker.check(result_dict)``.

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
    meta: dict[str, Any] = {
        "checker_class": FieldInstanceChecker,
        "field_name": field_name,
        "required": required,
        "expected_class": expected_class,
    }

    def decorator(func: Any) -> Any:
        if not hasattr(func, "_checker_meta"):
            func._checker_meta = []
        func._checker_meta.append(meta)
        return func

    return decorator
