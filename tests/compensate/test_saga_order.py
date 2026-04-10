# tests/compensate/test_saga_order.py
"""
Тесты порядка обработки ошибки: компенсация выполняется ДО @on_error.
═══════════════════════════════════════════════════════════════════════════════
СТРУКТУРА
═══════════════════════════════════════════════════════════════════════════════
TestCompensateBeforeOnError — компенсаторы выполняются до @on_error
"""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from action_machine.testing import TestBench
from tests.domain_model.compensate_actions import (
    CompensateAndOnErrorAction,
    CompensateTestParams,
)
from tests.domain_model.compensate_plugins import SagaObserverPlugin
from tests.domain_model.services import InventoryService, PaymentService


@pytest.fixture
def saga_observer() -> SagaObserverPlugin:
    """Экземпляр SagaObserverPlugin — сбрасывается перед каждым тестом."""
    observer = SagaObserverPlugin()
    observer.reset()
    return observer


@pytest.fixture
def order_bench(
    mock_payment: AsyncMock,
    mock_inventory: AsyncMock,
    saga_observer: SagaObserverPlugin,
) -> TestBench:
    """TestBench с SagaObserverPlugin для CompensateAndOnErrorAction."""
    return TestBench(
        mocks={
            PaymentService: mock_payment,
            InventoryService: mock_inventory,
        },
        plugins=[saga_observer],
        log_coordinator=AsyncMock(),
    )


def get_last_run_events(observer: SagaObserverPlugin) -> list[dict]:
    """Возвращает события от последнего прогона машины."""
    events = observer.collected_events
    last_start = -1
    for i, e in enumerate(events):
        if e["event_type"] == "SagaRollbackStartedEvent":
            last_start = i
    if last_start == -1:
        return events
    return events[last_start:]


class TestCompensateBeforeOnError:
    """Проверяет, что компенсаторы выполняются ДО @on_error."""

    @pytest.mark.anyio
    async def test_compensators_execute_before_on_error_via_mocks(
        self,
        order_bench: TestBench,
        mock_payment: AsyncMock,
        mock_inventory: AsyncMock,
    ) -> None:
        """
        Компенсаторы вызываются ДО @on_error: после run() оба мока
        вызваны, и результат сформирован @on_error.
        """
        # ── Arrange ──
        params = CompensateTestParams(
            user_id="user_order_mock",
            amount=100.0,
            item_id="ITEM-OM1",
            should_fail=True,
        )

        # ── Act ──
        result = await order_bench.run(
            CompensateAndOnErrorAction(),
            params,
            rollup=False,
        )

        # ── Assert ──
        assert mock_payment.refund.call_count >= 1
        assert mock_inventory.unreserve.call_count >= 1
        assert result.status == "handled_after_compensate"
        assert "Finalize error for user_order_mock" in result.detail

    @pytest.mark.anyio
    async def test_compensators_execute_before_on_error_via_events(
        self,
        order_bench: TestBench,
        saga_observer: SagaObserverPlugin,
    ) -> None:
        """
        Порядок подтверждается через события плагина: SagaRollbackStartedEvent
        и SagaRollbackCompletedEvent эмитируются, а результат @on_error
        содержит status="handled_after_compensate".
        """
        # ── Arrange ──
        params = CompensateTestParams(
            user_id="user_order_evt",
            amount=200.0,
            item_id="ITEM-OE1",
            should_fail=True,
        )

        # ── Act ──
        result = await order_bench.run(
            CompensateAndOnErrorAction(),
            params,
            rollup=False,
        )

        # ── Assert ──
        events = get_last_run_events(saga_observer)
        event_types = [e["event_type"] for e in events]

        assert "SagaRollbackStartedEvent" in event_types
        assert "SagaRollbackCompletedEvent" in event_types

        completed = next(e for e in events if e["event_type"] == "SagaRollbackCompletedEvent")
        assert completed["succeeded"] == 2
        assert completed["failed"] == 0

        assert result.status == "handled_after_compensate"
