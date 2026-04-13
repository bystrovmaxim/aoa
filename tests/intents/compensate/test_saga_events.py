# tests/intents/compensate/test_saga_events.py
"""
Тесты типизированных событий плагинов при размотке стека компенсации.
═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════
Проверяет, что ActionProductMachine эмитирует корректные типизированные
события при размотке стека компенсации через _rollback_saga():

Уровень ВСЕЙ РАЗМОТКИ (saga-level):
- SagaRollbackStartedEvent — начало размотки с метаданными стека.
- SagaRollbackCompletedEvent — конец размотки с итогами (succeeded,
  failed, skipped, duration_ms).

Уровень ОДНОГО КОМПЕНСАТОРА (compensator-level):
- BeforeCompensateAspectEvent — перед вызовом каждого компенсатора.
- AfterCompensateAspectEvent — после успешного компенсатора.
- CompensateFailedEvent — при сбое компенсатора.

События проверяются через SagaObserverPlugin, который дублирует
каждое событие в self.collected_events — атрибут экземпляра,
доступный тестам напрямую. TestBench не экспонирует
PluginRunContext.get_plugin_state(), поэтому per-request state
недоступен снаружи.

TestBench.run() прогоняет ДВЕ машины (async и sync). Плагины
НЕ сбрасываются между прогонами — collected_events содержит события
от ОБОИХ прогонов. Тесты учитывают удвоение через фильтрацию
второй половины или проверку >= N.
═══════════════════════════════════════════════════════════════════════════════
СТРУКТУРА
═══════════════════════════════════════════════════════════════════════════════
TestSagaRollbackEvents        — saga-level события (Started, Completed)
TestCompensateAspectEvents    — compensator-level события (Before, After)
TestCompensateFailedEvent     — событие сбоя компенсатора
"""
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
from tests.scenarios.domain_model.services import InventoryService, PaymentService

# ═════════════════════════════════════════════════════════════════════════════
# Фикстура: TestBench с SagaObserverPlugin
# ═════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def saga_observer() -> SagaObserverPlugin:
    """Экземпляр SagaObserverPlugin — сбрасывается перед каждым тестом."""
    observer = SagaObserverPlugin()
    observer.reset()
    return observer


@pytest.fixture
def observed_bench(
    mock_payment: AsyncMock,
    mock_inventory: AsyncMock,
    saga_observer: SagaObserverPlugin,
) -> TestBench:
    """
    TestBench с SagaObserverPlugin — для проверки эмитированных событий.
    Содержит моки PaymentService и InventoryService, необходимые для
    CompensatedOrderAction, CompensateErrorAction, PartialCompensateAction.
    """
    return TestBench(
        mocks={
            PaymentService: mock_payment,
            InventoryService: mock_inventory,
        },
        plugins=[saga_observer],
        log_coordinator=AsyncMock(),
    )


# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательная функция для получения событий от одного прогона
# ═════════════════════════════════════════════════════════════════════════════


def get_last_run_events(observer: SagaObserverPlugin) -> list[dict]:
    """
    Возвращает события от ПОСЛЕДНЕГО прогона машины.

    TestBench.run() прогоняет две машины (async и sync). Оба прогона
    эмитируют события в collected_events. Каждый прогон начинается
    с SagaRollbackStartedEvent и заканчивается SagaRollbackCompletedEvent.

    Возвращаем события от ВТОРОГО прогона (sync) — это последний набор,
    который видят моки после _reset_all_mocks().
    """
    events = observer.collected_events
    # Найти индекс последнего SagaRollbackStartedEvent
    last_start = -1
    for i, e in enumerate(events):
        if e["event_type"] == "SagaRollbackStartedEvent":
            last_start = i
    if last_start == -1:
        return events  # fallback — вернуть всё
    return events[last_start:]


# ═════════════════════════════════════════════════════════════════════════════
# TestSagaRollbackEvents — saga-level события
# ═════════════════════════════════════════════════════════════════════════════


