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

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Metrics plugin with compensation monitoring:

    from action_machine.logging.channel import Channel
    from action_machine.intents.on import Plugin, on
    from action_machine.plugin.events import (
        GlobalFinishEvent,
        UnhandledErrorEvent,
        CompensateFailedEvent,
        SagaRollbackCompletedEvent,
    )

    class MetricsPlugin(Plugin):
        async def get_initial_state(self) -> dict:
            return {"total": 0, "slow": 0, "saga_failures": 0}

        @on(GlobalFinishEvent)
        async def on_track(self, state, event: GlobalFinishEvent, log):
            state["total"] += 1
            if event.duration_ms > 1000:
                state["slow"] += 1
                await log.warning(
                    Channel.business,
                    "Slow action: {%var.name} in {%var.ms}ms",
                    name=event.action_name,
                    ms=event.duration_ms,
                )
            return state

        @on(UnhandledErrorEvent)
        async def on_error(self, state, event: UnhandledErrorEvent, log):
            await log.critical(
                Channel.error,
                "Unhandled error: {%var.err}",
                err=str(event.error),
            )
            return state

        @on(CompensateFailedEvent)
        async def on_compensate_failed(self, state, event: CompensateFailedEvent, log):
            await log.critical(
                Channel.error,
                "Compensator {%var.comp} failed for {%var.aspect}: {%var.err}",
                comp=event.compensator_name,
                aspect=event.failed_for_aspect,
                err=str(event.compensator_error),
            )
            state["saga_failures"] += 1
            return state

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Handler declaration/typing mismatches fail metadata validation early.
- Compensator failures are suppressed inside rollback core and surfaced through
  plugin events (for example, ``CompensateFailedEvent``).
- This package exports contracts/infrastructure; runtime orchestration lives in
  machine and coordinator flow.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Public plugin subsystem entrypoint and event API surface.
CONTRACT: Export event classes, subscription decorators, and runtime plumbing.
INVARIANTS: Type-safe event subscriptions and per-run plugin state isolation.
FLOW: machine emits typed events -> run context filters -> handlers update state.
FAILURES: validation/declaration errors fail fast during metadata build.
EXTENSION POINTS: add new event classes + @on filters + coordinator handling.
AI-CORE-END
"""

from __future__ import annotations

from action_machine.intents.on.on_decorator import on
from action_machine.legacy.on_intent import OnIntent
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
from action_machine.plugin.plugin import Plugin
from action_machine.plugin.plugin_coordinator import PluginCoordinator
from action_machine.plugin.plugin_run_context import PluginRunContext
from action_machine.plugin.subscription_info import SubscriptionInfo

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
