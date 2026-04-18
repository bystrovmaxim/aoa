# src/action_machine/intents/plugins/on_decorator.py
"""
``@on`` decorator for subscribing plugin methods to runtime events.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``@on`` is part of ActionMachine plugin intent grammar. It declares that a
plugin method should run on selected event classes emitted by
``ActionProductMachine`` and delivered through ``PluginRunContext`` after
subscription filters pass.

═══════════════════════════════════════════════════════════════════════════════
TYPE-SAFE SUBSCRIPTION VIA EVENT CLASSES
═══════════════════════════════════════════════════════════════════════════════

First parameter ``event_class`` must be from ``BasePluginEvent`` hierarchy.
Subscription matches the class and its subclasses via ``isinstance``:

    @on(BasePluginEvent)              - all events
    @on(GlobalLifecycleEvent)         - global_start + global_finish
    @on(GlobalFinishEvent)            - only global_finish
    @on(AspectEvent)                  - all before/after aspect events
    @on(RegularAspectEvent)           - before + after regular aspects
    @on(AfterRegularAspectEvent)      - only after regular aspects

Typos in event class names fail fast at import time instead of creating silent
runtime bugs.

═══════════════════════════════════════════════════════════════════════════════
FILTERS: AND LOGIC INSIDE ONE @on
═══════════════════════════════════════════════════════════════════════════════

All filters in one decorator are AND-combined. Handler runs only when all
specified filters pass. Unspecified filters (``None``) are skipped.

    @on(
        GlobalFinishEvent,
        action_class=CreateOrderAction,     # action class matches
        nest_level=0,                       # root call only
        predicate=lambda e: e.duration_ms > 1000,  # duration > 1s
    )

═══════════════════════════════════════════════════════════════════════════════
OR LOGIC ACROSS MULTIPLE @on ON SAME METHOD
═══════════════════════════════════════════════════════════════════════════════

Multiple ``@on`` decorators on one method provide OR semantics:

    @on(GlobalStartEvent)               # OR start
    @on(GlobalFinishEvent)              # OR finish
    async def on_lifecycle(self, state, event: GlobalLifecycleEvent, log):
        ...

Each ``@on`` creates a separate ``SubscriptionInfo``.

═══════════════════════════════════════════════════════════════════════════════
HANDLER SIGNATURE
═══════════════════════════════════════════════════════════════════════════════

All handlers must have this 4-parameter signature:

    async def handler(self, state, event: EventClass, log) -> state

    - self: plugin instance
    - state: current per-request plugin state
    - event: event object; annotation may be concrete/group/root class
    - log: scoped logger for plugin scope

Handler must return updated state.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Applies only to methods/callables.
- Method must be async.
- Method signature must be exactly 4 parameters.
- Method name must start with ``"on_"``.
- ``event_class`` must be ``BasePluginEvent`` subclass.
- ``action_class`` must be None/type/tuple[type].
- Pattern fields must be None or valid regex strings.
- ``aspect_name_pattern`` is only valid for ``AspectEvent`` subclasses.
- ``nest_level`` must be None/int/tuple[int].
- ``domain`` must be None or type.
- ``predicate`` must be None or callable.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    @on(GlobalFinishEvent, action_class=OrderAction, nest_level=0)
        │
        ▼  Decorator creates SubscriptionInfo and stores in method._on_subscriptions
    SubscriptionInfo(
        event_class=GlobalFinishEvent,
        action_class=(OrderAction,),
        nest_level=(0,),
        method_name="on_order_finish",
        ...
    )
        │
        ▼  MetadataBuilder.collect_subscriptions (validation)
        ▼  GraphCoordinator.get_subscriptions() snapshot
        │
        ▼  MetadataBuilder → on_intent.validate_subscriptions(cls, ...)
    Validate event_class <-> event annotation compatibility
        │
        ▼  PluginRunContext.emit_event(event)
    Per subscription: filter chain -> handler call

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.intents.logging.channel import Channel
    from action_machine.intents.plugins.events import (
        GlobalFinishEvent,
        AfterRegularAspectEvent,
        AspectEvent,
        UnhandledErrorEvent,
    )

    class MetricsPlugin(Plugin):
        async def get_initial_state(self) -> dict:
            return {"slow_count": 0, "errors": []}

        # Concrete event with duration filter
        @on(
            GlobalFinishEvent,
            predicate=lambda e: e.duration_ms > 1000,
        )
        async def on_slow_actions(self, state, event: GlobalFinishEvent, log):
            state["slow_count"] += 1
            await log.warning(
                Channel.business,
                "Slow action: {%var.name} in {%var.ms}ms",
                name=event.action_name,
                ms=event.duration_ms,
            )
            return state

        # Group event: all aspects
        @on(AspectEvent)
        async def on_any_aspect(self, state, event: AspectEvent, log):
            await log.info(Channel.debug, "Aspect: {%var.name}", name=event.aspect_name)
            return state

        # Filter by aspect type and name
        @on(
            AfterRegularAspectEvent,
            aspect_name_pattern=r"validate_.*",
            nest_level=0,
        )
        async def on_validation_done(self, state, event: AfterRegularAspectEvent, log):
            return state

        # Unhandled pipeline errors
        @on(UnhandledErrorEvent)
        async def on_unhandled(self, state, event: UnhandledErrorEvent, log):
            state["errors"].append(str(event.error))
            return state

        # OR semantics: two @on decorators on one method
        @on(GlobalFinishEvent, action_class=OrderAction)
        @on(GlobalFinishEvent, action_class=PaymentAction)
        async def on_business_finish(self, state, event: GlobalFinishEvent, log):
            return state

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

    TypeError: invalid event_class/action_class/domain types, non-callable
        target, non-async method, wrong parameter count.
    ValueError: invalid regex, negative nest_level, or aspect_name_pattern used
        with non-aspect events.
    NamingPrefixError: method name does not start with ``"on_"``.
"""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Callable
from typing import Any

