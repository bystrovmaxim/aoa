# tests/intents/plugins/test_emit.py
"""Tests for sending events to plugins via PluginRunContext.emit_event().
═══════════════════ ════════════════════ ════════════════════ ════════════════════
PURPOSE
═══════════════════ ════════════════════ ════════════════════ ════════════════════
Checks the mechanism for delivering typed events from the machine to the plugins.
The ActionProductMachine creates concrete event objects from
hierarchy BasePluginEvent (GlobalStartEvent, GlobalFinishEvent,
BeforeRegularAspectEvent, etc.) at key points in the pipeline and transmits
them in plugin_ctx.emit_event(event) [1].

PluginRunContext finds signed handlers via plugin.get_handlers()
(step 1: isinstance by event_class), checks other filters
(steps 2–7) and calls each handler with the current state
and a typed event object [1].
═══════════════════ ════════════════════ ════════════════════ ════════════════════
SCENARIOS COVERED
═══════════════════ ════════════════════ ════════════════════ ════════════════════
- The handler is called when the event_class matches the subscription.
- The event object contains the correct fields (event_type, action_name,
  nest_level, duration_ms).
- Repeated calls to emit_event() correctly accumulate data in state.
- Event of a different type (GlobalStartEvent instead of GlobalFinishEvent)
  is not delivered to a handler subscribed to GlobalFinishEvent.
- action_name_pattern correctly filters by action name.
- Empty plugin list - emit_event() completes without errors.
- Subscription to compensation events (Saga): CompensateFailedEvent,
  SagaRollbackCompletedEvent - handlers are called correctly."""
import pytest

from action_machine.context.context import Context
from action_machine.logging.scoped_logger import ScopedLogger
from action_machine.plugin.events import (
    CompensateFailedEvent,
    SagaRollbackCompletedEvent,
)
from action_machine.intents.on.on_decorator import on
from action_machine.plugin.plugin import Plugin
from action_machine.plugin.plugin_coordinator import PluginCoordinator
from action_machine.model.base_params import BaseParams

from .conftest import (
    RecordingPlugin,
    SelectivePlugin,
    emit_global_finish,
    emit_global_start,
)

# ═════════════════════════════════════════════════════════════════════════════
#Helper plugins for compensation events
# ═════════════════════════════════════════════════════════════════════════════


class CompensateFailedRecorderPlugin(Plugin):
    """Plugin subscribed to CompensateFailedEvent.
    Logs each compensator failure event to state["failed_events"].
    Used to check that the subscription to CompensateFailedEvent
    works correctly via PluginRunContext.emit_event()."""

    async def get_initial_state(self) -> dict:
        return {"failed_events": []}

    @on(CompensateFailedEvent)
    async def on_compensate_failed(
        self,
        state: dict,
        event: CompensateFailedEvent,
        log: ScopedLogger | None,
    ) -> dict:
        state["failed_events"].append({
            "compensator_name": event.compensator_name,
            "failed_for_aspect": event.failed_for_aspect,
            "original_error_type": type(event.original_error).__name__,
            "compensator_error_type": type(event.compensator_error).__name__,
        })
        return state


class SagaCompletedRecorderPlugin(Plugin):
    """Plugin subscribed to SagaRollbackCompletedEvent.
    Writes the stack unwind results to state["completed_events"].
    Used to check that the subscription to SagaRollbackCompletedEvent
    works correctly via PluginRunContext.emit_event()."""

    async def get_initial_state(self) -> dict:
        return {"completed_events": []}

    @on(SagaRollbackCompletedEvent)
    async def on_saga_completed(
        self,
        state: dict,
        event: SagaRollbackCompletedEvent,
        log: ScopedLogger | None,
    ) -> dict:
        state["completed_events"].append({
            "total_frames": event.total_frames,
            "succeeded": event.succeeded,
            "failed": event.failed,
            "skipped": event.skipped,
        })
        return state


# ═════════════════════════════════════════════════════════════════════════════
#Helper functions for issuing Saga events
# ═════════════════════════════════════════════════════════════════════════════


