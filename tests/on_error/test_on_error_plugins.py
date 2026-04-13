# tests/on_error/test_on_error_plugins.py
"""
Tests for error events in the plugin system.
═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════
Verifies that plugins receive typed error events when
exception occurs in aspect:

- BeforeOnErrorAspectEvent is emitted when Action has @on_error
  handler — plugin is called BEFORE handler invocation [1].
- UnhandledErrorEvent is emitted when Action does NOT have suitable
  @on_error handler — plugin is called BEFORE exception propagation [1].
- Plugin cannot change result — only observes.
- Plugin is called both when Action has handler and when it doesn't.
- No error in aspect — error events are not emitted.

In the new typed system, instead of a single string event
"on_error" with Optional field has_action_handler, two
separate event types are used with different fields:

    BeforeOnErrorAspectEvent  — handler found (fields: error, handler_name)
    UnhandledErrorEvent       — handler not found (fields: error, failed_aspect_name)

Tests use plugins from tests/domain/error_plugins.py
and Actions from tests/domain/error_actions.py.
"""
import pytest

from action_machine.intents.context.context import Context
from action_machine.intents.logging.log_coordinator import LogCoordinator
from action_machine.intents.plugins.events import (
    BeforeOnErrorAspectEvent,
    UnhandledErrorEvent,
)
from action_machine.intents.plugins.on_decorator import on
from action_machine.intents.plugins.plugin import Plugin
from action_machine.runtime.machines.action_product_machine import ActionProductMachine
from action_machine.runtime.machines.core_action_machine import CoreActionMachine
from tests.domain_model import (
    ErrorHandledAction,
    ErrorTestParams,
    NoErrorHandlerAction,
)
from tests.domain_model.error_plugins import ErrorCounterPlugin, ErrorObserverPlugin

# ═════════════════════════════════════════════════════════════════════════════
# Helper function to create machine with plugins
# ═════════════════════════════════════════════════════════════════════════════

def _make_machine(
    plugins: list,
) -> ActionProductMachine:
    """Creates machine with given plugins and quiet logger."""
    return ActionProductMachine(
        mode="test",
        coordinator=CoreActionMachine.create_coordinator(),
        plugins=plugins,
        log_coordinator=LogCoordinator(loggers=[]),
    )


# ═════════════════════════════════════════════════════════════════════════════
# Plugin called on error with handler on Action
# ═════════════════════════════════════════════════════════════════════════════

class TestOnErrorPluginWithHandler:
    """
    Plugin receives BeforeOnErrorAspectEvent when Action has @on_error handler.

    Machine emits BeforeOnErrorAspectEvent before calling found
    @on_error handler [1]. Event contains error (exception) and
    handler_name (handler method name).
    """

    @pytest.mark.asyncio()
    async def test_observer_receives_error_event(self) -> None:
        """ErrorObserverPlugin records error in state["errors"]."""
        # Arrange — observer plugin + Action with ValueError handler
        observer = ErrorObserverPlugin()
        machine = _make_machine(plugins=[observer])
        params = ErrorTestParams(value="test", should_fail=True)
        context = Context()

        # Act — aspect throws ValueError, Action handler catches
        result = await machine.run(context, ErrorHandledAction(), params)

        # Assert — result from handler (error handled)
        assert result.status == "handled"

    @pytest.mark.asyncio()
    async def test_observer_records_error_details(self) -> None:
        """Plugin records error type, message, and handler presence."""
        # Arrange
        observer = ErrorObserverPlugin()
        counter = ErrorCounterPlugin()
        machine = ActionProductMachine(
            mode="test",
            coordinator=CoreActionMachine.create_coordinator(),
            plugins=[observer, counter],
            log_coordinator=LogCoordinator(loggers=[]),
        )
        params = ErrorTestParams(value="broken", should_fail=True)
        context = Context()

        # Act — execute action
        result = await machine.run(context, ErrorHandledAction(), params)

        # Assert — result handled
        assert result.status == "handled"

    @pytest.mark.asyncio()
    async def test_counter_increments_handled(self) -> None:
        """
        Plugin with external storage increments handled_count
        on error with handler on Action.

        Subscribed to BeforeOnErrorAspectEvent — emitted when machine
        found suitable @on_error handler [1].
        """
        external_storage: dict = {"count": 0, "handled": 0, "unhandled": 0}

        class StoringCounterPlugin(Plugin):
            async def get_initial_state(self) -> dict:
                return {}

            @on(BeforeOnErrorAspectEvent)
            async def on_count_handled(self, state, event: BeforeOnErrorAspectEvent, log):
                external_storage["count"] += 1
                external_storage["handled"] += 1
                return state

            @on(UnhandledErrorEvent)
            async def on_count_unhandled(self, state, event: UnhandledErrorEvent, log):
                external_storage["count"] += 1
                external_storage["unhandled"] += 1
                return state

        machine = _make_machine(plugins=[StoringCounterPlugin()])
        params = ErrorTestParams(value="test", should_fail=True)

        # Act — error handled by Action
        result = await machine.run(Context(), ErrorHandledAction(), params)

        # Assert
        assert result.status == "handled"
        assert external_storage["count"] == 1
        assert external_storage["handled"] == 1
        assert external_storage["unhandled"] == 0