from action_machine.intents.plugins.events import BasePluginEvent
from action_machine.intents.plugins.subscription_info import SubscriptionInfo
from action_machine.model.exceptions import NamingPrefixError

# Expected @on handler parameter count: self, state, event, log.
_EXPECTED_PARAM_COUNT = 4

# Parameter names for validation errors.
_EXPECTED_PARAM_NAMES = "self, state, event, log"

# Required method name prefix.
_REQUIRED_PREFIX = "on_"


# ============================================================================
# Decorator argument validation
# ============================================================================


def _validate_event_class(event_class: Any) -> None:
    """Validate event_class as BasePluginEvent subclass."""
    if not isinstance(event_class, type) or not issubclass(
        event_class, BasePluginEvent
    ):
        raise TypeError(
            f"@on: first argument event_class must be a BasePluginEvent subclass, "
            f"got {event_class!r}. Example: @on(GlobalFinishEvent)"
        )


def _normalize_action_class(
    action_class: type | tuple[type, ...] | None,
) -> tuple[type, ...] | None:
    """Normalize action_class to tuple[type, ...] or None."""
    if action_class is None:
        return None

    if isinstance(action_class, type):
        return (action_class,)

    if isinstance(action_class, tuple):
        for i, item in enumerate(action_class):
            if not isinstance(item, type):
                raise TypeError(
                    f"@on: action_class[{i}] must be a type, "
                    f"got {type(item).__name__}: {item!r}."
                )
        return action_class

    raise TypeError(
        f"@on: action_class must be a type, tuple of types, or None, "
        f"got {type(action_class).__name__}: {action_class!r}."
    )


def _validate_string_or_none(value: Any, param_name: str) -> None:
    """Validate value as string or None."""
    if value is not None and not isinstance(value, str):
        raise TypeError(
            f"@on: {param_name} must be a string or None, "
            f"got {type(value).__name__}: {value!r}."
        )


