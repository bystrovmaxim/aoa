# tests/intents/compensate/test_saga_rollup.py
"""
Тесты поведения компенсации при rollup=True.
═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════
Проверяет, что при rollup=True компенсаторы работают так же, как при
rollup=False. Значение rollup влияет ТОЛЬКО на ресурсные менеджеры
(WrapperSqlConnectionManager выполняет ROLLBACK вместо COMMIT).
Компенсаторы — независимый механизм для отката нетранзакционных
побочных эффектов (HTTP-запросы к внешним сервисам). Они вызываются
при любом значении rollup.

Архитектурное решение: rollup=True НЕ отключает компенсацию.
rollup влияет только на ресурсные менеджеры. Компенсаторы и Saga-события
работают одинаково при rollup=True и rollup=False.
═══════════════════════════════════════════════════════════════════════════════
СТРУКТУРА
═══════════════════════════════════════════════════════════════════════════════
TestCompensatorsWorkWithRollup — компенсаторы вызываются при rollup=True
"""
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
# Фикстуры
# ═════════════════════════════════════════════════════════════════════════════


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


# ═════════════════════════════════════════════════════════════════════════════
# TestCompensatorsWorkWithRollup
# ═════════════════════════════════════════════════════════════════════════════


class TestCompensatorsWorkWithRollup:
    """
    Проверяет, что при rollup=True компенсаторы вызываются
    и Saga-события эмитируются — так же, как при rollup=False.

    rollup=True влияет ТОЛЬКО на ресурсные менеджеры
    (WrapperSqlConnectionManager выполняет ROLLBACK вместо COMMIT).
    Компенсаторы — независимый механизм отката нетранзакционных
    побочных эффектов (HTTP-запросы к внешним сервисам).
    """

    @pytest.mark.anyio
    async def test_compensators_called_with_rollup(
        self,
        rollup_bench: TestBench,
        mock_payment: AsyncMock,
        mock_inventory: AsyncMock,
    ) -> None:
        """
        При rollup=True компенсаторы вызываются — refund() и unreserve()
        должны быть вызваны при ошибке в аспекте.

        rollup не влияет на компенсацию. Компенсаторы откатывают
        нетранзакционные побочные эффекты (HTTP-запросы), которые
        не откатываются через WrapperSqlConnectionManager.
        """
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
        # Компенсаторы ВЫЗВАНЫ — rollup не отключает компенсацию
        assert mock_payment.refund.call_count >= 1
        assert mock_inventory.unreserve.call_count >= 1

    @pytest.mark.anyio
    async def test_saga_events_emitted_with_rollup(
        self,
        rollup_bench: TestBench,
        saga_observer: SagaObserverPlugin,
    ) -> None:
        """
        При rollup=True Saga-события эмитируются — SagaObserverPlugin
        получает SagaRollbackStartedEvent и SagaRollbackCompletedEvent.

        rollup не влияет на эмиссию событий компенсации.
        Плагины мониторинга получают полную информацию о размотке
        стека независимо от значения rollup.
        """
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
        # Saga-события ЭМИТИРОВАНЫ — rollup не отключает события
        events = get_last_run_events(saga_observer)
        assert len(events) > 0

        event_types = [e["event_type"] for e in events]
        assert "SagaRollbackStartedEvent" in event_types
        assert "SagaRollbackCompletedEvent" in event_types

        # Проверяем итоги размотки
        completed = next(
            e for e in events if e["event_type"] == "SagaRollbackCompletedEvent"
        )
        assert completed["succeeded"] == 2
        assert completed["failed"] == 0
        assert completed["skipped"] == 0
