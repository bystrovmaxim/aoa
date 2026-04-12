# tests/domain_model/error_plugins.py
"""
Test plugins that observe aspect errors.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Plugins subscribed to typed error events from the BasePluginEvent hierarchy
for testing aspect error observation. Observer plugins cannot change the outcome
or suppress errors — they only record information in per-request state.

Typed error events:
    UnhandledErrorEvent       — no matching @on_error handler
    BeforeOnErrorAspectEvent  — before invoking a matched @on_error handler
    AfterOnErrorAspectEvent   — after a successful @on_error handler

ActionProductMachine emits these in _handle_aspect_error():
- If a handler is found → BeforeOnErrorAspectEvent, then AfterOnErrorAspectEvent
  after a successful call.
- If no handler → UnhandledErrorEvent, then the original exception propagates.

═══════════════════════════════════════════════════════════════════════════════
PLUGINS
═══════════════════════════════════════════════════════════════════════════════

- ErrorObserverPlugin — appends all errors to state["errors"].
  Subscribes to UnhandledErrorEvent and BeforeOnErrorAspectEvent.
  Records action_name, error type, message, and event type.

- ErrorCounterPlugin — counts errors in state["count"].
  Same subscriptions. Splits into handled (BeforeOnErrorAspectEvent — handler found)
  and unhandled (UnhandledErrorEvent — no handler).

═══════════════════════════════════════════════════════════════════════════════
USAGE IN TESTS
═══════════════════════════════════════════════════════════════════════════════
    from tests.domain_model.error_plugins import ErrorObserverPlugin, ErrorCounterPlugin

    observer = ErrorObserverPlugin()
    counter = ErrorCounterPlugin()
    bench = TestBench(
        plugins=[observer, counter],
        log_coordinator=LogCoordinator(loggers=[]),
    )
    result = await bench.run(ErrorHandledAction(), params, rollup=False)
"""
from action_machine.logging.scoped_logger import ScopedLogger
from action_machine.plugins.events import (
    BeforeOnErrorAspectEvent,
    UnhandledErrorEvent,
)
from action_machine.plugins.on_decorator import on
from action_machine.plugins.plugin import Plugin


class ErrorObserverPlugin(Plugin):
    """
    Observer plugin that records aspect errors into state.

    Per-request state: {"errors": []}. Each error is appended as a dict with
    action, error_type, error_message, event_type.

    Subscribed events:

    1. UnhandledErrorEvent — no matching @on_error handler.
       Fields: error (Exception), failed_aspect_name (str | None).
       has_handler is False.

    2. BeforeOnErrorAspectEvent — before calling a matched @on_error handler.
       Fields: error (Exception), handler_name (str).
       has_handler is True.

    Does not suppress errors or alter results — observation only.
    """

    async def get_initial_state(self) -> dict:
        """Initial state — empty error list."""
        return {"errors": []}

    @on(UnhandledErrorEvent)
    async def on_observe_unhandled(
        self,
        state: dict,
        event: UnhandledErrorEvent,
        log: ScopedLogger | None,
    ) -> dict:
        """
        Record an unhandled error in state["errors"].

        UnhandledErrorEvent is emitted when no @on_error handler matches.
        After this event, the original exception propagates from machine.run().
        """
        state["errors"].append({
            "action": event.action_name,
            "error_type": type(event.error).__name__,
            "error_message": str(event.error),
            "has_handler": False,
            "event_type": type(event).__name__,
            "failed_aspect_name": event.failed_aspect_name,
        })
        return state

    @on(BeforeOnErrorAspectEvent)
    async def on_observe_before_handler(
        self,
        state: dict,
        event: BeforeOnErrorAspectEvent,
        log: ScopedLogger | None,
    ) -> dict:
        """
        Record an error before the @on_error handler runs.

        BeforeOnErrorAspectEvent is emitted when a handler was found but not yet
        invoked. The observer records the error and handler name.
        """
        state["errors"].append({
            "action": event.action_name,
            "error_type": type(event.error).__name__,
            "error_message": str(event.error),
            "has_handler": True,
            "event_type": type(event).__name__,
            "handler_name": event.handler_name,
        })
        return state


class ErrorCounterPlugin(Plugin):
    """
    Counter plugin for aspect errors.

    Per-request state: {"count": 0, "handled_count": 0, "unhandled_count": 0}.
    Increments count on each error event.
    handled = BeforeOnErrorAspectEvent (handler exists).
    unhandled = UnhandledErrorEvent (no handler).

    Subscribes to both event types for separate counts.
    """

    async def get_initial_state(self) -> dict:
        """Initial state — zero counters."""
        return {"count": 0, "handled_count": 0, "unhandled_count": 0}

    @on(UnhandledErrorEvent)
    async def on_count_unhandled(
        self,
        state: dict,
        event: UnhandledErrorEvent,
        log: ScopedLogger | None,
    ) -> dict:
        """
        Increment counters for an unhandled error.

        count — total errors.
        unhandled_count — errors without a handler (will propagate).
        """
        state["count"] += 1
        state["unhandled_count"] += 1
        return state

    @on(BeforeOnErrorAspectEvent)
    async def on_count_handled(
        self,
        state: dict,
        event: BeforeOnErrorAspectEvent,
        log: ScopedLogger | None,
    ) -> dict:
        """
        Increment counters for a handled error.

        count — total errors.
        handled_count — errors for which the Action has a handler.
        """
        state["count"] += 1
        state["handled_count"] += 1
        return state
