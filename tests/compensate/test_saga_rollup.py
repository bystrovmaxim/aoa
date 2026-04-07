# tests/compensate/test_saga_rollup.py
"""
Тесты поведения компенсации при rollup=True.
═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════
Проверяет, что при rollup=True:
- Компенсаторы НЕ вызываются.
- Saga-события НЕ эмитируются.
═══════════════════════════════════════════════════════════════════════════════
СТРУКТУРА
═══════════════════════════════════════════════════════════════════════════════
TestNoCompensatorsWithRollup — компенсаторы и события не срабатывают
"""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from action_machine.testing import TestBench
from tests.domain.compensate_actions import (
    CompensatedOrderAction,
    CompensateTestParams,
)
from tests.domain.compensate_plugins import SagaObserverPlugin
from tests.domain.services import InventoryService, PaymentService


@pytest.fixture
def saga_observer() -> SagaObserverPlugin:
    """Экземпляр SagaObserverPlugin — сбрасывается перед каждым тестом."""
    observer = SagaObserverPlugin()
    observer.reset()
    return observer


@pytest.fixture
def rollup_bench(
    mock_payment: AsyncMock,
    mock_inventory: AsyncMock,
    saga_observer: SagaObserverPlugin,
) -> TestBench:
    """TestBench с SagaObserverPlugin для запуска с rollup=True."""
    return TestBench(
        mocks={
            PaymentService: mock_payment,
            InventoryService: mock_inventory,
        },
        plugins=[saga_observer],
        log_coordinator=AsyncMock(),
    )


class TestNoCompensatorsWithRollup:
    """Проверяет, что при rollup=True компенсаторы не вызываются."""

    @pytest.mark.anyio
    async def test_compensators_not_called_with_rollup(
        self,
        rollup_bench: TestBench,
        mock_payment: AsyncMock,
        mock_inventory: AsyncMock,
    ) -> None:
        """При rollup=True refund() и unreserve() не вызываются."""
        # ── Arrange ──
        params = CompensateTestParams(
            user_id="user_rollup",
            amount=100.0,
            item_id="ITEM-RU1",
            should_fail=True,
        )

        # ── Act ──
        with pytest.raises(ValueError, match="Ошибка финализации"):
            await rollup_bench.run(
                CompensatedOrderAction(),
                params,
                rollup=True,
            )

        # ── Assert ──
        assert mock_payment.refund.call_count == 0
        assert mock_inventory.unreserve.call_count == 0

    @pytest.mark.anyio
    async def test_saga_events_not_emitted_with_rollup(
        self,
        rollup_bench: TestBench,
        saga_observer: SagaObserverPlugin,
    ) -> None:
        """При rollup=True Saga-события не эмитируются."""
        # ── Arrange ──
        params = CompensateTestParams(
            user_id="user_no_events",
            amount=200.0,
            item_id="ITEM-NE1",
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
        assert len(saga_observer.collected_events) == 0
