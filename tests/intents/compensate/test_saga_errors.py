# tests/intents/compensate/test_saga_errors.py
"""Tests of silent error suppression of compensators.
═══════════════════ ════════════════════ ════════════════════ ════════════════════
PURPOSE
═══════════════════ ════════════════════ ════════════════════ ════════════════════
Checks that compensator errors:
- Do not interrupt stack unwinding - all subsequent compensators are called.
- Do not forward outside - @on_error receives the ORIGINAL aspect error.
- Do not replace the original error - the calling code sees the ValueError of the aspect,
  rather than a RuntimeError compensator.

Architectural solution: compensator errors are completely suppressed internally
_rollback_saga(). Instead of forwarding, a typed event is used
CompensateFailedEvent that the monitoring plugin can subscribe to.
═══════════════════ ════════════════════ ════════════════════ ════════════════════
STRUCTURE
═══════════════════ ════════════════════ ════════════════════ ════════════════════
TestCompensatorErrorSuppressed - compensator error is suppressed
TestAllCompensatorsCalled - all compensators get a chance to be executed
TestOnErrorReceivesOriginalError — @on_error receives the original error
TestOnErrorReceivesStateAfterRegularPipeline - after regular in state for @on_error
TestOnErrorPipelineStateAtFailureSite - empty state / first aspect only / summary"""
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
    """Checks that the compensator error is suppressed and does not interrupt unwinding.

    CompensateErrorAction has two compensators:
    - rollback_charge_compensate - THROWS a RuntimeError.
    - rollback_reserve_compensate - works fine.

    If there is an error in fail_aspect (ValueError), unwinding proceeds in the reverse order:
    1. rollback_reserve_compensate → success.
    2. rollback_charge_compensate → RuntimeError → SUPPRESSED.

    The ORIGINAL ValueError of the aspect is thrown outside, not the RuntimeError
    compensator."""

    @pytest.mark.anyio
    async def test_compensator_error_suppressed_original_error_propagated(
        self, compensate_bench,
    ) -> None:
        """The compensator error is suppressed - the original
        ValueError of the aspect, not the RuntimeError of the compensator."""
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
    """Checks that if the first compensator (in the unwinding order) has fallen,
    the second one is still called.

    Unwinding order for CompensateErrorAction:
    1. rollback_reserve_compensate (last successful → first in unrolling).
    2. rollback_charge_compensate (first successful → second in unwinding).

    rollback_charge_compensate throws RuntimeError, but rollback_reserve_compensate
    already called before it. We check that BOTH have a chance to be executed."""

    @pytest.mark.anyio
    async def test_all_compensators_called_despite_error(
        self, compensate_bench,
    ) -> None:
        """Both compensators are called: unreserve() successfully, then
        rollback_charge_compensate throws RuntimeError - but unreserve()
        has already been called and the unwinding is completed."""
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
        #unreserve() is called - the reserve_aspect compensator is executed
        #despite the fact that the charge_aspect compensator threw a RuntimeError.
        #We use call_count instead of assert_awaited because
        #TestBench.run() runs two machines with _reset_all_mocks() in between.
        assert mock_inventory.unreserve.call_count == 1
        assert mock_inventory.unreserve.call_args[0][0] == "RES-TEST-001"


# ═════════════════════════════════════════════════════════════════════════════
# TestOnErrorReceivesOriginalError
# ═════════════════════════════════════════════════════════════════════════════


class TestOnErrorReceivesOriginalError:
    """Checks that @on_error receives the ORIGINAL aspect error,
    and not a compensator error.

    CompensateAndOnErrorAction has:
    - Two compensators (both work fine).
    - @on_error(ValueError) → Result(status="handled_after_compensate").

    Processing order:
    1. fail_aspect throws ValueError.
    2. _rollback_saga(): rollback_reserve → rollback_charge (both successful).
    3. _handle_aspect_error(): @on_error(ValueError) → Result.

    @on_error receives ValueError with message "Finalize error for ...",
    and not any compensator error."""

    @pytest.mark.anyio
    async def test_on_error_receives_original_error_after_compensate(
        self, compensate_bench,
    ) -> None:
        """@on_error gets the original ValueError of the aspect.
        The result contains status="handled_after_compensate" and detail
        with the text of the original error."""
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
        """Compensators are called BEFORE @on_error - check via mocks.
        After run() both mocks (refund, unreserve) must be called,
        and the result is formed by @on_error."""
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
        #The compensators have been called (unwinding has occurred).
        #We use call_count instead of assert_awaited because
        #TestBench.run() runs the sync machine last, and asyncio.run()
        #may register await calls differently.
        assert mock_payment.refund.call_count == 1
        assert mock_inventory.unreserve.call_count == 1
        #@on_error worked too
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
    """``@on_error`` gets exactly the ``BaseState`` that was the **input** to the failed step:

    - the first regular fell → empty state;
    - the second regular fell → state after the first aspect (without the following fields);
    - summary fell → state after all regular (see ``SummaryFailsOnErrorStateAction``)."""

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
        assert mock_payment.refund.call_count == 1
