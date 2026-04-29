# tests/intents/compensate/test_saga_events.py
"""Tests of typed plugin events when unwinding the compensation stack.
═══════════════════ ════════════════════ ════════════════════ ════════════════════
PURPOSE
═══════════════════ ════════════════════ ════════════════════ ════════════════════
Verifies that the ActionProductMachine emits the correct typed
events when unwinding the compensation stack via _rollback_saga():

Level of the WHOLE UNWINDING (saga-level):
- SagaRollbackStartedEvent - start of unwinding with stack metadata.
- SagaRollbackCompletedEvent - end of unwinding with results (succeeded,
  failed, skipped, duration_ms).

Level of ONE COMPENSATOR (compensator-level):
- BeforeCompensateAspectEvent - before calling each compensator.
- AfterCompensateAspectEvent - after a successful compensator.
- CompensateFailedEvent - when the compensator fails.

Events are checked through SagaObserverPlugin, which duplicates
each event in self.collected_events is an instance attribute,
directly accessible to tests. TestBench does not expose
PluginRunContext.get_plugin_state(), so per-request state
not accessible from outside.

TestBench.run() runs TWO machines (async and sync). Plugins
NOT reset between runs - collected_events contains events
from BOTH runs. Tests take into account doubling through filtering
second half or check >= N.
═══════════════════ ════════════════════ ════════════════════ ════════════════════
STRUCTURE
═══════════════════ ════════════════════ ════════════════════ ════════════════════
TestSagaRollbackEvents — saga-level events (Started, Completed)
TestCompensateAspectEvents — compensator-level events (Before, After)
TestCompensateFailedEvent - compensator failure event"""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from action_machine.testing import TestBench
from tests.scenarios.domain_model.compensate_actions import (
    CompensatedOrderAction,
    CompensateErrorAction,
    CompensateTestParams,
    PartialCompensateAction,
)
from tests.scenarios.domain_model.compensate_plugins import SagaObserverPlugin
from tests.scenarios.domain_model.services import (
    InventoryServiceResource,
    PaymentServiceResource,
)

# ═════════════════════════════════════════════════════════════════════════════
#Fixture: TestBench with SagaObserverPlugin
# ═════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def saga_observer() -> SagaObserverPlugin:
    """SagaObserverPlugin instance - reset before each test."""
    observer = SagaObserverPlugin()
    observer.reset()
    return observer


@pytest.fixture
def observed_bench(
    mock_payment: AsyncMock,
    mock_inventory: AsyncMock,
    saga_observer: SagaObserverPlugin,
) -> TestBench:
    """TestBench with SagaObserverPlugin - for checking emitted events.
    Contains mocks of PaymentService and InventoryService required for
    CompensatedOrderAction, CompensateErrorAction, PartialCompensateAction."""
    return TestBench(
        mocks={
            PaymentServiceResource: PaymentServiceResource(mock_payment),
            InventoryServiceResource: InventoryServiceResource(mock_inventory),
        },
        plugins=[saga_observer],
        log_coordinator=AsyncMock(),
    )


# ═════════════════════════════════════════════════════════════════════════════
#Helper function for receiving events from one run
# ═════════════════════════════════════════════════════════════════════════════


def get_last_run_events(observer: SagaObserverPlugin) -> list[dict]:
    """Returns events from the LAST machine run.

    TestBench.run() runs two machines (async and sync). Both runs
    emit events in collected_events. Every run starts
    with SagaRollbackStartedEvent and ends with SagaRollbackCompletedEvent.

    We return events from the SECOND run (sync) - this is the last set,
    which mocks see after _reset_all_mocks()."""
    events = observer.collected_events
    #Find the index of the last SagaRollbackStartedEvent
    last_start = -1
    for i, e in enumerate(events):
        if e["event_type"] == "SagaRollbackStartedEvent":
            last_start = i
    if last_start == -1:
        return events  #fallback - return everything
    return events[last_start:]


# ═════════════════════════════════════════════════════════════════════════════
#TestSagaRollbackEvents — saga-level events
# ═════════════════════════════════════════════════════════════════════════════


