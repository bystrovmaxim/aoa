# tests/scenarios/domain_model/compensate_plugins.py
"""
Observer plugins for compensation (Saga) events in tests.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Plugins subscribed to typed Saga events from BasePluginEvent. They write each
event into per-request plugin state and duplicate into the instance attribute
collected_events for direct access from tests.

Duplication is needed because TestBench does not expose
PluginRunContext.get_plugin_state(). Per-request state only exists for one
run inside the machine. collected_events is readable as saga_observer.collected_events.

Observer plugins cannot change outcomes or suppress errors — they only record
facts for assertions.

═══════════════════════════════════════════════════════════════════════════════
COMPENSATION EVENT TYPES
═══════════════════════════════════════════════════════════════════════════════
ActionProductMachine emits five compensation-related events from _rollback_saga():

Whole-rollback (saga) level:
    SagaRollbackStartedEvent — unwind begins. Fields:
        error, stack_depth, compensator_count, aspect_names.
    SagaRollbackCompletedEvent — unwind ends. Fields:
        error, total_frames, succeeded, failed, skipped,
        duration_ms, failed_aspects.

Single compensator level:
    BeforeCompensateAspectEvent — before a compensator. Fields:
        error, compensator_name, compensator_state_before,
        compensator_state_after.
    AfterCompensateAspectEvent — after a successful compensator. Fields:
        error, compensator_name, duration_ms.
    CompensateFailedEvent — compensator raised. Fields:
        original_error, compensator_error, compensator_name,
        failed_for_aspect.

═══════════════════════════════════════════════════════════════════════════════
PLUGINS
═══════════════════════════════════════════════════════════════════════════════
SagaObserverPlugin — records all five compensation event types into
    state["events"] (per-request) and self.collected_events (persistent).
    Each entry is a dict with event_type, action_name, and event-specific
    fields. Tests can assert full ordering and payloads.

═══════════════════════════════════════════════════════════════════════════════
USAGE IN TESTS
═══════════════════════════════════════════════════════════════════════════════
    from tests.scenarios.domain_model.compensate_plugins import SagaObserverPlugin

    observer = SagaObserverPlugin()
    bench = TestBench(
        plugins=[observer],
        log_coordinator=AsyncMock(),
    )

    await bench.run(action, params, rollup=False)

    events = observer.collected_events
    assert events[0]["event_type"] == "SagaRollbackStartedEvent"
    assert events[-1]["event_type"] == "SagaRollbackCompletedEvent"

═══════════════════════════════════════════════════════════════════════════════
DUPLICATE EVENTS FROM DUAL RUNS
═══════════════════════════════════════════════════════════════════════════════
TestBench.run() executes with both async and sync machines, with
_reset_all_mocks() between them. Plugins are not reset — collected_events
contains events from BOTH runs. Tests must account for duplication or call
observer.reset() before run().
"""
from action_machine.logging.scoped_logger import ScopedLogger
from action_machine.plugin.events import (
    AfterCompensateAspectEvent,
    BeforeCompensateAspectEvent,
    CompensateFailedEvent,
    SagaRollbackCompletedEvent,
    SagaRollbackStartedEvent,
)
from action_machine.intents.on.on_decorator import on
from action_machine.plugin.plugin import Plugin