def _normalize_nest_level(
    nest_level: int | tuple[int, ...] | None,
) -> tuple[int, ...] | None:
    """Validate and normalize nest_level into tuple[int, ...] or None."""
    if nest_level is None:
        return None

    if isinstance(nest_level, int):
        if nest_level < 0:
            raise ValueError(
                f"@on: nest_level cannot be negative, got {nest_level}."
            )
        return (nest_level,)

    if isinstance(nest_level, tuple):
        for i, item in enumerate(nest_level):
            if not isinstance(item, int):
                raise TypeError(
                    f"@on: nest_level[{i}] must be int, "
                    f"got {type(item).__name__}: {item!r}."
                )
            if item < 0:
                raise ValueError(
                    f"@on: nest_level[{i}] cannot be negative, got {item}."
                )
        return nest_level

    raise TypeError(
        f"@on: nest_level must be int, tuple[int, ...], or None, "
        f"got {type(nest_level).__name__}: {nest_level!r}."
    )


def _validate_domain(domain: Any) -> None:
    """Validate domain as type or None."""
    if domain is not None and not isinstance(domain, type):
        raise TypeError(
            f"@on: domain must be a domain type or None, "
            f"got {type(domain).__name__}: {domain!r}."
        )


def _validate_predicate(predicate: Any) -> None:
    """Validate predicate as callable or None."""
    if predicate is not None and not callable(predicate):
        raise TypeError(
            f"@on: predicate must be callable or None, "
            f"got {type(predicate).__name__}: {predicate!r}."
        )


def _validate_method(func: Any, event_class_name: str) -> None:
    """Validate decorated method contract: callable, async, signature, prefix."""
    if not callable(func):
        raise TypeError(
            f"@on can only be applied to methods/callables. "
            f"Got object of type {type(func).__name__}: {func!r}."
        )

    if not asyncio.iscoroutinefunction(func):
        raise TypeError(
            f"@on({event_class_name}): method {func.__name__} "
            f"must be async (async def). Synchronous handlers are not supported."
        )

    sig = inspect.signature(func)
    param_count = len(sig.parameters)
    if param_count != _EXPECTED_PARAM_COUNT:
        raise TypeError(
            f"@on({event_class_name}): method {func.__name__} "
            f"must accept {_EXPECTED_PARAM_COUNT} parameters "
            f"({_EXPECTED_PARAM_NAMES}), got {param_count}."
        )

    if not func.__name__.startswith(_REQUIRED_PREFIX):
        raise NamingPrefixError(
            f"@on({event_class_name}): method '{func.__name__}' "
            f"must start with '{_REQUIRED_PREFIX}'. Rename to "
            f"'{_REQUIRED_PREFIX}{func.__name__}' or any name with prefix "
            f"'{_REQUIRED_PREFIX}'."
        )


# ============================================================================
# Main decorator
# ============================================================================


def on(
    event_class: type[BasePluginEvent],
    *,
    action_class: type | tuple[type, ...] | None = None,
    action_name_pattern: str | None = None,
    aspect_name_pattern: str | None = None,
    nest_level: int | tuple[int, ...] | None = None,
    domain: type | None = None,
    predicate: Callable[[BasePluginEvent], bool] | None = None,
    ignore_exceptions: bool = True,
) -> Callable[[Any], Any]:
    """
    Method-level decorator subscribing a plugin handler to runtime events.

    Stores ``SubscriptionInfo`` in ``method._on_subscriptions``.
    """
    # Validate decorator arguments.
    _validate_event_class(event_class)
    normalized_action_class = _normalize_action_class(action_class)
    _validate_string_or_none(action_name_pattern, "action_name_pattern")
    _validate_string_or_none(aspect_name_pattern, "aspect_name_pattern")
    validated_nest_level = _normalize_nest_level(nest_level)
    _validate_domain(domain)
    _validate_predicate(predicate)

    def decorator(func: Any) -> Any:
        """Inner decorator applied to plugin method."""
        _validate_method(func, event_class.__name__)

        # Create SubscriptionInfo with __post_init__ validation.
        subscription = SubscriptionInfo(
            event_class=event_class,
            method_name=func.__name__,
            action_class=normalized_action_class,
            action_name_pattern=action_name_pattern,
            aspect_name_pattern=aspect_name_pattern,
            nest_level=validated_nest_level,
            domain=domain,
            predicate=predicate,
            ignore_exceptions=ignore_exceptions,
        )

        if not hasattr(func, "_on_subscriptions"):
            func._on_subscriptions = []

        func._on_subscriptions.append(subscription)

        return func

    return decorator
