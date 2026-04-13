# tests/compensate/test_saga_errors.py
"""
Тесты молчаливого подавления ошибок компенсаторов.
═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════
Проверяет, что ошибки компенсаторов:
- Не прерывают размотку стека — все последующие компенсаторы вызываются.
- Не пробрасываются наружу — @on_error получает ОРИГИНАЛЬНУЮ ошибку аспекта.
- Не подменяют исходную ошибку — вызывающий код видит ValueError аспекта,
  а не RuntimeError компенсатора.

Архитектурное решение: ошибки компенсаторов полностью подавляются внутри
_rollback_saga(). Вместо проброса используется типизированное событие
CompensateFailedEvent, на которое плагин мониторинга может подписаться.
═══════════════════════════════════════════════════════════════════════════════
СТРУКТУРА
═══════════════════════════════════════════════════════════════════════════════
TestCompensatorErrorSuppressed     — ошибка компенсатора подавляется
TestAllCompensatorsCalled          — все компенсаторы получают шанс выполниться
TestOnErrorReceivesOriginalError   — @on_error получает оригинальную ошибку
TestOnErrorReceivesStateAfterRegularPipeline — после regular в state для @on_error
TestOnErrorPipelineStateAtFailureSite — пустой state / только первый аспект / summary
"""
from __future__ import annotations

import pytest

from tests.scenarios.domain_model.compensate_actions import (
    CompensateAndOnErrorAction,
    CompensateErrorAction,
    CompensateTestParams,
    FirstRegularFailsOnErrorAction,
    SecondRegularFailsOnErrorAction,
    SummaryFailsOnErrorStateAction,
)
from tests.scenarios.domain_model.services import InventoryService, PaymentService

# ═════════════════════════════════════════════════════════════════════════════
# TestCompensatorErrorSuppressed
# ═════════════════════════════════════════════════════════════════════════════


class TestCompensatorErrorSuppressed:
    """
    Проверяет, что ошибка компенсатора подавляется и не прерывает размотку.

    CompensateErrorAction имеет два компенсатора:
    - rollback_charge_compensate — БРОСАЕТ RuntimeError.
    - rollback_reserve_compensate — работает нормально.

    При ошибке в fail_aspect (ValueError) размотка идёт в обратном порядке:
    1. rollback_reserve_compensate → успех.
    2. rollback_charge_compensate → RuntimeError → ПОДАВЛЕНО.

    Наружу пробрасывается ИСХОДНАЯ ValueError аспекта, а не RuntimeError
    компенсатора.
    """

    @pytest.mark.anyio
    async def test_compensator_error_suppressed_original_error_propagated(
        self, compensate_bench,
    ) -> None:
        """
        Ошибка компенсатора подавляется — наружу пробрасывается исходная
        ValueError аспекта, а не RuntimeError компенсатора.
        """
        # ── Arrange ──
        params = CompensateTestParams(
            user_id="user_err",
            amount=100.0,
            item_id="ITEM-ERR",
            should_fail=True,
        )

        # ── Act & Assert ──
        with pytest.raises(ValueError, match="Finalize error"):
            await compensate_bench.run(
                CompensateErrorAction(),
                params,
                rollup=False,
            )


# ═════════════════════════════════════════════════════════════════════════════
# TestAllCompensatorsCalled
# ═════════════════════════════════════════════════════════════════════════════


class TestAllCompensatorsCalled:
    """
    Проверяет, что если первый компенсатор (в порядке размотки) упал,
    второй всё равно вызывается.

    Порядок размотки для CompensateErrorAction:
    1. rollback_reserve_compensate (последний успешный → первый в размотке).
    2. rollback_charge_compensate (первый успешный → второй в размотке).

    rollback_charge_compensate бросает RuntimeError, но rollback_reserve_compensate
    уже вызван до него. Проверяем, что ОБА получили шанс выполниться.
    """

    @pytest.mark.anyio
    async def test_all_compensators_called_despite_error(
        self, compensate_bench,
    ) -> None:
        """
        Оба компенсатора вызываются: unreserve() успешно, затем
        rollback_charge_compensate бросает RuntimeError — но unreserve()
        уже вызван, и размотка завершается.
        """
        # ── Arrange ──
        mock_inventory = compensate_bench.mocks[InventoryService]

        params = CompensateTestParams(
            user_id="user_all",
            amount=200.0,
            item_id="ITEM-ALL",
            should_fail=True,
        )

        # ── Act ──
        with pytest.raises(ValueError):
            await compensate_bench.run(
                CompensateErrorAction(),
                params,
                rollup=False,
            )

        # ── Assert ──
        # unreserve() вызван — компенсатор reserve_aspect выполнился
        # несмотря на то, что компенсатор charge_aspect бросил RuntimeError.
        # Используем call_count вместо assert_awaited, потому что
        # TestBench.run() прогоняет две машины с _reset_all_mocks() между ними.
        assert mock_inventory.unreserve.call_count == 1
        assert mock_inventory.unreserve.call_args[0][0] == "RES-TEST-001"


# ═════════════════════════════════════════════════════════════════════════════
# TestOnErrorReceivesOriginalError
# ═════════════════════════════════════════════════════════════════════════════


