# tests/intents/compensate/test_saga_integration.py
"""Complete E2E compensation mechanism scenarios (Saga).
═══════════════════ ════════════════════ ════════════════════ ════════════════════
PURPOSE
═══════════════════ ════════════════════ ════════════════════ ════════════════════
Tests the complete pipeline from start to finish: several aspects +
compensators + @on_error, including checking the result of mock calls
and plugin events in one run.
═══════════════════ ════════════════════ ════════════════════ ════════════════════
STRUCTURE
═══════════════════ ════════════════════ ════════════════════ ════════════════════
TestFullSagaE2E - complete integration scripts"""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from action_machine.testing import StubTesterRole, TestBench
from tests.scenarios.domain_model.compensate_actions import (
    CompensateAndOnErrorAction,
    CompensatedOrderAction,
    CompensateTestParams,
    CompensateWithContextAction,
)
from tests.scenarios.domain_model.compensate_plugins import SagaObserverPlugin
from tests.scenarios.domain_model.services import InventoryService, PaymentService

# ═════════════════════════════════════════════════════════════════════════════
#Fittings
# ═════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def saga_observer() -> SagaObserverPlugin:
    """SagaObserverPlugin instance - reset before each test."""
    observer = SagaObserverPlugin()
    observer.reset()
    return observer


@pytest.fixture
def e2e_bench(
    mock_payment: AsyncMock,
    mock_inventory: AsyncMock,
    saga_observer: SagaObserverPlugin,
) -> TestBench:
    """TestBench with mocks and SagaObserverPlugin - for E2E scenarios."""
    return TestBench(
        mocks={
            PaymentService: mock_payment,
            InventoryService: mock_inventory,
        },
        plugins=[saga_observer],
        log_coordinator=AsyncMock(),
    )


def get_last_run_events(observer: SagaObserverPlugin) -> list[dict]:
    """Returns events from the last run of the machine.
    TestBench.run() runs two cars - collected_events contains
    events from both. We take from the last SagaRollbackStartedEvent."""
    events = observer.collected_events
    last_start = -1
    for i, e in enumerate(events):
        if e["event_type"] == "SagaRollbackStartedEvent":
            last_start = i
    if last_start == -1:
        return events
    return events[last_start:]


# ═════════════════════════════════════════════════════════════════════════════
# TestFullSagaE2E
# ═════════════════════════════════════════════════════════════════════════════


class TestFullSagaE2E:
    """Complete E2E scenarios: aspects → error → unwinding → result."""

    @pytest.mark.anyio
    async def test_full_pipeline_with_compensators_and_on_error(
        self,
        e2e_bench: TestBench,
        saga_observer: SagaObserverPlugin,
        mock_payment: AsyncMock,
        mock_inventory: AsyncMock,
    ) -> None:
        """Full pipeline: 3 aspects, 2 compensators, error in 3rd,
        unwinding 2 frames, @on_error generates the result."""
        # ── Arrange ──
        params = CompensateTestParams(
            user_id="user_e2e",
            amount=500.0,
            item_id="ITEM-E2E",
            should_fail=True,
        )

        # ── Act ──
        result = await e2e_bench.run(
            CompensateAndOnErrorAction(),
            params,
            rollup=False,
        )

        #── Assert: result ──
        assert result.status == "handled_after_compensate"
        assert "Finalize error for user_e2e" in result.detail

        #── Assert: compensators are called ──
        assert mock_payment.refund.call_count >= 1
        assert mock_inventory.unreserve.call_count >= 1

        #── Assert: events ──
        events = get_last_run_events(saga_observer)
        event_types = [e["event_type"] for e in events]

        assert event_types[0] == "SagaRollbackStartedEvent"
        assert event_types[-1] == "SagaRollbackCompletedEvent"

        completed = events[-1]
        assert completed["succeeded"] == 2
        assert completed["failed"] == 0
        assert completed["skipped"] == 0
        assert completed["duration_ms"] >= 0

    @pytest.mark.anyio
    async def test_full_pipeline_without_on_error_propagates_exception(
        self,
        e2e_bench: TestBench,
        saga_observer: SagaObserverPlugin,
        mock_payment: AsyncMock,
        mock_inventory: AsyncMock,
    ) -> None:
        """Full pipeline without @on_error: the error is thrown after unwinding."""
        # ── Arrange ──
        params = CompensateTestParams(
            user_id="user_no_handler",
            amount=300.0,
            item_id="ITEM-NH1",
            should_fail=True,
        )

        #── Act & Assert: error is thrown ──
        with pytest.raises(ValueError, match="Finalize error for user_no_handler"):
            await e2e_bench.run(
                CompensatedOrderAction(),
                params,
                rollup=False,
            )

        #── Assert: compensators are called ──
        assert mock_payment.refund.call_count >= 1
        assert mock_inventory.unreserve.call_count >= 1

        #── Assert: events ──
        events = get_last_run_events(saga_observer)
        completed = next(
            e for e in events if e["event_type"] == "SagaRollbackCompletedEvent"
        )
        assert completed["succeeded"] == 2
        assert completed["failed"] == 0

    @pytest.mark.anyio
    async def test_compensator_with_context_requires(
        self,
        mock_payment: AsyncMock,
        saga_observer: SagaObserverPlugin,
    ) -> None:
        """The compensator with @context_requires gets the ContextView with user_id."""
        # ── Arrange ──
        bench = TestBench(
            mocks={PaymentService: mock_payment},
            plugins=[saga_observer],
            log_coordinator=AsyncMock(),
        ).with_user(user_id="ctx_user_42", roles=(StubTesterRole,))

        params = CompensateTestParams(
            user_id="ctx_user_42",
            amount=150.0,
            item_id="ITEM-CTX",
            should_fail=True,
        )

        # ── Act ──
        with pytest.raises(ValueError, match="Finalize error"):
            await bench.run(
                CompensateWithContextAction(),
                params,
                rollup=False,
            )

        #── Assert: compensator with context is called ──
        assert mock_payment.refund.call_count >= 1

        #── Assert: events ──
        events = get_last_run_events(saga_observer)
        completed = next(
            e for e in events if e["event_type"] == "SagaRollbackCompletedEvent"
        )
        assert completed["succeeded"] == 1
        assert completed["failed"] == 0

    @pytest.mark.anyio
    async def test_no_compensators_no_saga_events_on_success(
        self,
        e2e_bench: TestBench,
        saga_observer: SagaObserverPlugin,
        mock_payment: AsyncMock,
        mock_inventory: AsyncMock,
    ) -> None:
        """If successful, compensators are not called
        and Saga events are not issued."""
        # ── Arrange ──
        params = CompensateTestParams(
            user_id="user_success",
            amount=100.0,
            item_id="ITEM-OK",
            should_fail=False,
        )

        # ── Act ──
        result = await e2e_bench.run(
            CompensatedOrderAction(),
            params,
            rollup=False,
        )

        #── Assert: the result is successful ──
        assert result.status == "ok"
        assert "TXN-TEST-001" in result.detail

        #── Assert: compensators are NOT called ──
        assert mock_payment.refund.call_count == 0
        assert mock_inventory.unreserve.call_count == 0

        #── Assert: Saga events are NOT issued ──
        assert len(saga_observer.collected_events) == 0
        assert len(saga_observer.collected_events) == 0