class TestSagaRollbackEvents:
    """
    Проверяет SagaRollbackStartedEvent и SagaRollbackCompletedEvent.

    Эти события эмитируются ОДИН РАЗ за размотку: Started — перед
    обходом стека, Completed — после обхода всех фреймов. Позволяют
    плагину мониторинга зафиксировать границы размотки и итоги.
    """

    @pytest.mark.anyio
    async def test_saga_rollback_started_event_fields(
        self, observed_bench: TestBench, saga_observer: SagaObserverPlugin,
    ) -> None:
        """
        SagaRollbackStartedEvent содержит stack_depth, compensator_count,
        aspect_names и информацию об ошибке.
        """
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
        """
        SagaRollbackCompletedEvent содержит succeeded, failed, skipped,
        duration_ms и failed_aspects.
        """
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
        """
        Порядок событий: Started → (Before → After)* → Completed.
        """
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
        assert len(middle) == 4  # 2 компенсатора × (Before + After)
        assert middle[0] == "BeforeCompensateAspectEvent"
        assert middle[1] == "AfterCompensateAspectEvent"
        assert middle[2] == "BeforeCompensateAspectEvent"
        assert middle[3] == "AfterCompensateAspectEvent"

    @pytest.mark.anyio
    async def test_completed_event_with_skipped_frames(
        self, observed_bench: TestBench, saga_observer: SagaObserverPlugin,
    ) -> None:
        """
        PartialCompensateAction: компенсатор только у первого аспекта.
        Второй аспект (log_aspect) не имеет компенсатора → skipped=1.
        """
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
        assert completed["total_frames"] == 2
        assert completed["succeeded"] == 1
        assert completed["skipped"] == 1
        assert completed["failed"] == 0


# ═════════════════════════════════════════════════════════════════════════════
# TestCompensateAspectEvents — compensator-level события
# ═════════════════════════════════════════════════════════════════════════════


class TestCompensateAspectEvents:
    """
    Проверяет BeforeCompensateAspectEvent и AfterCompensateAspectEvent.

    Эти события эмитируются для КАЖДОГО фрейма с компенсатором.
    Before — перед вызовом, After — после успешного завершения.
    Фреймы без компенсатора пропускаются (ни Before, ни After).
    """

    @pytest.mark.anyio
    async def test_before_compensate_event_contains_compensator_name(
        self, observed_bench: TestBench, saga_observer: SagaObserverPlugin,
    ) -> None:
        """
        BeforeCompensateAspectEvent содержит compensator_name и aspect_name.
        """
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

        # Обратный порядок: сначала reserve, потом charge
        assert before_events[0]["aspect_name"] == "reserve_aspect"
        assert before_events[0]["compensator_name"] == "rollback_reserve_compensate"
        assert before_events[1]["aspect_name"] == "charge_aspect"
        assert before_events[1]["compensator_name"] == "rollback_charge_compensate"

    @pytest.mark.anyio
    async def test_after_compensate_event_contains_duration(
        self, observed_bench: TestBench, saga_observer: SagaObserverPlugin,
    ) -> None:
        """
        AfterCompensateAspectEvent содержит duration_ms >= 0 и compensator_name.
        """
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
# TestCompensateFailedEvent — событие сбоя компенсатора
# ═════════════════════════════════════════════════════════════════════════════


class TestCompensateFailedEvent:
    """
    Проверяет CompensateFailedEvent — событие, эмитируемое при сбое
    компенсатора.

    CompensateErrorAction: rollback_charge_compensate бросает RuntimeError.
    Машина подавляет ошибку, но эмитирует CompensateFailedEvent с двумя
    ошибками: original_error (ValueError аспекта) и compensator_error
    (RuntimeError компенсатора).
    """

    @pytest.mark.anyio
    async def test_compensate_failed_event_contains_both_errors(
        self, observed_bench: TestBench, saga_observer: SagaObserverPlugin,
    ) -> None:
        """
        CompensateFailedEvent содержит original_error (ошибка аспекта),
        compensator_error (ошибка компенсатора), compensator_name
        и failed_for_aspect.
        """
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
        """
        SagaRollbackCompletedEvent после сбоя компенсатора:
        failed=1, succeeded=1, failed_aspects содержит имя аспекта.
        """
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