def _make_base_event_kwargs() -> dict:
    """Generates common kwargs for creating Saga events."""
    from tests.scenarios.domain_model import PingAction
    return {
        "action_class": PingAction,
        "action_name": "tests.domain.ping_action.PingAction",
        "nest_level": 1,
        "context": Context(),
        "params": BaseParams(),
    }


async def emit_compensate_failed(plugin_ctx) -> None:
    """Emits a test CompensateFailedEvent."""
    event = CompensateFailedEvent(
        **_make_base_event_kwargs(),
        aspect_name="charge_aspect",
        state_snapshot=None,
        original_error=ValueError("Aspect Error"),
        compensator_error=RuntimeError("Compensator error"),
        compensator_name="rollback_charge_compensate",
        failed_for_aspect="charge_aspect",
    )
    await plugin_ctx.emit_event(event)


async def emit_saga_rollback_completed(plugin_ctx) -> None:
    """Emits a test SagaRollbackCompletedEvent."""
    event = SagaRollbackCompletedEvent(
        **_make_base_event_kwargs(),
        error=ValueError("Aspect Error"),
        total_frames=3,
        succeeded=2,
        failed=1,
        skipped=0,
        duration_ms=15.5,
        failed_aspects=("charge_aspect",),
    )
    await plugin_ctx.emit_event(event)


# ═════════════════════════════════════════════════════════════════════════════
#Event Delivery Tests
# ═════════════════════════════════════════════════════════════════════════════


class TestEmitEvent:
    """Tests for delivery of typed events via PluginRunContext.emit_event()."""

    @pytest.mark.anyio
    async def test_handler_called_on_matching_event(self):
        """RecordingPlugin is subscribed to GlobalFinishEvent.
        When a GlobalFinishEvent is dispatched, the handler is called and writes
        event in state["events"]."""
        #Arrange - a plugin that records all events
        plugin = RecordingPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()
        #Act - send GlobalFinishEvent
        await emit_global_finish(plugin_ctx)
        #Assert - one event recorded with the correct type
        state = plugin_ctx.get_plugin_state(plugin)
        assert len(state["events"]) == 1
        assert state["events"][0]["event_type"] == "GlobalFinishEvent"

    @pytest.mark.anyio
    async def test_event_contains_correct_fields(self):
        """A typed GlobalFinishEvent object passed to the handler,
        contains correct action_name, nest_level and duration_ms values
        from the event constructor arguments."""
        #Arrange - plugin that writes event fields
        plugin = RecordingPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()
        #Act - send an event with nest_level=3 and duration_ms=42.5
        await emit_global_finish(plugin_ctx, nest_level=3, duration_ms=42.5)
        #Assert - event fields are correct
        state = plugin_ctx.get_plugin_state(plugin)
        event_record = state["events"][0]
        assert event_record["nest_level"] == 3
        assert event_record["duration_ms"] == 42.5
        assert "PingAction" in event_record["action_name"]

    @pytest.mark.anyio
    async def test_multiple_emits_accumulate_in_state(self):
        """Three consecutive calls to emit_event() - RecordingPlugin
        writes three events to state["events"]. The handler is called
        for each emit_event(), state is not reset between calls."""
        #Arrange - recorder plugin
        plugin = RecordingPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()
        #Act - three events in a row
        await emit_global_finish(plugin_ctx)
        await emit_global_finish(plugin_ctx)
        await emit_global_finish(plugin_ctx)
        #Assert - three entries in state
        state = plugin_ctx.get_plugin_state(plugin)
        assert len(state["events"]) == 3

    @pytest.mark.anyio
    async def test_wrong_event_type_not_delivered(self):
        """SelectivePlugin is subscribed to GlobalFinishEvent with action_name_pattern.
        Sending GlobalStartEvent not delivered - isinstance(event,
        GlobalFinishEvent) returns False at step 1 of the filter chain.
        state["order_events"] remains empty."""
        #Arrange - a plugin that responds only to GlobalFinishEvent
        plugin = SelectivePlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()
        #Act - send GlobalStartEvent (plugin is subscribed to GlobalFinishEvent)
        await emit_global_start(plugin_ctx)
        #Assert - the handler is not called (event_class does not match)
        state = plugin_ctx.get_plugin_state(plugin)
        assert state["order_events"] == []

    @pytest.mark.anyio
    async def test_action_name_pattern_filters_matching_action(self):
        """SelectivePlugin is subscribed to GlobalFinishEvent with
        action_name_pattern=".*Order.*". Event with action_name
        containing "Order" is delivered to the handler."""
        #Arrange - plugin with filter ".*Order.*"
        plugin = SelectivePlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()
        #Act - send GlobalFinishEvent with "Order" in action_name
        await emit_global_finish(
            plugin_ctx,
            action_name="app.actions.CreateOrderAction",
        )
        #Assert - the handler is called (action_name matches the pattern)
        state = plugin_ctx.get_plugin_state(plugin)
        assert len(state["order_events"]) == 1
        assert state["order_events"][0] == "app.actions.CreateOrderAction"

    @pytest.mark.anyio
    async def test_action_name_pattern_blocks_non_matching_action(self):
        """SelectivePlugin is subscribed to GlobalFinishEvent with
        action_name_pattern=".*Order.*". Event with action_name
        NOT containing "Order" is not delivered to the handler."""
        #Arrange - plugin with filter ".*Order.*"
        plugin = SelectivePlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()
        #Act - send GlobalFinishEvent without "Order" in action_name
        await emit_global_finish(
            plugin_ctx,
            action_name="app.actions.PingAction",
        )
        #Assert - the handler is not called (action_name does not match)
        state = plugin_ctx.get_plugin_state(plugin)
        assert state["order_events"] == []

    @pytest.mark.anyio
    async def test_empty_plugins_list_no_error(self):
        """Coordinator without plugins. emit_event() completes without errors
        and without side effects - no plugins, no handlers."""
        #Arrange - coordinator without plugins
        coordinator = PluginCoordinator(plugins=[])
        plugin_ctx = await coordinator.create_run_context()
        #Act + Assert - there should be no exceptions
        await emit_global_finish(plugin_ctx)


