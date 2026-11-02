# packages/aoa-action-machine/src/aoa/action_machine/intents/emits/emits_decorator.py
"""
@emits — the events one method of an action may emit.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A method with ``@emits`` is a typed zone: every line it writes carries one of the listed
events. The declaration says what the method may emit, not what it must.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    @emits(OrderCompletedEvent)            writes the tuple on the function
         │
         └── emission_rules_for(...)       reads the tuple for each call of the method

"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from aoa.action_machine.exceptions.decorator_argument_type_error import DecoratorArgumentTypeError
from aoa.action_machine.exceptions.decorator_argument_value_error import DecoratorArgumentValueError
from aoa.action_machine.exceptions.decorator_target_error import DecoratorTargetError
from aoa.action_machine.exceptions.duplicate_declaration_error import DuplicateDeclarationError
from aoa.action_machine.model.base_event import BaseEvent

EMITS_ATTR = "_emits_events"


def _validated_events(events: tuple[Any, ...]) -> tuple[type[BaseEvent], ...]:
    """Return ``events`` once each one is known to be a distinct event class."""
    if not events:
        raise DecoratorArgumentValueError("@emits: at least one event is required. Example: @emits(OrderCompletedEvent)")
    for event in events:
        if not isinstance(event, type) or not issubclass(event, BaseEvent):
            raise DecoratorArgumentTypeError(f"@emits: {event!r} is not a BaseEvent subclass.")
        if event is BaseEvent:
            raise DecoratorArgumentTypeError("@emits: BaseEvent names no fact; list its subclasses.")
    if len(set(events)) != len(events):
        raise DecoratorArgumentValueError(f"@emits: an event is listed twice in {events!r}.")
    return events


def emits(*events: type[BaseEvent]) -> Callable[[Any], Any]:
    """
    Declare the events a method may emit.

    AI-CORE-BEGIN
    ROLE: Turns one method of an action into a typed zone.
    CONTRACT: Writes the listed classes on the function and returns it unchanged.
    INVARIANTS: Written once per method, above or below the method's own decorator; only the five kinds of method read it.
    FAILURES: Decorator errors for bad arguments; ``DuplicateDeclarationError`` for a second ``@emits``.
    AI-CORE-END
    """
    validated = _validated_events(events)

    def decorator(func: Any) -> Any:
        """Write the declaration on the method."""
        if not callable(func):
            raise DecoratorTargetError(f"@emits can only be applied to methods, got {func!r}.")
        if hasattr(func, EMITS_ATTR):
            raise DuplicateDeclarationError(f"@emits: '{func.__name__}' already declares its events.")
        setattr(func, EMITS_ATTR, validated)
        return func

    return decorator