class TestOnErrorReceivesOriginalError:
    """
    Проверяет, что @on_error получает ОРИГИНАЛЬНУЮ ошибку аспекта,
    а не ошибку компенсатора.

    CompensateAndOnErrorAction имеет:
    - Два компенсатора (оба работают нормально).
    - @on_error(ValueError) → Result(status="handled_after_compensate").

    Порядок обработки:
    1. fail_aspect бросает ValueError.
    2. _rollback_saga(): rollback_reserve → rollback_charge (оба успешно).
    3. _handle_aspect_error(): @on_error(ValueError) → Result.

    @on_error receives ValueError with message "Finalize error for ...",
    а не какую-либо ошибку компенсатора.
    """

    @pytest.mark.anyio
    async def test_on_error_receives_original_error_after_compensate(
        self, compensate_bench,
    ) -> None:
        """
        @on_error получает оригинальную ValueError аспекта.
        Результат содержит status="handled_after_compensate" и detail
        с текстом исходной ошибки.
        """
        # ── Arrange ──
        params = CompensateTestParams(
            user_id="user_original",
            amount=300.0,
            item_id="ITEM-ORIG",
            should_fail=True,
        )

        # ── Act ──
        result = await compensate_bench.run(
            CompensateAndOnErrorAction(),
            params,
            rollup=False,
        )

        # ── Assert ──
        assert result.status == "handled_after_compensate"
        assert "Finalize error for user_original" in result.detail
        # State passed into fail_aspect includes prior regular aspects (charge, reserve).
        assert "TXN-TEST-001" in result.detail
        assert "RES-TEST-001" in result.detail

    @pytest.mark.anyio
    async def test_compensators_called_before_on_error(
        self, compensate_bench,
    ) -> None:
        """
        Компенсаторы вызываются ДО @on_error — проверка через моки.
        После run() оба мока (refund, unreserve) должны быть вызваны,
        а результат — сформирован @on_error.
        """
        # ── Arrange ──
        mock_payment = compensate_bench.mocks[PaymentService]
        mock_inventory = compensate_bench.mocks[InventoryService]

        params = CompensateTestParams(
            user_id="user_order",
            amount=400.0,
            item_id="ITEM-ORD",
            should_fail=True,
        )

        # ── Act ──
        result = await compensate_bench.run(
            CompensateAndOnErrorAction(),
            params,
            rollup=False,
        )

        # ── Assert ──
        # Компенсаторы были вызваны (размотка произошла).
        # Используем call_count вместо assert_awaited, потому что
        # TestBench.run() прогоняет sync-машину последней, и asyncio.run()
        # может регистрировать await-вызовы иначе.
        assert mock_payment.refund.call_count == 1
        assert mock_inventory.unreserve.call_count == 1
        # @on_error тоже отработал
        assert result.status == "handled_after_compensate"
        assert "TXN-TEST-001" in result.detail


# ═════════════════════════════════════════════════════════════════════════════
# TestOnErrorReceivesStateAfterRegularPipeline
# ═════════════════════════════════════════════════════════════════════════════


class TestOnErrorReceivesStateAfterRegularPipeline:
    """
    When the summary aspect fails after all regular aspects succeeded,
    ``@on_error`` must receive the ``BaseState`` passed into summary (full regular
    pipeline output).

    ``CompensateAndOnErrorAction`` fails inside a regular aspect: ``@on_error`` must
    receive the state **passed into that aspect** (including outputs of earlier
    regular aspects).
    """

    @pytest.mark.anyio
    async def test_on_error_sees_txn_and_order_after_summary_failure(
        self, compensate_bench,
    ) -> None:
        params = CompensateTestParams(
            user_id="user_state",
            amount=50.0,
            item_id="ITEM-ST",
            should_fail=False,
        )

        result = await compensate_bench.run(
            SummaryFailsOnErrorStateAction(),
            params,
            rollup=False,
        )

        assert result.status == "handled_summary_error"
        assert "TXN-TEST-001" in result.detail
        assert "ORD-user_state" in result.detail
        assert "summary failed" in result.detail


# ═════════════════════════════════════════════════════════════════════════════
# TestOnErrorPipelineStateAtFailureSite
# ═════════════════════════════════════════════════════════════════════════════


class TestOnErrorPipelineStateAtFailureSite:
    """
    ``@on_error`` получает ровно тот ``BaseState``, что был **входом** в упавший шаг:

    - первый regular упал → пустой state;
    - второй regular упал → state после первого аспекта (без полей следующих);
    - summary упал → state после всего regular (см. ``SummaryFailsOnErrorStateAction``).
    """

    @pytest.mark.anyio
    async def test_first_regular_failure_empty_state_for_on_error(
        self, compensate_bench,
    ) -> None:
        params = CompensateTestParams(
            user_id="u_first",
            amount=1.0,
            item_id="ITEM-1",
            should_fail=False,
        )
        result = await compensate_bench.run(
            FirstRegularFailsOnErrorAction(),
            params,
            rollup=False,
        )
        assert result.status == "handled_first_regular"
        assert "first_regular_failed" in result.detail
        assert "txn=None" in result.detail
        assert "res=None" in result.detail

    @pytest.mark.anyio
    async def test_second_regular_failure_state_includes_only_prior_aspect(
        self, compensate_bench,
    ) -> None:
        mock_payment = compensate_bench.mocks[PaymentService]

        params = CompensateTestParams(
            user_id="u_second",
            amount=77.0,
            item_id="ITEM-2",
            should_fail=False,
        )
        result = await compensate_bench.run(
            SecondRegularFailsOnErrorAction(),
            params,
            rollup=False,
        )

        assert result.status == "handled_second_regular"
        assert "second_regular_failed" in result.detail
        assert "TXN-TEST-001" in result.detail
        assert "res=None" in result.detail
        assert mock_payment.refund.call_count == 1
