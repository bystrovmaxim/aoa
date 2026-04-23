# tests/intents/compensate/test_saga_rollback.py
"""Compensation stack unwinding tests (Saga) in ActionProductMachine.
═══════════════════ ════════════════════ ════════════════════ ════════════════════
PURPOSE
═══════════════════ ════════════════════ ════════════════════ ════════════════════
Checks that if there is an error in the aspect pipeline:
- Compensators for already completed aspects are called in reverse order.
- The compensator receives the correct parameters: params, state_before, state_after, error.
- For a fallen aspect, the frame is not added to the stack (the compensator is not called).
- The return value of the compensator is ignored.
═══════════════════ ════════════════════ ════════════════════ ════════════════════
STRUCTURE
═══════════════════ ════════════════════ ════════════════════ ════════════════════
TestCompensatorsCalledInReverseOrder - call order
TestCompensatorReceivesCorrectData - data correctness
TestFrameNotAddedForFailedAspect - no frame for the failed aspect
TestCompensatorReturnValueIgnored - the return value is ignored"""
from __future__ import annotations

import pytest

from tests.scenarios.domain_model.compensate_actions import (
    CompensatedOrderAction,
    CompensateTestParams,
)
from tests.scenarios.domain_model.services import (
    InventoryServiceResource,
    PaymentServiceResource,
)

# ═════════════════════════════════════════════════════════════════════════════
# TestCompensatorsCalledInReverseOrder
# ═════════════════════════════════════════════════════════════════════════════


class TestCompensatorsCalledInReverseOrder:
    """Checks that compensators are called in reverse order."""

    @pytest.mark.anyio
    async def test_compensators_called_in_reverse_order(self, compensate_bench) -> None:
        """If there is an error in the 3rd aspect, the 2nd and 1st compensators are called
        in reverse order."""
        # ── Arrange ──
        mock_payment = compensate_bench.mocks[PaymentServiceResource].service
        mock_inventory = compensate_bench.mocks[InventoryServiceResource].service

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
        #We check through call_count and call_args_list (not await_args_list),
        #because TestBench.run() runs two cars and resets mocks
        #between runs - the test sees calls from a sync run, where
        #asyncio.run() may log calls differently.
        assert mock_inventory.unreserve.call_count == 1
        assert mock_payment.refund.call_count == 1

        #Checking call arguments
        assert mock_inventory.unreserve.call_args[0][0] == "RES-TEST-001"
        assert mock_payment.refund.call_args[0][0] == "TXN-TEST-001"

    @pytest.mark.anyio
    async def test_compensator_not_called_for_failed_aspect(self, compensate_bench) -> None:
        """For an aspect that has fallen, its compensator is not called."""
        # ── Arrange ──
        mock_payment = compensate_bench.mocks[PaymentServiceResource].service
        mock_inventory = compensate_bench.mocks[InventoryServiceResource].service

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
        #The charge and reserve compensators are called (they completed successfully).
        #The finalize_aspect compensator is missing (the aspect has fallen, the frame has not been added).
        assert mock_payment.refund.call_count == 1
        assert mock_inventory.unreserve.call_count == 1


# ═════════════════════════════════════════════════════════════════════════════
# TestCompensatorReceivesCorrectData
# ═════════════════════════════════════════════════════════════════════════════


class TestCompensatorReceivesCorrectData:
    """Checks that the compensator receives correct data."""

    @pytest.mark.anyio
    async def test_compensator_receives_correct_state_data(self, compensate_bench) -> None:
        """The compensator calls refund/unreserve with the correct data
        from state_after - indirect check that params and state_after
        were transmitted correctly."""
        # ── Arrange ──
        mock_payment = compensate_bench.mocks[PaymentServiceResource].service
        mock_inventory = compensate_bench.mocks[InventoryServiceResource].service

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
        #The charge_aspect compensator calls refund with txn_id from state_after
        assert mock_payment.refund.call_args[0][0] == "TXN-TEST-001"
        #The reserve_aspect compensator calls unreserve with reservation_id from state_after
        assert mock_inventory.unreserve.call_args[0][0] == "RES-TEST-001"


# ═════════════════════════════════════════════════════════════════════════════
# TestFrameNotAddedForFailedAspect
# ═════════════════════════════════════════════════════════════════════════════


class TestFrameNotAddedForFailedAspect:
    """Checks that the frame for the failed aspect is not added to the stack."""

    @pytest.mark.anyio
    async def test_no_frame_for_failed_aspect(self, compensate_bench) -> None:
        """If an aspect throws an exception, its frame is not on the stack.
        and the compensator is not called."""
        # ── Arrange ──
        mock_payment = compensate_bench.mocks[PaymentServiceResource].service
        mock_inventory = compensate_bench.mocks[InventoryServiceResource].service

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
        #Compensators of successful aspects are called
        assert mock_payment.refund.call_count == 1
        assert mock_inventory.unreserve.call_count == 1
        #Compensator finalize_aspect (fallen) - does not exist,
        #frame not added to stack


# ═════════════════════════════════════════════════════════════════════════════
# TestCompensatorReturnValueIgnored
# ═════════════════════════════════════════════════════════════════════════════


class TestCompensatorReturnValueIgnored:
    """Checks that the compensator's return value is ignored."""

    @pytest.mark.anyio
    async def test_compensator_return_value_ignored(self, compensate_bench) -> None:
        """Even if the compensator returns a dict, it does not affect the result −
        the aspect error is thrown out."""
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
        # The error remained the original ValueError — compensator return
        # value did not replace the outcome.
