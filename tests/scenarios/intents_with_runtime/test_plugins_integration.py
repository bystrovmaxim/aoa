# tests/scenarios/intents_with_runtime/test_plugins_integration.py
"""Plugin integration tests with the full ActionMachine pipeline.
═══════════════════ ════════════════════ ════════════════════ ════════════════════
PURPOSE
═══════════════════ ════════════════════ ════════════════════ ════════════════════
Checks that plugins correctly receive typed events from
a real pipeline for executing actions. Unlike other tests
plugins/ packages that call emit_event() directly, these tests
run actions through TestBench.run() - a complete async pipeline
and sync machines with matching results.

The ActionProductMachine creates concrete event objects from
BasePluginEvent [1] hierarchy at key points in the pipeline:

    GlobalStartEvent - before the first aspect
    BeforeRegularAspectEvent - before each regular aspect
    AfterRegularAspectEvent - after each regular aspect
    BeforeSummaryAspectEvent - before the summary aspect
    AfterSummaryAspectEvent - after the summary aspect
    GlobalFinishEvent - after successful completion

Plugins subscribe via @on(EventClass) and receive typed
event objects with specific fields (without Optional fields) [1].

═══════════════════ ════════════════════ ════════════════════ ════════════════════
SCENARIOS COVERED
═══════════════════ ════════════════════ ════════════════════ ════════════════════
- The counter plugin receives a GlobalFinishEvent when running a PingAction.
- The counter plugin receives a GlobalFinishEvent when running a SimpleAction
  (regular + summary).
- Recorder plugin captures GlobalStartEvent and GlobalFinishEvent
  PingAction pipeline.
- Plugin with action_name_pattern receives events only from suitable ones
  actions.
- Several plugins at the same time - all receive events.

═══════════════════ ════════════════════ ════════════════════ ════════════════════
ACCESS TO PLUGIN STATUS
═══════════════════ ════════════════════ ════════════════════ ════════════════════
TestBench uses production machines (ActionProductMachine,
SyncActionProductMachine) which create PluginRunContext inside
_run_internal(). After run() completes, the context is destroyed −
There is no direct access to plugin_ctx.get_plugin_state().

To check the operation of plugins, external storage is used,
passed through the plugin constructor. Event processing plugin
writes data to an external list/dictionary that the test reads
after run() completes."""
from unittest.mock import AsyncMock

import pytest

from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.plugin.events import (
    GlobalFinishEvent,
    GlobalStartEvent,
)
from action_machine.intents.on.on_decorator import on
from action_machine.plugin.plugin import Plugin
from action_machine.runtime.machines.core import Core
from action_machine.testing import TestBench
from tests.scenarios.domain_model import (
    FullAction,
    NotificationService,
    PaymentService,
    PingAction,
    SimpleAction,
    TestDbManager,
)
from tests.scenarios.domain_model.roles import ManagerRole

# ═════════════════════════════════════════════════════════════════════════════
#Plugins with external storage for verification from tests
# ═════════════════════════════════════════════════════════════════════════════

class ExternalCounterPlugin(Plugin):
    """Counter plugin with external storage.

    Subscribed to GlobalFinishEvent - records the number of calls
    event type and action name to an external list. Test reads a list
    after run() to check that the plugin received the events."""

    def __init__(self, storage: list):
        self._storage = storage

    async def get_initial_state(self) -> dict:
        return {"count": 0}

    @on(GlobalFinishEvent)
    async def on_count(self, state: dict, event: GlobalFinishEvent, log) -> dict:
        state["count"] += 1
        self._storage.append({
            "event_type": type(event).__name__,
            "action": event.action_name,
            "count": state["count"],
            "duration_ms": event.duration_ms,
        })
        return state