class TestSagaRollbackEvents:
    """Checks SagaRollbackStartedEvent and SagaRollbackCompletedEvent.

    These events are emitted ONCE per unwinding: Started - before
    by traversing the stack, Completed - after traversing all frames. Allow
    monitoring plugin to record the unwinding boundaries and results."""

    @pytest.mark.anyio
    async def test_saga_rollback_started_event_fields(
        self, observed_bench: TestBench, saga_observer: SagaObserverPlugin,
    ) -> None:
        """SagaRollbackStartedEvent contains stack_depth, compensator_count,
        aspect_names and error information."""
        # ── Arrange ──
        params = CompensateTestParams(
            user_id="user_started",
            amount=100.0,
            item_id="ITEM-S01",
            should_fail=True,
        )

        # ── Act ──
        with pytest.raises(ValueError):
            await observed_bench.run(
                CompensatedOrderAction(),
                params,
                rollup=False,
            )

        # ── Assert ──
        events = get_last_run_events(saga_observer)
        started = events[0]
        assert started["event_type"] == "SagaRollbackStartedEvent"
        assert started["error_type"] == "ValueError"
        assert "Finalize error" in started["error_message"]
        assert started["stack_depth"] == 2
        assert started["compensator_count"] == 2
        assert "reserve_aspect" in started["aspect_names"]
        assert "charge_aspect" in started["aspect_names"]

    @pytest.mark.anyio
    async def test_saga_rollback_completed_event_fields(
        self, observed_bench: TestBench, saga_observer: SagaObserverPlugin,
    ) -> None:
        """SagaRollbackCompletedEvent contains succeeded, failed, skipped,
        duration_ms and failed_aspects."""
        # ── Arrange ──
        params = CompensateTestParams(
            user_id="user_completed",
            amount=100.0,
            item_id="ITEM-C01",
            should_fail=True,
        )

        # ── Act ──
        with pytest.raises(ValueError):
            await observed_bench.run(
                CompensatedOrderAction(),
                params,
                rollup=False,
            )

        # ── Assert ──
        events = get_last_run_events(saga_observer)
        completed = events[-1]
        assert completed["event_type"] == "SagaRollbackCompletedEvent"
        assert completed["error_type"] == "ValueError"
        assert completed["total_frames"] == 2
        assert completed["succeeded"] == 2
        assert completed["failed"] == 0
        assert completed["skipped"] == 0
        assert completed["duration_ms"] >= 0
        assert completed["failed_aspects"] == []

    @pytest.mark.anyio
    async def test_event_order_started_then_compensators_then_completed(
        self, observed_bench: TestBench, saga_observer: SagaObserverPlugin,
    ) -> None:
        """Order of events: Started → (Before → After)* → Completed."""
        # ── Arrange ──
        params = CompensateTestParams(
            user_id="user_order",
            amount=100.0,
            item_id="ITEM-O01",
            should_fail=True,
        )

        # ── Act ──
        with pytest.raises(ValueError):
            await observed_bench.run(
                CompensatedOrderAction(),
                params,
                rollup=False,
            )

        # ── Assert ──
        events = get_last_run_events(saga_observer)
        event_types = [e["event_type"] for e in events]

        assert event_types[0] == "SagaRollbackStartedEvent"
        assert event_types[-1] == "SagaRollbackCompletedEvent"

        middle = event_types[1:-1]
        assert len(middle) == 4  #2 compensators × (Before + After)
        assert middle[0] == "BeforeCompensateAspectEvent"
        assert middle[1] == "AfterCompensateAspectEvent"
        assert middle[2] == "BeforeCompensateAspectEvent"
        assert middle[3] == "AfterCompensateAspectEvent"

    @pytest.mark.anyio
    async def test_completed_event_sparse_stack_partial_compensate(
        self, observed_bench: TestBench, saga_observer: SagaObserverPlugin,
    ) -> None:
        """PartialCompensateAction: only the charge aspect pushes a saga frame."""
        # ── Arrange ──
        params = CompensateTestParams(
            user_id="user_skip",
            amount=100.0,
            item_id="ITEM-SK1",
            should_fail=True,
        )

        # ── Act ──
        with pytest.raises(ValueError):
            await observed_bench.run(
                PartialCompensateAction(),
                params,
                rollup=False,
            )

        # ── Assert ──
        events = get_last_run_events(saga_observer)
        completed = events[-1]
        assert completed["event_type"] == "SagaRollbackCompletedEvent"
        assert completed["total_frames"] == 1
        assert completed["succeeded"] == 1
        assert completed["skipped"] == 0
        assert completed["failed"] == 0


# ═════════════════════════════════════════════════════════════════════════════
#TestCompensateAspectEvents — compensator-level events
# ═════════════════════════════════════════════════════════════════════════════