class SagaObserverPlugin(Plugin):
    """
    Observer plugin that records all compensation events.

    Besides per-request state (for PluginRunContext), duplicates events into
    self.collected_events — a list of dicts tests read as
    saga_observer.collected_events after bench.run().

    This works around TestBench not exposing PluginRunContext.get_plugin_state().

    Per-request state: {"events": []}. Each event is a dict with event_type
    (class name) and extracted fields.

    Subscriptions:
    1. SagaRollbackStartedEvent — unwind start.
       Records: stack_depth, compensator_count, aspect_names.
    2. BeforeCompensateAspectEvent — before each compensator.
       Records: compensator_name, aspect_name.
    3. AfterCompensateAspectEvent — after successful compensator.
       Records: compensator_name, aspect_name, duration_ms.
    4. CompensateFailedEvent — compensator failure.
       Records: compensator_name, failed_for_aspect,
       original_error_type, compensator_error_type.
    5. SagaRollbackCompletedEvent — unwind complete.
       Records: total_frames, succeeded, failed, skipped,
       duration_ms, failed_aspects.

    Emission order: Started → (Before → After|Failed)* → Completed.
    """

    def __init__(self) -> None:
        super().__init__()
        self.collected_events: list[dict] = []

    def reset(self) -> None:
        """
        Clear collected events.

        Call from a fixture per test for isolation. TestBench runs two machines;
        without reset(), events accumulate across tests.
        """
        self.collected_events = []

    async def get_initial_state(self) -> dict:
        """Initial state — empty event list."""
        return {"events": []}

    @on(SagaRollbackStartedEvent)
    async def on_saga_started(
        self,
        state: dict,
        event: SagaRollbackStartedEvent,
        log: ScopedLogger | None,
    ) -> dict:
        """
        Record compensation unwind start.

        SagaRollbackStartedEvent fires once before walking the stack in reverse.
        Includes stack depth, compensator count, aspect names.
        """
        entry = {
            "event_type": "SagaRollbackStartedEvent",
            "action_name": event.action_name,
            "error_type": type(event.error).__name__,
            "error_message": str(event.error),
            "stack_depth": event.stack_depth,
            "compensator_count": event.compensator_count,
            "aspect_names": list(event.aspect_names),
        }
        state["events"].append(entry)
        self.collected_events.append(entry)
        return state

    @on(BeforeCompensateAspectEvent)
    async def on_before_compensate(
        self,
        state: dict,
        event: BeforeCompensateAspectEvent,
        log: ScopedLogger | None,
    ) -> dict:
        """
        Record the moment before one compensator runs.

        BeforeCompensateAspectEvent fires per frame that has a compensator
        (frames without compensators are skipped). Useful to assert reverse order.
        """
        entry = {
            "event_type": "BeforeCompensateAspectEvent",
            "action_name": event.action_name,
            "aspect_name": event.aspect_name,
            "compensator_name": event.compensator_name,
        }
        state["events"].append(entry)
        self.collected_events.append(entry)
        return state

    @on(AfterCompensateAspectEvent)
    async def on_after_compensate(
        self,
        state: dict,
        event: AfterCompensateAspectEvent,
        log: ScopedLogger | None,
    ) -> dict:
        """
        Record successful compensator completion.

        AfterCompensateAspectEvent fires only if the compensator did not raise.
        Includes duration_ms.
        """
        entry = {
            "event_type": "AfterCompensateAspectEvent",
            "action_name": event.action_name,
            "aspect_name": event.aspect_name,
            "compensator_name": event.compensator_name,
            "duration_ms": event.duration_ms,
        }
        state["events"].append(entry)
        self.collected_events.append(entry)
        return state

    @on(CompensateFailedEvent)
    async def on_compensate_failed(
        self,
        state: dict,
        event: CompensateFailedEvent,
        log: ScopedLogger | None,
    ) -> dict:
        """
        Record compensator failure.

        CompensateFailedEvent fires when a compensator raises. Carries
        original_error (aspect error that triggered unwind) and
        compensator_error (compensator exception). Unwind continues — later
        compensators may still run.
        """
        entry = {
            "event_type": "CompensateFailedEvent",
            "action_name": event.action_name,
            "aspect_name": event.aspect_name,
            "compensator_name": event.compensator_name,
            "failed_for_aspect": event.failed_for_aspect,
            "original_error_type": type(event.original_error).__name__,
            "compensator_error_type": type(event.compensator_error).__name__,
            "compensator_error_message": str(event.compensator_error),
        }
        state["events"].append(entry)
        self.collected_events.append(entry)
        return state

    @on(SagaRollbackCompletedEvent)
    async def on_saga_completed(
        self,
        state: dict,
        event: SagaRollbackCompletedEvent,
        log: ScopedLogger | None,
    ) -> dict:
        """
        Record compensation unwind completion.

        SagaRollbackCompletedEvent fires once after all stack frames are processed.
        Summarizes succeeded, failed, skipped, duration_ms, failed_aspects.
        """
        entry = {
            "event_type": "SagaRollbackCompletedEvent",
            "action_name": event.action_name,
            "error_type": type(event.error).__name__,
            "total_frames": event.total_frames,
            "succeeded": event.succeeded,
            "failed": event.failed,
            "skipped": event.skipped,
            "duration_ms": event.duration_ms,
            "failed_aspects": list(event.failed_aspects),
        }
        state["events"].append(entry)
        self.collected_events.append(entry)
        return state