class ExternalRecorderPlugin(Plugin):
    """Recorder plugin with external storage.

    Subscribed to GlobalStartEvent and GlobalFinishEvent.
    Writes the event class name to an external list.
    Allows the test to see the sequence of pipeline events."""

    def __init__(self, storage: list):
        self._storage = storage

    async def get_initial_state(self) -> dict:
        return {}

    @on(GlobalStartEvent)
    async def on_start(self, state: dict, event: GlobalStartEvent, log) -> dict:
        self._storage.append(type(event).__name__)
        return state

    @on(GlobalFinishEvent)
    async def on_finish(self, state: dict, event: GlobalFinishEvent, log) -> dict:
        self._storage.append(type(event).__name__)
        return state


class SelectiveCounterPlugin(Plugin):
    """Counter plugin with filter by action name.

    Subscribed to GlobalFinishEvent with action_name_pattern=".*Simple.*".
    Only responds to actions containing "Simple" in the full name.
    Writes action_name to an external list."""

    def __init__(self, storage: list):
        self._storage = storage

    async def get_initial_state(self) -> dict:
        return {}

    @on(GlobalFinishEvent, action_name_pattern=".*Simple.*")
    async def on_simple(self, state: dict, event: GlobalFinishEvent, log) -> dict:
        self._storage.append(event.action_name)
        return state


# ═════════════════════════════════════════════════════════════════════════════
#Tests
# ═════════════════════════════════════════════════════════════════════════════

