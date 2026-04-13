# tests/intents/compensate/test_saga_rollup.py
"""Tests of compensation behavior with rollup=True.
═══════════════════ ════════════════════ ════════════════════ ════════════════════
PURPOSE
═══════════════════ ════════════════════ ════════════════════ ════════════════════
Checks that with rollup=True the compensators work the same as with
rollup=False. The rollup value ONLY affects resource managers
(WrapperSqlConnectionManager does ROLLBACK instead of COMMIT).
Compensators are an independent mechanism for rolling back non-transactional
side effects (HTTP requests to external services). They are called
for any rollup value.

Architectural decision: rollup=True does NOT disable compensation.
rollup only affects resource managers. Compensators and Saga events
work the same for rollup=True and rollup=False.
═══════════════════ ════════════════════ ════════════════════ ════════════════════
STRUCTURE
═══════════════════ ════════════════════ ════════════════════ ════════════════════
TestCompensatorsWorkWithRollup - compensators are called when rollup=True"""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from action_machine.testing import TestBench
from tests.scenarios.domain_model.compensate_actions import (
    CompensatedOrderAction,
    CompensateTestParams,
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
def rollup_bench(
    mock_payment: AsyncMock,
    mock_inventory: AsyncMock,
    saga_observer: SagaObserverPlugin,
) -> TestBench:
    """TestBench with SagaObserverPlugin to run with rollup=True."""
    return TestBench(
        mocks={
            PaymentService: mock_payment,
            InventoryService: mock_inventory,
        },
        plugins=[saga_observer],
        log_coordinator=AsyncMock(),
    )


def get_last_run_events(observer: SagaObserverPlugin) -> list[dict]:
    """Returns events from the last run of the machine."""
    events = observer.collected_events
    last_start = -1
    for i, e in enumerate(events):
        if e["event_type"] == "SagaRollbackStartedEvent":
            last_start = i
    if last_start == -1:
        return events
    return events[last_start:]


# ═════════════════════════════════════════════════════════════════════════════
# TestCompensatorsWorkWithRollup
# ═════════════════════════════════════════════════════════════════════════════


class TestCompensatorsWorkWithRollup:
    """Checks that when rollup=True compensators are called
    and Saga events are emitted - the same as with rollup=False.

    rollup=True ONLY affects resource managers
    (WrapperSqlConnectionManager does ROLLBACK instead of COMMIT).
    Compensators are an independent mechanism for rolling back non-transactional
    side effects (HTTP requests to external services)."""

    @pytest.mark.anyio
    async def test_compensators_called_with_rollup(
        self,
        rollup_bench: TestBench,
        mock_payment: AsyncMock,
        mock_inventory: AsyncMock,
    ) -> None:
        """When rollup=True, compensators are called - refund() and unreserve()
        must be called when an aspect fails.

        rollup does not affect compensation. Compensators roll back
        non-transactional side effects (HTTP requests) that
        are not rolled back via WrapperSqlConnectionManager."""
        # ── Arrange ──
        params = CompensateTestParams(
            user_id="user_rollup",
            amount=100.0,
            item_id="ITEM-RU1",
            should_fail=True,
        )

        # ── Act ──
        with pytest.raises(ValueError, match="Finalize error"):
            await rollup_bench.run(
                CompensatedOrderAction(),
                params,
                rollup=True,
            )

        # ── Assert ──
        #Compensators CALLED - rollup does not disable compensation
        assert mock_payment.refund.call_count >= 1
        assert mock_inventory.unreserve.call_count >= 1

    @pytest.mark.anyio
    async def test_saga_events_emitted_with_rollup(
        self,
        rollup_bench: TestBench,
        saga_observer: SagaObserverPlugin,
    ) -> None:
        """When rollup=True Saga events are emitted - SagaObserverPlugin
        receives SagaRollbackStartedEvent and SagaRollbackCompletedEvent.

        rollup does not affect the emission of compensation events.
        Monitoring plugins receive complete information about unwinding
        stack regardless of the value of rollup."""
        # ── Arrange ──
        params = CompensateTestParams(
            user_id="user_events_rollup",
            amount=200.0,
            item_id="ITEM-ER1",
            should_fail=True,
        )

        # ── Act ──
        with pytest.raises(ValueError):
            await rollup_bench.run(
                CompensatedOrderAction(),
                params,
                rollup=True,
            )

        # ── Assert ──
        #Saga events are EMITTED - rollup does not disable events
        events = get_last_run_events(saga_observer)
        assert len(events) > 0

        event_types = [e["event_type"] for e in events]
        assert "SagaRollbackStartedEvent" in event_types
        assert "SagaRollbackCompletedEvent" in event_types

        #Checking the unwinding results
        completed = next(
            e for e in events if e["event_type"] == "SagaRollbackCompletedEvent"
        )
        assert completed["succeeded"] == 2
        assert completed["failed"] == 0
        assert completed["skipped"] == 0
        assert completed["skipped"] == 0
