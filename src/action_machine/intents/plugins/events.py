# src/action_machine/intents/plugins/events.py
"""
ActionMachine plugin event class hierarchy.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

This module defines the full hierarchy of frozen dataclass events emitted by
``ActionProductMachine`` at key pipeline points and delivered to plugin
handlers via ``PluginRunContext.emit_event()``.

Each event class contains exactly the fields meaningful for that event type.
For example, ``GlobalStartEvent`` has no ``result`` yet, and
``AfterRegularAspectEvent`` has no ``error`` field. This avoids a monolithic
optional-heavy event shape where most fields are ``None`` most of the time.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BasePluginEvent                              - root, shared fields
    ├── GlobalLifecycleEvent                     - group: start + finish
    │   ├── GlobalStartEvent                     - pipeline start
    │   └── GlobalFinishEvent                    - pipeline finish (+ result, duration_ms)
    ├── AspectEvent                              - group: all aspect events
    │   ├── RegularAspectEvent                   - group: regular aspects
    │   │   ├── BeforeRegularAspectEvent         - before regular
    │   │   └── AfterRegularAspectEvent          - after regular (+ aspect_result, duration_ms)
    │   ├── SummaryAspectEvent                   - group: summary aspects
    │   │   ├── BeforeSummaryAspectEvent         - before summary
    │   │   └── AfterSummaryAspectEvent          - after summary (+ result, duration_ms)
    │   ├── OnErrorAspectEvent                   - group: on_error aspects
    │   │   ├── BeforeOnErrorAspectEvent         - before on_error (+ error)
    │   │   └── AfterOnErrorAspectEvent          - after on_error (+ error, handler_result, duration_ms)
    │   └── CompensateAspectEvent                - group: per-compensator events
    │       ├── BeforeCompensateAspectEvent      - before compensator (+ error, state_before, state_after)
    │       ├── AfterCompensateAspectEvent       - after successful compensator (+ duration_ms)
    │       └── CompensateFailedEvent            - compensator failure (+ compensator_error)
    ├── SagaEvent                                - group: rollback lifecycle
    │   ├── SagaRollbackStartedEvent             - rollback start
    │   └── SagaRollbackCompletedEvent           - rollback completion (+ totals)
    ├── ErrorEvent                               - pipeline errors
    │   └── UnhandledErrorEvent                  - error without matching @on_error handler
    └── (future groups extend via inheritance)

═══════════════════════════════════════════════════════════════════════════════
SUBSCRIPTION VIA HIERARCHY
═══════════════════════════════════════════════════════════════════════════════

Hierarchy supports different subscription granularity via ``isinstance`` checks:

    @on(BasePluginEvent)              - all events
    @on(GlobalLifecycleEvent)         — global_start + global_finish
    @on(GlobalFinishEvent)            - only global_finish
    @on(AspectEvent)                  - all before/after aspect events
    @on(RegularAspectEvent)           - before + after regular aspects
    @on(AfterRegularAspectEvent)      - only after regular aspects
    @on(CompensateAspectEvent)        - all per-compensator events
    @on(CompensateFailedEvent)        - only compensator failures
    @on(SagaEvent)                    - all saga rollback events
    @on(SagaRollbackStartedEvent)     - only rollback start
    @on(SagaRollbackCompletedEvent)   - only rollback completion
    @on(ErrorEvent)                   - all pipeline errors

Grouped classes are never emitted directly; runtime always emits concrete leaf
events. Grouped classes exist only for ``isinstance``-based subscriptions.

═══════════════════════════════════════════════════════════════════════════════
COMPENSATION EVENTS (SAGA)
═══════════════════════════════════════════════════════════════════════════════

Compensation events have two levels:

1. WHOLE ROLLBACK LEVEL (SagaEvent):
   ``SagaRollbackStartedEvent`` and ``SagaRollbackCompletedEvent`` are emitted
   once per rollback and carry aggregate rollback telemetry.

2. SINGLE COMPENSATOR LEVEL (CompensateAspectEvent):
   ``BeforeCompensateAspectEvent``, ``AfterCompensateAspectEvent``,
   ``CompensateFailedEvent``.

``CompensateFailedEvent`` is a dedicated type (not a flag on success event)
because compensator failure is operationally distinct and often alert-worthy.
Compensator errors are suppressed inside ``_rollback_saga()`` and surfaced only
through this event stream.

═══════════════════════════════════════════════════════════════════════════════
FROZEN SEMANTICS
═══════════════════════════════════════════════════════════════════════════════

All event classes are ``@dataclass(frozen=True)``. Observing plugins can read
event payloads but cannot mutate them.

═══════════════════════════════════════════════════════════════════════════════
FIELDS action_class AND action_name
═══════════════════════════════════════════════════════════════════════════════

Every event contains both fields:

    action_class: action type for type-safe filtering.

    action_name: full string name (module.ClassName) used in templates and
        regex filters.

═══════════════════════════════════════════════════════════════════════════════
FIELD state_snapshot
═══════════════════════════════════════════════════════════════════════════════

Aspect events carry ``state_snapshot: dict[str, object] | None`` captured from
``state.to_dict()`` so plugins observe state without mutable access.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES OF EVENT CREATION BY RUNTIME
═══════════════════════════════════════════════════════════════════════════════

    # Global lifecycle: PluginEmitSupport.emit_global_start / emit_global_finish
    # build the same events and call plugin_ctx.emit_event. Shape example:
    event = GlobalStartEvent(
        action_class=type(action),
        action_name=action.get_full_class_name(),
        nest_level=current_nest,
        context=context,
        params=params,
    )
    await plugin_ctx.emit_event(event)

    # Regular/summary pipeline: ActionProductMachine calls PluginEmitSupport
    # (emit_before_regular_aspect / emit_after_regular_aspect / …), which builds
    # the same event objects and passes them to plugin_ctx.emit_event. Shape example:
    event = AfterRegularAspectEvent(
        action_class=type(action),
        action_name=action.get_full_class_name(),
        nest_level=box.nested_level,
        context=context,
        params=params,
        aspect_name=aspect_meta.method_name,
        state_snapshot=state.to_dict(),
        aspect_result=new_state_dict,
        duration_ms=aspect_duration * 1000,
    )
    await plugin_ctx.emit_event(event)

    # In ActionProductMachine._rollback_saga():
    event = SagaRollbackStartedEvent(
        action_class=type(action),
        action_name=action.get_full_class_name(),
        nest_level=box.nested_level,
        context=context,
        params=params,
        error=error,
        stack_depth=len(saga_stack),
        compensator_count=sum(1 for f in saga_stack if f.compensator),
        aspect_names=tuple(f.aspect_name for f in reversed(saga_stack)),
    )
    await plugin_ctx.emit_event(event)

═══════════════════════════════════════════════════════════════════════════════
PLUGIN USAGE EXAMPLE
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.intents.logging.channel import Channel
    from action_machine.intents.plugins.events import (
        GlobalFinishEvent,
        AfterRegularAspectEvent,
        AspectEvent,
        CompensateFailedEvent,
        SagaRollbackCompletedEvent,
    )

    class MetricsPlugin(Plugin):

        async def get_initial_state(self) -> dict:
            return {"slow_count": 0, "saga_failures": 0}

        @on(GlobalFinishEvent)
        async def on_track_slow(self, state, event: GlobalFinishEvent, log):
            if event.duration_ms > 1000:
                state["slow_count"] += 1
            return state

        @on(AspectEvent)
        async def on_any_aspect(self, state, event: AspectEvent, log):
            await log.info(
                Channel.debug,
                "Aspect: {%var.name}",
                name=event.aspect_name,
            )
            return state

        @on(CompensateFailedEvent)
        async def on_compensate_failed(self, state, event: CompensateFailedEvent, log):
            await log.critical(
                Channel.error,
                "Compensator {%var.comp} failed for aspect {%var.aspect}: {%var.err}",
                comp=event.compensator_name,
                aspect=event.failed_for_aspect,
                err=str(event.compensator_error),
            )
            state["saga_failures"] += 1
            return state

        @on(SagaRollbackCompletedEvent)
        async def on_saga_complete(self, state, event: SagaRollbackCompletedEvent, log):
            await log.warning(
                Channel.business,
                "Rollback completed: {%var.ok} succeeded, {%var.fail} failed in {%var.ms}ms",
                ok=event.succeeded,
                fail=event.failed,
                ms=event.duration_ms,
            )
            return state
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from action_machine.intents.context.context import Context
from action_machine.model.base_schema import BaseSchema

# ═════════════════════════════════════════════════════════════════════════════
# Root class
# ═════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class BasePluginEvent:
    """
    Root class for all plugin-system events.

    Contains fields shared by every event delivered to plugin handlers.
    """

    action_class: type
    action_name: str
    nest_level: int
    context: Context
    params: BaseSchema


# ═════════════════════════════════════════════════════════════════════════════
# Group: Global lifecycle (pipeline start and finish)
# ═════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class GlobalLifecycleEvent(BasePluginEvent):
    """
    Group class for action lifecycle events.

    Combines ``GlobalStartEvent`` and ``GlobalFinishEvent``.
    Subscribing to ``@on(GlobalLifecycleEvent)`` delivers both.

    Never instantiated directly; the production path emits concrete
    ``GlobalStartEvent`` / ``GlobalFinishEvent`` through ``PluginEmitSupport``.
    This class exists only for ``isinstance``-based subscriptions.
    """


@dataclass(frozen=True)
class GlobalStartEvent(GlobalLifecycleEvent):
    """
    Fired when a run is about to enter the aspect pipeline.

    Emitted via ``PluginEmitSupport.emit_global_start`` after role and connection
    gates and ``ToolsBox`` creation, before ``_execute_aspects_with_error_handling``.
    No ``result`` or ``duration_ms`` yet.
    """


@dataclass(frozen=True)
class GlobalFinishEvent(GlobalLifecycleEvent):
    """
    Fired when a run completes with a final result (summary or ``@on_error``).

    Emitted via ``PluginEmitSupport.emit_global_finish`` after
    ``_execute_aspects_with_error_handling`` returns.

    Attributes:
        result: Final frozen ``BaseResult`` (from summary or a matching error handler).
        duration_ms: Wall time for the whole ``_run_internal`` call, in milliseconds
            (from start of ``_run_internal`` until just before this event).
    """

    result: BaseSchema
    duration_ms: float


# ═════════════════════════════════════════════════════════════════════════════
# Group: Aspect events
# ═════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class AspectEvent(BasePluginEvent):
    """
    Group class for all aspect-related events.

    Adds fields specific to aspect execution context.
    """

    aspect_name: str
    state_snapshot: dict[str, object] | None


# ─────────────────────────────────────────────────────────────────────────────
# Regular Aspect Events
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class RegularAspectEvent(AspectEvent):
    """
    Group class for regular aspect events.
    """


@dataclass(frozen=True)
class BeforeRegularAspectEvent(RegularAspectEvent):
    """
    Fired immediately before a regular aspect method runs.

    Emitted via ``PluginEmitSupport.emit_before_regular_aspect`` (which delegates to
    ``PluginRunContext.emit_event``). No ``aspect_result`` or ``duration_ms`` yet.
    """


@dataclass(frozen=True)
class AfterRegularAspectEvent(RegularAspectEvent):
    """
    Fired after a regular aspect completes and checkers have validated its output.

    Emitted via ``PluginEmitSupport.emit_after_regular_aspect``.

    Attributes:
        aspect_result: Dict merged into state after checker validation (e.g.
            ``{"txn_id": "TXN-001", "charged_amount": 500.0}``).
        duration_ms: Wall time for the aspect call plus checker work, in milliseconds.
    """

    aspect_result: dict[str, Any]
    duration_ms: float


# ─────────────────────────────────────────────────────────────────────────────
# Summary Aspect Events
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SummaryAspectEvent(AspectEvent):
    """
    Group class for summary aspect events.
    """


@dataclass(frozen=True)
class BeforeSummaryAspectEvent(SummaryAspectEvent):
    """
    Fired immediately before the summary aspect runs.

    Emitted via ``PluginEmitSupport.emit_before_summary_aspect``. No ``result`` or
    ``duration_ms`` yet.
    """


@dataclass(frozen=True)
class AfterSummaryAspectEvent(SummaryAspectEvent):
    """
    Fired after the summary aspect returns the action's final result.

    Emitted via ``PluginEmitSupport.emit_after_summary_aspect``.

    Attributes:
        result: Frozen ``BaseResult`` subclass produced by the summary aspect.
        duration_ms: Summary aspect duration in milliseconds.
    """

    result: BaseSchema
    duration_ms: float


# ─────────────────────────────────────────────────────────────────────────────
# OnError Aspect Events
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class OnErrorAspectEvent(AspectEvent):
    """
    Group class for @on_error handler events.
    """


@dataclass(frozen=True)
class BeforeOnErrorAspectEvent(OnErrorAspectEvent):
    """
    Event emitted before invoking matched @on_error handler.
    """

    error: Exception
    handler_name: str


@dataclass(frozen=True)
class AfterOnErrorAspectEvent(OnErrorAspectEvent):
    """
    Event emitted after successful @on_error handler execution.
    """

    error: Exception
    handler_name: str
    handler_result: BaseSchema
    duration_ms: float


# ─────────────────────────────────────────────────────────────────────────────
# Compensate aspect events (per-compensator)
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CompensateAspectEvent(AspectEvent):
    """
    Group class for compensation (Saga) per-compensator events.
    """


@dataclass(frozen=True)
class BeforeCompensateAspectEvent(CompensateAspectEvent):
    """
    Event emitted before compensator execution.
    """

    error: Exception
    compensator_name: str
    compensator_state_before: object  # BaseState
    compensator_state_after: object | None  # BaseState | None


@dataclass(frozen=True)
class AfterCompensateAspectEvent(CompensateAspectEvent):
    """
    Event emitted after successful compensator execution.
    """

    error: Exception
    compensator_name: str
    duration_ms: float


@dataclass(frozen=True)
class CompensateFailedEvent(CompensateAspectEvent):
    """
    Event emitted when a compensator fails.
    """

    original_error: Exception
    compensator_error: Exception
    compensator_name: str
    failed_for_aspect: str


# ═════════════════════════════════════════════════════════════════════════════
# Group: Saga events (rollback lifecycle)
# ═════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class SagaEvent(BasePluginEvent):
    """
    Group class for rollback-level saga events.
    """


@dataclass(frozen=True)
class SagaRollbackStartedEvent(SagaEvent):
    """
    Event emitted once when rollback starts.
    """

    error: Exception
    stack_depth: int
    compensator_count: int
    aspect_names: tuple[str, ...]


@dataclass(frozen=True)
class SagaRollbackCompletedEvent(SagaEvent):
    """
    Event emitted once when rollback completes with aggregate totals.
    """

    error: Exception
    total_frames: int
    succeeded: int
    failed: int
    skipped: int
    duration_ms: float
    failed_aspects: tuple[str, ...]


# ═════════════════════════════════════════════════════════════════════════════
# Group: Error events (pipeline failures)
# ═════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class ErrorEvent(BasePluginEvent):
    """
    Group class for pipeline error events.
    """


@dataclass(frozen=True)
class UnhandledErrorEvent(ErrorEvent):
    """
    Event emitted when aspect error remains unhandled at action level.
    """

    error: Exception
    failed_aspect_name: str | None = None