class TestPluginsIntegration:
    """Full pipeline integration tests of plugins via TestBench.

    Each test creates an external storage (list), transmits it
    into the plugin through the constructor, runs the action through TestBench.run()
    (async + machine sync) and checks the contents of the storage."""

    @pytest.mark.anyio
    async def test_counter_plugin_receives_global_finish_from_ping(self):
        """ExternalCounterPlugin receives GlobalFinishEvent when running PingAction
        via TestBench. PingAction - summary only, NoneRole.

        The storage contains records from both machines (async + sync),
        so we expect at least one entry (TestBench resets
        mocks between runs, but the plugin is not mocked, its storage
        accumulates records from both machines)."""
        #Arrange - external storage and plugin
        storage: list = []
        plugin = ExternalCounterPlugin(storage)
        bench = TestBench(
            coordinator=Core.create_coordinator(),
            log_coordinator=LogCoordinator(loggers=[]),
            plugins=[plugin],
        )

        #Act - full run of PingAction on both machines
        result = await bench.run(
            PingAction(),
            PingAction.Params(),
            rollup=False,
        )

        #Assert - the result is correct
        assert result.message == "pong"

        #Assert - the plugin received events (from async and sync machines)
        assert len(storage) >= 1
        assert all(record["event_type"] == "GlobalFinishEvent" for record in storage)
        assert all("PingAction" in record["action"] for record in storage)

    @pytest.mark.anyio
    async def test_counter_plugin_receives_global_finish_from_simple(self):
        """ExternalCounterPlugin receives a GlobalFinishEvent when running a SimpleAction.
        SimpleAction has regular + summary, NoneRole."""
        #Arrange - storage and plugin
        storage: list = []
        plugin = ExternalCounterPlugin(storage)
        bench = TestBench(
            coordinator=Core.create_coordinator(),
            log_coordinator=LogCoordinator(loggers=[]),
            plugins=[plugin],
        )

        #Act - full run of SimpleAction
        result = await bench.run(
            SimpleAction(),
            SimpleAction.Params(name="Alice"),
            rollup=False,
        )

        #Assert - the result is correct
        assert result.greeting == "Hello, Alice!"

        #Assert - the plugin received events
        assert len(storage) >= 1
        assert all("SimpleAction" in record["action"] for record in storage)

    @pytest.mark.anyio
    async def test_recorder_plugin_captures_event_sequence(self):
        """ExternalRecorderPlugin is subscribed to GlobalStartEvent and GlobalFinishEvent.
        When run, PingAction records a sequence of event types."""
        #Arrange - storage and recorder plugin
        storage: list = []
        plugin = ExternalRecorderPlugin(storage)
        bench = TestBench(
            coordinator=Core.create_coordinator(),
            log_coordinator=LogCoordinator(loggers=[]),
            plugins=[plugin],
        )

        #Act - full run of PingAction
        await bench.run(
            PingAction(),
            PingAction.Params(),
            rollup=False,
        )

        #Assert - sequence contains event types
        #(from both machines, so there can be 4 entries: start+finish × 2)
        assert "GlobalStartEvent" in storage
        assert "GlobalFinishEvent" in storage

    @pytest.mark.anyio
    async def test_selective_plugin_filters_by_action_name(self):
        """SelectiveCounterPlugin only responds to actions with "Simple" in the name.
        When running PingAction, the plugin does not receive events.
        When running SimpleAction, it gets it."""
        #Arrange - storage and filter plugin
        storage: list = []
        plugin = SelectiveCounterPlugin(storage)
        bench = TestBench(
            coordinator=Core.create_coordinator(),
            log_coordinator=LogCoordinator(loggers=[]),
            plugins=[plugin],
        )

        #Act - run PingAction (does not contain "Simple")
        await bench.run(
            PingAction(),
            PingAction.Params(),
            rollup=False,
        )

        #Assert - the plugin did not receive events from PingAction
        assert len(storage) == 0

        #Act - run SimpleAction (contains "Simple")
        await bench.run(
            SimpleAction(),
            SimpleAction.Params(name="Bob"),
            rollup=False,
        )

        #Assert - the plugin received events from SimpleAction
        assert len(storage) >= 1
        assert all("SimpleAction" in name for name in storage)

    @pytest.mark.anyio
    async def test_multiple_plugins_all_receive_events(self):
        """Two plugins at the same time: ExternalCounterPlugin and ExternalRecorderPlugin.
        Both receive events from the same PingAction run."""
        #Arrange - two repositories and two plugins
        counter_storage: list = []
        recorder_storage: list = []
        counter_plugin = ExternalCounterPlugin(counter_storage)
        recorder_plugin = ExternalRecorderPlugin(recorder_storage)

        bench = TestBench(
            coordinator=Core.create_coordinator(),
            log_coordinator=LogCoordinator(loggers=[]),
            plugins=[counter_plugin, recorder_plugin],
        )

        #Act - full run of PingAction
        await bench.run(
            PingAction(),
            PingAction.Params(),
            rollup=False,
        )

        #Assert - both plugins received events
        assert len(counter_storage) >= 1
        assert "GlobalStartEvent" in recorder_storage
        assert "GlobalFinishEvent" in recorder_storage

    @pytest.mark.anyio
    async def test_plugin_with_full_action_and_mocks(self):
        """ExternalCounterPlugin with FullAction - action with dependencies
        (PaymentService, NotificationService) and connection ("db").
        The plugin receives a GlobalFinishEvent from the full pipeline."""
        #Arrange - dependency mocks
        mock_payment = AsyncMock(spec=PaymentService)
        mock_payment.charge.return_value = "TXN-INTEGRATION-001"
        mock_notification = AsyncMock(spec=NotificationService)
        mock_notification.send.return_value = True
        mock_db = AsyncMock(spec=TestDbManager)

        #Arrange - storage and plugin
        storage: list = []
        plugin = ExternalCounterPlugin(storage)
        bench = TestBench(
            coordinator=Core.create_coordinator(),
            log_coordinator=LogCoordinator(loggers=[]),
            mocks={
                PaymentService: mock_payment,
                NotificationService: mock_notification,
            },
            plugins=[plugin],
        ).with_user(user_id="mgr_1", roles=(ManagerRole,))

        #Act - full run of FullAction with connections
        result = await bench.run(
            FullAction(),
            FullAction.Params(user_id="user_int", amount=500.0),
            rollup=False,
            connections={"db": mock_db},
        )

        #Assert - the result is correct
        assert result.order_id == "ORD-user_int"
        assert result.txn_id == "TXN-INTEGRATION-001"
        assert result.total == 500.0

        #Assert - the plugin received events from the full pipeline
        assert len(storage) >= 1
        assert all("FullAction" in record["action"] for record in storage)
        assert all("FullAction" in record["action"] for record in storage)
        assert all("FullAction" in record["action"] for record in storage)
