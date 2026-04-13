# tests/compensate/test_saga_integration.py
"""
Полные E2E-сценарии механизма компенсации (Saga).
═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════
Проверяет полный конвейер от начала до конца: несколько аспектов +
компенсаторы + @on_error, включая проверку результата, вызовов моков
и событий плагинов в одном прогоне.
═══════════════════════════════════════════════════════════════════════════════
СТРУКТУРА
═══════════════════════════════════════════════════════════════════════════════
TestFullSagaE2E — полные интеграционные сценарии
"""
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
# Фикстуры
# ═════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def saga_observer() -> SagaObserverPlugin:
    """Экземпляр SagaObserverPlugin — сбрасывается перед каждым тестом."""
    observer = SagaObserverPlugin()
    observer.reset()
    return observer


@pytest.fixture
def e2e_bench(
    mock_payment: AsyncMock,
    mock_inventory: AsyncMock,
    saga_observer: SagaObserverPlugin,
) -> TestBench:
    """TestBench с моками и SagaObserverPlugin — для E2E-сценариев."""
    return TestBench(
        mocks={
            PaymentService: mock_payment,
            InventoryService: mock_inventory,
        },
        plugins=[saga_observer],
        log_coordinator=AsyncMock(),
    )


def get_last_run_events(observer: SagaObserverPlugin) -> list[dict]:
    """
    Возвращает события от последнего прогона машины.
    TestBench.run() прогоняет две машины — collected_events содержит
    события от обоих. Берём от последнего SagaRollbackStartedEvent.
    """
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
    """Полные E2E-сценарии: аспекты → ошибка → размотка → результат."""

    @pytest.mark.anyio
    async def test_full_pipeline_with_compensators_and_on_error(
        self,
        e2e_bench: TestBench,
        saga_observer: SagaObserverPlugin,
        mock_payment: AsyncMock,
        mock_inventory: AsyncMock,
    ) -> None:
        """
        Полный конвейер: 3 аспекта, 2 компенсатора, ошибка в 3-м,
        размотка 2 фреймов, @on_error формирует результат.
        """
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

        # ── Assert: результат ──
        assert result.status == "handled_after_compensate"
        assert "Finalize error for user_e2e" in result.detail

        # ── Assert: компенсаторы вызваны ──
        assert mock_payment.refund.call_count >= 1
        assert mock_inventory.unreserve.call_count >= 1

        # ── Assert: события ──
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
        """
        Полный конвейер без @on_error: ошибка пробрасывается после размотки.
        """
        # ── Arrange ──
        params = CompensateTestParams(
            user_id="user_no_handler",
            amount=300.0,
            item_id="ITEM-NH1",
            should_fail=True,
        )

        # ── Act & Assert: ошибка пробрасывается ──
        with pytest.raises(ValueError, match="Finalize error for user_no_handler"):
            await e2e_bench.run(
                CompensatedOrderAction(),
                params,
                rollup=False,
            )

        # ── Assert: компенсаторы вызваны ──
        assert mock_payment.refund.call_count >= 1
        assert mock_inventory.unreserve.call_count >= 1

        # ── Assert: события ──
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
        """
        Компенсатор с @context_requires получает ContextView с user_id.
        """
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

        # ── Assert: компенсатор с контекстом вызван ──
        assert mock_payment.refund.call_count >= 1

        # ── Assert: события ──
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
        """
        При успешном выполнении компенсаторы не вызываются
        и Saga-события не эмитируются.
        """
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

        # ── Assert: результат успешный ──
        assert result.status == "ok"
        assert "TXN-TEST-001" in result.detail

        # ── Assert: компенсаторы НЕ вызваны ──
        assert mock_payment.refund.call_count == 0
        assert mock_inventory.unreserve.call_count == 0

        # ── Assert: Saga-события НЕ эмитированы ──
        assert len(saga_observer.collected_events) == 0