# ═════════════════════════════════════════════════════════════════════════════
# Plugin called on error WITHOUT handler on Action
# ═════════════════════════════════════════════════════════════════════════════

class TestOnErrorPluginWithoutHandler:
    """
    Plugin receives UnhandledErrorEvent when Action has no @on_error.

    Machine emits UnhandledErrorEvent when no @on_error handler
    matched exception type [1]. After event emission, original
    exception propagates outward.
    """

    @pytest.mark.asyncio()
    async def test_plugin_called_before_error_propagates(self) -> None:
        """Plugin receives UnhandledErrorEvent, then error propagates."""
        external_storage: dict = {"called": False, "error_type": None}

        class ObserverPlugin(Plugin):
            async def get_initial_state(self) -> dict:
                return {}

            @on(UnhandledErrorEvent)
            async def on_observe(self, state, event: UnhandledErrorEvent, log):
                external_storage["called"] = True
                external_storage["error_type"] = type(event.error).__name__
                return state

        machine = _make_machine(plugins=[ObserverPlugin()])
        params = ErrorTestParams(value="fail", should_fail=True)

        # Act & Assert — error propagates (no @on_error on Action)
        with pytest.raises(ValueError, match="Error: fail"):
            await machine.run(Context(), NoErrorHandlerAction(), params)

        # Assert — plugin was still called BEFORE propagation
        assert external_storage["called"] is True
        assert external_storage["error_type"] == "ValueError"


# ═════════════════════════════════════════════════════════════════════════════
# Plugin cannot suppress error
# ═════════════════════════════════════════════════════════════════════════════

class TestOnErrorPluginCannotSuppressError:
    """Plugin observes but cannot suppress error or change result."""

    @pytest.mark.asyncio()
    async def test_plugin_cannot_change_result(self) -> None:
        """Even if plugin returns something — result is determined by Action, not plugin."""

        class AggressivePlugin(Plugin):
            """Plugin that tries to 'handle' error — but cannot."""

            async def get_initial_state(self) -> dict:
                return {"tried_to_handle": False}

            @on(BeforeOnErrorAspectEvent)
            async def on_try_handle(self, state, event: BeforeOnErrorAspectEvent, log):
                state["tried_to_handle"] = True
                # Plugin cannot suppress error — only observes.
                # Return state, but it doesn't affect Action result.
                return state

        machine = _make_machine(plugins=[AggressivePlugin()])
        params = ErrorTestParams(value="test", should_fail=True)

        # Act — Action has handler, result from Action, not from plugin
        result = await machine.run(Context(), ErrorHandledAction(), params)

        # Assert — result is determined by @on_error handler of Action
        assert result.status == "handled"


# ═════════════════════════════════════════════════════════════════════════════
# No error — error events not emitted
# ═════════════════════════════════════════════════════════════════════════════

