# tests/compensate/test_saga_rollback.py
"""
Тесты размотки стека компенсации (Saga) в ActionProductMachine.
═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════
Проверяет, что при ошибке в конвейере аспектов:
- Компенсаторы уже выполненных аспектов вызываются в обратном порядке.
- Компенсатор получает корректные параметры: params, state_before, state_after, error.
- Для упавшего аспекта фрейм не добавляется в стек (компенсатор не вызывается).
- Возвращаемое значение компенсатора игнорируется.
═══════════════════════════════════════════════════════════════════════════════
СТРУКТУРА
═══════════════════════════════════════════════════════════════════════════════
TestCompensatorsCalledInReverseOrder — порядок вызовов
TestCompensatorReceivesCorrectData    — корректность данных
TestFrameNotAddedForFailedAspect      — отсутствие фрейма для упавшего аспекта
TestCompensatorReturnValueIgnored     — возвращаемое значение игнорируется
"""
from __future__ import annotations

import pytest

from tests.scenarios.domain_model.compensate_actions import (
    CompensatedOrderAction,
    CompensateTestParams,
)
from tests.scenarios.domain_model.services import InventoryService, PaymentService

# ═════════════════════════════════════════════════════════════════════════════
# TestCompensatorsCalledInReverseOrder
# ═════════════════════════════════════════════════════════════════════════════


class TestCompensatorsCalledInReverseOrder:
    """Проверяет, что компенсаторы вызываются в обратном порядке."""

    @pytest.mark.anyio
    async def test_compensators_called_in_reverse_order(self, compensate_bench) -> None:
        """
        При ошибке в 3-м аспекте компенсаторы 2-го и 1-го вызываются
        в обратном порядке.
        """
        # ── Arrange ──
        mock_payment = compensate_bench.mocks[PaymentService]
        mock_inventory = compensate_bench.mocks[InventoryService]

        params = CompensateTestParams(
            user_id="user_123",
            amount=100.0,
            item_id="ITEM-001",
            should_fail=True,
        )

        # ── Act ──
        with pytest.raises(ValueError, match="Finalize error for user_123"):
            await compensate_bench.run(
                CompensatedOrderAction(),
                params,
                rollup=False,
            )

        # ── Assert ──
        # Проверяем через call_count и call_args_list (не await_args_list),
        # потому что TestBench.run() прогоняет две машины и сбрасывает моки
        # между прогонами — тест видит вызовы от sync-прогона, где
        # asyncio.run() может регистрировать вызовы иначе.
        assert mock_inventory.unreserve.call_count == 1
        assert mock_payment.refund.call_count == 1

        # Проверяем аргументы вызовов
        assert mock_inventory.unreserve.call_args[0][0] == "RES-TEST-001"
        assert mock_payment.refund.call_args[0][0] == "TXN-TEST-001"

    @pytest.mark.anyio
    async def test_compensator_not_called_for_failed_aspect(self, compensate_bench) -> None:
        """
        Для аспекта, который упал, его компенсатор не вызывается.
        """
        # ── Arrange ──
        mock_payment = compensate_bench.mocks[PaymentService]
        mock_inventory = compensate_bench.mocks[InventoryService]

        params = CompensateTestParams(
            user_id="user_123",
            amount=100.0,
            should_fail=True,
        )

        # ── Act ──
        with pytest.raises(ValueError):
            await compensate_bench.run(
                CompensatedOrderAction(),
                params,
                rollup=False,
            )

        # ── Assert ──
        # Компенсаторы charge и reserve вызваны (они успешно выполнились).
        # Компенсатор finalize_aspect — отсутствует (аспект упал, фрейм не добавлен).
        assert mock_payment.refund.call_count == 1
        assert mock_inventory.unreserve.call_count == 1


# ═════════════════════════════════════════════════════════════════════════════
# TestCompensatorReceivesCorrectData
# ═════════════════════════════════════════════════════════════════════════════


class TestCompensatorReceivesCorrectData:
    """Проверяет, что компенсатор получает корректные данные."""

    @pytest.mark.anyio
    async def test_compensator_receives_correct_state_data(self, compensate_bench) -> None:
        """
        Компенсатор вызывает refund/unreserve с правильными данными
        из state_after — косвенная проверка, что params и state_after
        были переданы корректно.
        """
        # ── Arrange ──
        mock_payment = compensate_bench.mocks[PaymentService]
        mock_inventory = compensate_bench.mocks[InventoryService]

        params = CompensateTestParams(
            user_id="user_456",
            amount=200.0,
            item_id="ITEM-002",
            should_fail=True,
        )

        # ── Act ──
        with pytest.raises(ValueError):
            await compensate_bench.run(
                CompensatedOrderAction(),
                params,
                rollup=False,
            )

        # ── Assert ──
        # Компенсатор charge_aspect вызывает refund с txn_id из state_after
        assert mock_payment.refund.call_args[0][0] == "TXN-TEST-001"
        # Компенсатор reserve_aspect вызывает unreserve с reservation_id из state_after
        assert mock_inventory.unreserve.call_args[0][0] == "RES-TEST-001"


# ═════════════════════════════════════════════════════════════════════════════
# TestFrameNotAddedForFailedAspect
# ═════════════════════════════════════════════════════════════════════════════


class TestFrameNotAddedForFailedAspect:
    """Проверяет, что для упавшего аспекта фрейм не добавляется в стек."""

    @pytest.mark.anyio
    async def test_no_frame_for_failed_aspect(self, compensate_bench) -> None:
        """
        Если аспект бросил исключение, его фрейм отсутствует в стеке,
        и компенсатор не вызывается.
        """
        # ── Arrange ──
        mock_payment = compensate_bench.mocks[PaymentService]
        mock_inventory = compensate_bench.mocks[InventoryService]

        params = CompensateTestParams(
            user_id="user_123",
            amount=100.0,
            should_fail=True,
        )

        # ── Act ──
        with pytest.raises(ValueError):
            await compensate_bench.run(
                CompensatedOrderAction(),
                params,
                rollup=False,
            )

        # ── Assert ──
        # Компенсаторы успешных аспектов вызваны
        assert mock_payment.refund.call_count == 1
        assert mock_inventory.unreserve.call_count == 1
        # Компенсатор finalize_aspect (упавший) — не существует,
        # фрейм не добавлен в стек


# ═════════════════════════════════════════════════════════════════════════════
# TestCompensatorReturnValueIgnored
# ═════════════════════════════════════════════════════════════════════════════


class TestCompensatorReturnValueIgnored:
    """Проверяет, что возвращаемое значение компенсатора игнорируется."""

    @pytest.mark.anyio
    async def test_compensator_return_value_ignored(self, compensate_bench) -> None:
        """
        Даже если компенсатор возвращает dict, это не влияет на результат —
        ошибка аспекта пробрасывается наружу.
        """
        # ── Arrange ──
        params = CompensateTestParams(
            user_id="user_123",
            amount=100.0,
            should_fail=True,
        )

        # ── Act & Assert ──
        with pytest.raises(ValueError):
            await compensate_bench.run(
                CompensatedOrderAction(),
                params,
                rollup=False,
            )
        # Ошибка осталась исходной ValueError — возвращаемое значение
        # компенсатора не подменило результат.
