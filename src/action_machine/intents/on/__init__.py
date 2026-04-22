# src/action_machine/intents/on/__init__.py
"""
ActionMachine plugin package.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provides the full plugin subsystem for ActionMachine. Plugins extend runtime
behavior without changing core machine logic: metrics, audit, side-effect
logging, compensation monitoring (Saga), and more.

═══════════════════════════════════════════════════════════════════════════════
TYPE-SAFE SUBSCRIPTION VIA EVENT CLASSES
═══════════════════════════════════════════════════════════════════════════════

Plugins subscribe via ``@on`` using event classes from ``BasePluginEvent`` tree:

    @on(GlobalFinishEvent)                # only global_finish
    @on(GlobalLifecycleEvent)             # global_start + global_finish
    @on(AspectEvent)                      # all before/after aspect events
    @on(AfterRegularAspectEvent)          # only after regular aspects
    @on(CompensateFailedEvent)            # only compensator failures
    @on(SagaRollbackCompletedEvent)       # only rollback completion
    @on(UnhandledErrorEvent)              # errors without @on_error handler

Typos in class names fail fast at import time instead of becoming silent runtime
bugs. IDE completion/type checks work on event classes and payload fields.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    ActionProductMachine._run_internal()
                |
                v
    PluginCoordinator.create_run_context()
                |
                v
    PluginRunContext (per-request plugin states)
                |
                v
    emit_event(typed Event object)
                |
                +--> subscription filter chain
                +--> matched handlers receive (state, event, log)
                +--> handler returns updated plugin state

═══════════════════════════════════════════════════════════════════════════════
EVENT CLASS HIERARCHY
═══════════════════════════════════════════════════════════════════════════════

    BasePluginEvent                              - root, shared fields
    ├── GlobalLifecycleEvent                     - group: start + finish
    │   ├── GlobalStartEvent                     - pipeline start
    │   └── GlobalFinishEvent                    - pipeline finish (+ result, duration_ms)
    ├── AspectEvent                              - group: all aspect events
    │   ├── RegularAspectEvent                   - group: regular aspects
    │   │   ├── BeforeRegularAspectEvent
    │   │   └── AfterRegularAspectEvent          (+ aspect_result)
    │   ├── SummaryAspectEvent                   - group: summary aspects
    │   │   ├── BeforeSummaryAspectEvent
    │   │   └── AfterSummaryAspectEvent          (+ result)
    │   ├── OnErrorAspectEvent                   - group: @on_error handlers
    │   │   ├── BeforeOnErrorAspectEvent         (+ error)
    │   │   └── AfterOnErrorAspectEvent          (+ handler_result)
    │   └── CompensateAspectEvent                - group: single compensators
    │       ├── BeforeCompensateAspectEvent      (+ error, states)
    │       ├── AfterCompensateAspectEvent       (+ duration_ms)
    │       └── CompensateFailedEvent            (+ compensator_error)
    ├── SagaEvent                                - group: rollback lifecycle
    │   ├── SagaRollbackStartedEvent
    │   └── SagaRollbackCompletedEvent           (+ totals)
    ├── ErrorEvent                               - pipeline errors
    │   └── UnhandledErrorEvent
    └── (future groups extend via inheritance)

Group classes are for grouped subscription via ``isinstance`` and are not
directly emitted by runtime.

═══════════════════════════════════════════════════════════════════════════════
ON DECORATOR FILTERS
═══════════════════════════════════════════════════════════════════════════════

Besides ``event_class``, ``@on`` supports optional filters:

    @on(
        GlobalFinishEvent,
        action_class=OrderAction,
        action_name_pattern=r"orders\\..*",
        aspect_name_pattern=r"validate_.*",
        nest_level=0,
        domain=OrdersDomain,
        predicate=lambda e: e.duration_ms > 1000,
        ignore_exceptions=True,
    )

Inside one ``@on``: filters are AND-combined.
Across multiple ``@on`` on one method: OR behavior.

═══════════════════════════════════════════════════════════════════════════════
COMPONENTS
═══════════════════════════════════════════════════════════════════════════════

- Event classes in ``events.py``: root, grouped, and leaf event types.
- ``SubscriptionInfo``: frozen subscription config with precompiled regexes.
- ``on``: decorator attaching subscriptions to plugin methods.
- ``OnIntent``: marker mixin declaring support for ``@on``.
- ``Plugin``: abstract base class for plugin implementations.
- ``PluginCoordinator``: stateless coordinator creating run contexts.
- ``PluginRunContext``: per-run isolation with state storage and event dispatch.

═══════════════════════════════════════════════════════════════════════════════
HANDLER SIGNATURE
═══════════════════════════════════════════════════════════════════════════════

All plugin handlers must use:

    async def handler(self, state, event: EventClass, log) -> state

``MetadataBuilder`` checks compatibility between ``@on(event_class=...)`` and
the annotated ``event`` parameter type.

"""