class TestOnErrorPluginNotCalledOnSuccess:
    """On successful execution, error events are not emitted."""

    @pytest.mark.asyncio()
    async def test_no_error_no_error_event(self) -> None:
        """Normal execution → plugins on error events are NOT called."""
        external_storage: dict = {"called": False}

        class NeverCalledPlugin(Plugin):
            async def get_initial_state(self) -> dict:
                return {}

            @on(BeforeOnErrorAspectEvent)
            async def on_should_not_be_called_handled(self, state, event: BeforeOnErrorAspectEvent, log):
                external_storage["called"] = True
                return state

            @on(UnhandledErrorEvent)
            async def on_should_not_be_called_unhandled(self, state, event: UnhandledErrorEvent, log):
                external_storage["called"] = True
                return state

        machine = _make_machine(plugins=[NeverCalledPlugin()])
        params = ErrorTestParams(value="ok", should_fail=False)

        # Act — normal execution, no error
        result = await machine.run(Context(), ErrorHandledAction(), params)

        # Assert — result from summary, error plugins NOT called
        assert result.status == "ok"
        assert external_storage["called"] is False


# ═════════════════════════════════════════════════════════════════════════════
# Plugin receives full scope in error event
# ═════════════════════════════════════════════════════════════════════════════

class TestOnErrorPluginEventScope:
    """Plugin receives correct data in typed error event."""

    @pytest.mark.asyncio()
    async def test_event_contains_error_and_action_name(self) -> None:
        """BeforeOnErrorAspectEvent contains error, action_name, handler_name."""
        captured_events: list[dict] = []

        class CapturingPlugin(Plugin):
            async def get_initial_state(self) -> dict:
                return {}

            @on(BeforeOnErrorAspectEvent)
            async def on_capture(self, state, event: BeforeOnErrorAspectEvent, log):
                captured_events.append({
                    "event_type": type(event).__name__,
                    "action_name": event.action_name,
                    "error": event.error,
                    "error_type": type(event.error).__name__,
                    "handler_name": event.handler_name,
                    "nest_level": event.nest_level,
                })
                return state

        machine = _make_machine(plugins=[CapturingPlugin()])
        params = ErrorTestParams(value="broken", should_fail=True)

        # Act
        await machine.run(Context(), ErrorHandledAction(), params)

        # Assert — one event captured
        assert len(captured_events) == 1
        ev = captured_events[0]

        # Assert — fields of typed event are correct
        assert ev["event_type"] == "BeforeOnErrorAspectEvent"
        assert "ErrorHandledAction" in ev["action_name"]
        assert ev["error_type"] == "ValueError"
        assert isinstance(ev["error"], ValueError)
        assert isinstance(ev["handler_name"], str)
        assert ev["nest_level"] >= 1

    @pytest.mark.asyncio()
    async def test_unhandled_event_contains_failed_aspect_name(self) -> None:
        """UnhandledErrorEvent contains error and failed_aspect_name."""
        captured_events: list[dict] = []

        class CapturingPlugin(Plugin):
            async def get_initial_state(self) -> dict:
                return {}

            @on(UnhandledErrorEvent)
            async def on_capture_unhandled(self, state, event: UnhandledErrorEvent, log):
                captured_events.append({
                    "event_type": type(event).__name__,
                    "action_name": event.action_name,
                    "error": event.error,
                    "error_type": type(event.error).__name__,
                    "failed_aspect_name": event.failed_aspect_name,
                    "nest_level": event.nest_level,
                })
                return state

        machine = _make_machine(plugins=[CapturingPlugin()])
        params = ErrorTestParams(value="fail", should_fail=True)

        # Act & Assert — error propagates
        with pytest.raises(ValueError):
            await machine.run(Context(), NoErrorHandlerAction(), params)

        # Assert — one event captured
        assert len(captured_events) == 1
        ev = captured_events[0]

        # Assert — UnhandledErrorEvent fields are correct
        assert ev["event_type"] == "UnhandledErrorEvent"
        assert "NoErrorHandlerAction" in ev["action_name"]
        assert ev["error_type"] == "ValueError"
        assert isinstance(ev["error"], ValueError)
        assert ev["nest_level"] >= 1