# ═════════════════════════════════════════════════════════════════════════════
#Compensation Event Subscription (Saga)
# ═════════════════════════════════════════════════════════════════════════════


class TestEmitCompensationEvents:
    """Tests for subscription to typed compensation events via emit_event().

    Added as part of the implementation of the compensation mechanism (Saga).
    Checks that plugins can subscribe to CompensateFailedEvent
    and SagaRollbackCompletedEvent and receive correct data from
    event objects [1]."""

    @pytest.mark.anyio
    async def test_compensate_failed_event_delivered(self):
        """CompensateFailedRecorderPlugin is subscribed to CompensateFailedEvent.
        When a CompensateFailedEvent is emitted, the handler is called and writes
        compensator failure data in state["failed_events"]."""
        #Arrange - a plugin that records compensator failures
        plugin = CompensateFailedRecorderPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()

        #Act — emit CompensateFailedEvent
        await emit_compensate_failed(plugin_ctx)

        #Assert - the event was recorded with the correct fields
        state = plugin_ctx.get_plugin_state(plugin)
        assert len(state["failed_events"]) == 1
        failed = state["failed_events"][0]
        assert failed["compensator_name"] == "rollback_charge_compensate"
        assert failed["failed_for_aspect"] == "charge_aspect"
        assert failed["original_error_type"] == "ValueError"
        assert failed["compensator_error_type"] == "RuntimeError"

    @pytest.mark.anyio
    async def test_saga_rollback_completed_event_delivered(self):
        """SagaCompletedRecorderPlugin is subscribed to SagaRollbackCompletedEvent.
        When SagaRollbackCompletedEvent is emitted, the handler is called
        and writes the unwinding results to state["completed_events"]."""
        #Arrange - a plugin that records the results of unwinding
        plugin = SagaCompletedRecorderPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()

        #Act — emit SagaRollbackCompletedEvent
        await emit_saga_rollback_completed(plugin_ctx)

        #Assert - the event was recorded with correct results
        state = plugin_ctx.get_plugin_state(plugin)
        assert len(state["completed_events"]) == 1
        completed = state["completed_events"][0]
        assert completed["total_frames"] == 3
        assert completed["succeeded"] == 2
        assert completed["failed"] == 1
        assert completed["skipped"] == 0
        assert completed["skipped"] == 0