from __future__ import annotations

from typing import Any

from action_machine.intents.on.on_decorator import on
from action_machine.intents.on.on_intent import OnIntent
from action_machine.plugin.events import (
    AfterCompensateAspectEvent,
    AfterOnErrorAspectEvent,
    AfterRegularAspectEvent,
    AfterSummaryAspectEvent,
    AspectEvent,
    BasePluginEvent,
    BeforeCompensateAspectEvent,
    BeforeOnErrorAspectEvent,
    BeforeRegularAspectEvent,
    BeforeSummaryAspectEvent,
    CompensateAspectEvent,
    CompensateFailedEvent,
    ErrorEvent,
    GlobalFinishEvent,
    GlobalLifecycleEvent,
    GlobalStartEvent,
    OnErrorAspectEvent,
    RegularAspectEvent,
    SagaEvent,
    SagaRollbackCompletedEvent,
    SagaRollbackStartedEvent,
    SummaryAspectEvent,
    UnhandledErrorEvent,
)

__all__ = [
    "AfterCompensateAspectEvent",
    "AfterOnErrorAspectEvent",
    "AfterRegularAspectEvent",
    "AfterSummaryAspectEvent",
    "AspectEvent",
    # Event classes - root and grouped
    "BasePluginEvent",
    "BeforeCompensateAspectEvent",
    "BeforeOnErrorAspectEvent",
    "BeforeRegularAspectEvent",
    "BeforeSummaryAspectEvent",
    "CompensateAspectEvent",
    "CompensateFailedEvent",
    "ErrorEvent",
    "GlobalFinishEvent",
    "GlobalLifecycleEvent",
    # Event classes - concrete leaf nodes
    "GlobalStartEvent",
    "OnErrorAspectEvent",
    # Infrastructure
    "OnIntent",
    "Plugin",
    "PluginCoordinator",
    "PluginRunContext",
    "RegularAspectEvent",
    "SagaEvent",
    "SagaRollbackCompletedEvent",
    "SagaRollbackStartedEvent",
    # Subscription and configuration
    "SubscriptionInfo",
    "SummaryAspectEvent",
    "UnhandledErrorEvent",
    "on",
]


def __getattr__(name: str) -> Any:
    """Lazy plugin imports: ``Plugin`` imports ``OnIntent`` from this package."""
    if name == "Plugin":
        from action_machine.plugin.plugin import Plugin

        return Plugin
    if name == "PluginCoordinator":
        from action_machine.plugin.plugin_coordinator import PluginCoordinator

        return PluginCoordinator
    if name == "PluginRunContext":
        from action_machine.plugin.plugin_run_context import PluginRunContext

        return PluginRunContext
    if name == "SubscriptionInfo":
        from action_machine.plugin.subscription_info import SubscriptionInfo

        return SubscriptionInfo
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


def __dir__() -> list[str]:
    return sorted(__all__)