class TestCompensateAspectEvents:
    """Checks BeforeCompensateAspectEvent and AfterCompensateAspectEvent.

    Emitted once per saga stack frame (stack holds only actionable compensators).
    Before — before the call; After — after successful completion."""

    @pytest.mark.anyio
    async def test_before_compensate_event_contains_compensator_name(
        self, observed_bench: TestBench, saga_observer: SagaObserverPlugin,
    ) -> None:
        """BeforeCompensateAspectEvent contains compensator_name and aspect_name."""
        # ── Arrange ──
        params = CompensateTestParams(
            user_id="user_before",
            amount=100.0,
            item_id="ITEM-B01",
            should_fail=True,
        )

        # ── Act ──
        with pytest.raises(ValueError):
            await observed_bench.run(
                CompensatedOrderAction(),
                params,
                rollup=False,
            )

        # ── Assert ──
        events = get_last_run_events(saga_observer)
        before_events = [e for e in events if e["event_type"] == "BeforeCompensateAspectEvent"]
        assert len(before_events) == 2

        #Reverse order: first reserve, then charge
        assert before_events[0]["aspect_name"] == "reserve_aspect"
        assert before_events[0]["compensator_name"] == "rollback_reserve_compensate"
        assert before_events[1]["aspect_name"] == "charge_aspect"
        assert before_events[1]["compensator_name"] == "rollback_charge_compensate"

    @pytest.mark.anyio
    async def test_after_compensate_event_contains_duration(
        self, observed_bench: TestBench, saga_observer: SagaObserverPlugin,
    ) -> None:
        """AfterCompensateAspectEvent contains duration_ms >= 0 and compensator_name."""
        # ── Arrange ──
        params = CompensateTestParams(
            user_id="user_after",
            amount=100.0,
            item_id="ITEM-A01",
            should_fail=True,
        )

        # ── Act ──
        with pytest.raises(ValueError):
            await observed_bench.run(
                CompensatedOrderAction(),
                params,
                rollup=False,
            )

        # ── Assert ──
        events = get_last_run_events(saga_observer)
        after_events = [e for e in events if e["event_type"] == "AfterCompensateAspectEvent"]
        assert len(after_events) == 2

        for after_event in after_events:
            assert after_event["duration_ms"] >= 0
            assert "compensator_name" in after_event
            assert "aspect_name" in after_event


# ═════════════════════════════════════════════════════════════════════════════
#TestCompensateFailedEvent - compensator failure event
# ═════════════════════════════════════════════════════════════════════════════


class TestCompensateFailedEvent:
    """Checks CompensateFailedEvent - event emitted on failure
    compensator.

    CompensateErrorAction: rollback_charge_compensate throws RuntimeError.
    The machine suppresses the error, but emits a CompensateFailedEvent with two
    errors: original_error (aspect ValueError) and compensator_error
    (RuntimeError compensator)."""

    @pytest.mark.anyio
    async def test_compensate_failed_event_contains_both_errors(
        self, observed_bench: TestBench, saga_observer: SagaObserverPlugin,
    ) -> None:
        """CompensateFailedEvent contains original_error (aspect error),
        compensator_error (compensator error), compensator_name
        and failed_for_aspect."""
        # ── Arrange ──
        params = CompensateTestParams(
            user_id="user_failed",
            amount=100.0,
            item_id="ITEM-F01",
            should_fail=True,
        )

        # ── Act ──
        with pytest.raises(ValueError):
            await observed_bench.run(
                CompensateErrorAction(),
                params,
                rollup=False,
            )

        # ── Assert ──
        events = get_last_run_events(saga_observer)
        failed_events = [e for e in events if e["event_type"] == "CompensateFailedEvent"]
        assert len(failed_events) == 1

        failed = failed_events[0]
        assert failed["original_error_type"] == "ValueError"
        assert failed["compensator_error_type"] == "RuntimeError"
        assert "Payment gateway unavailable" in failed["compensator_error_message"]
        assert failed["compensator_name"] == "rollback_charge_compensate"
        assert failed["failed_for_aspect"] == "charge_aspect"

    @pytest.mark.anyio
    async def test_completed_event_reflects_failure(
        self, observed_bench: TestBench, saga_observer: SagaObserverPlugin,
    ) -> None:
        """SagaRollbackCompletedEvent after compensator failure:
        failed=1, succeeded=1, failed_aspects contains the aspect name."""
        # ── Arrange ──
        params = CompensateTestParams(
            user_id="user_refl",
            amount=100.0,
            item_id="ITEM-RF1",
            should_fail=True,
        )

        # ── Act ──
        with pytest.raises(ValueError):
            await observed_bench.run(
                CompensateErrorAction(),
                params,
                rollup=False,
            )

        # ── Assert ──
        events = get_last_run_events(saga_observer)
        completed = events[-1]
        assert completed["event_type"] == "SagaRollbackCompletedEvent"
        assert completed["succeeded"] == 1
        assert completed["failed"] == 1
        assert completed["skipped"] == 0
        assert "charge_aspect" in completed["failed_aspects"]
        assert "charge_aspect" in completed["failed_aspects"]
