# tests/scenarios/intents_with_runtime/test_bench_run_compensator.py
"""Tests of the TestBench.run_compensator() method - isolated launch of compensators.
═══════════════════ ════════════════════ ════════════════════ ════════════════════
PURPOSE
═══════════════════ ════════════════════ ════════════════════ ════════════════════
Checks that TestBench.run_compensator() allows testing
compensators as unit - without running the full pipeline of aspects
and without unwinding the stack.

Key difference from production: run_compensator() DOES NOT SUPPRESS
exceptions. In production, _rollback_saga() suppresses errors
compensators. In tests, errors are FORWARDED - this allows
test edge cases.
═══════════════════ ════════════════════ ════════════════════ ════════════════════
STRUCTURE
═══════════════════ ════════════════════ ════════════════════ ════════════════════
TestRunCompensatorBasic - basic launch and side effects checking
TestRunCompensatorValidation - validations: non-existent method, non-compensator,
                                lack of context
TestRunCompensatorContext - integration with @context_requires"""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
from pydantic import Field

from action_machine.intents.aspects.regular_aspect_decorator import regular_aspect
from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.check_roles import NoneRole, check_roles
from action_machine.intents.checkers import result_string
from action_machine.intents.compensate import compensate
from action_machine.intents.context import Ctx, context_requires
from action_machine.intents.depends import depends
from action_machine.intents.meta.meta_decorator import meta
from action_machine.legacy.core import Core
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.model.base_state import BaseState
from action_machine.testing import StubTesterRole, TestBench
from tests.scenarios.domain_model.compensate_actions import (
    CompensatedOrderAction,
    CompensateTestParams,
    CompensateWithContextAction,
)
from tests.scenarios.domain_model.domains import TestDomain
from tests.scenarios.domain_model.services import (
    InventoryServiceResource,
    PaymentService,
    PaymentServiceResource,
    default_payment_service_resource,
)

# ═════════════════════════════════════════════════════════════════════════════
#Helper function to create a BaseState with data
# ═════════════════════════════════════════════════════════════════════════════


def make_state(**kwargs: Any) -> BaseState:
    """Creates a BaseState with custom fields.
    BaseState inherits Pydantic BaseModel and does not accept a positional dict.
    We use model_construct() to create an instance with arbitrary
    data without validation - similar to how a machine creates state
    from the results of the aspects."""
    state = BaseState.model_construct()
    for key, value in kwargs.items():
        state.__dict__[key] = value
    return state


# ═════════════════════════════════════════════════════════════════════════════
#Auxiliary Action for context test in compensator
# ═════════════════════════════════════════════════════════════════════════════


class CtxCheckParams(BaseParams):
    """Parameters for Action checking context."""
    amount: float = Field(default=1.0, description="Amount for test compensator")


class CtxCheckResult(BaseResult):
    """Result for Action checking context."""
    status: str = Field(default="ok", description="Execution Status")


@meta(description="Action to check the context in the compensator", domain=TestDomain)
@check_roles(NoneRole)
@depends(
    PaymentServiceResource,
    factory=default_payment_service_resource,
    description="Payments",
)
class CtxCheckAction(BaseAction[CtxCheckParams, CtxCheckResult]):
    """Action whose compensator uses ctx.get(Ctx.User.user_id)
    and passes user_id to the refund argument to check that
    The ContextView is created with the correct values."""

    @regular_aspect("Aspect")
    @result_string("txn_id", required=True)
    async def charge_aspect(self, params, state, box, connections):
        return {"txn_id": "TXN-001"}

    @compensate("charge_aspect", "Rollback with context")
    @context_requires(Ctx.User.user_id)
    async def rollback_compensate(
        self, params, state_before, state_after, box, connections, error, ctx,
    ):
        user_id = ctx.get(Ctx.User.user_id)
        payment = box.resolve(PaymentServiceResource).service
        await payment.refund(f"refund_for_{user_id}")

    @summary_aspect("Summary")
    async def summary(self, params, state, box, connections):
        return CtxCheckResult()


# ═════════════════════════════════════════════════════════════════════════════
#TestRunCompensatorBasic - basic run
# ═════════════════════════════════════════════════════════════════════════════


class TestRunCompensatorBasic:
    """Checks the basic compensator startup via run_compensator():
    side effects via mocks, error forwarding, state_after=None."""

    @pytest.mark.anyio
    async def test_compensator_calls_refund_via_mock(
        self,
        mock_payment: AsyncMock,
        mock_inventory: AsyncMock,
    ) -> None:
        """Isolated compensator start - side effect check
        via mok. refund() is called with txn_id from state_after."""
        # ── Arrange ──
        mock_payment.refund.reset_mock()

        bench = TestBench(
            coordinator=Core.create_coordinator(),
            mocks={
                PaymentServiceResource: PaymentServiceResource(mock_payment),
                InventoryServiceResource: InventoryServiceResource(mock_inventory),
            },
            log_coordinator=AsyncMock(),
        )

        params = CompensateTestParams(
            user_id="user_unit",
            amount=100.0,
            item_id="ITEM-U01",
        )
        state_before = BaseState()
        state_after = make_state(txn_id="TXN-UNIT-001")
        error = ValueError("Test error")

        # ── Act ──
        await bench.run_compensator(
            action=CompensatedOrderAction(),
            compensator_name="rollback_charge_compensate",
            params=params,
            state_before=state_before,
            state_after=state_after,
            error=error,
        )

        # ── Assert ──
        mock_payment.refund.assert_awaited_once_with("TXN-UNIT-001")

    @pytest.mark.anyio
    async def test_compensator_error_propagated_in_test(
        self,
        mock_payment: AsyncMock,
        mock_inventory: AsyncMock,
    ) -> None:
        """Unlike production, run_compensator() does NOT suppress errors.
        If the compensator throws, the exception is thrown."""
        # ── Arrange ──
        mock_payment.refund.side_effect = RuntimeError("Gateway unavailable")

        bench = TestBench(
            coordinator=Core.create_coordinator(),
            mocks={
                PaymentServiceResource: PaymentServiceResource(mock_payment),
                InventoryServiceResource: InventoryServiceResource(mock_inventory),
            },
            log_coordinator=AsyncMock(),
        )

        params = CompensateTestParams(
            user_id="user_err",
            amount=100.0,
        )
        state_before = BaseState()
        state_after = make_state(txn_id="TXN-ERR-001")
        error = ValueError("Original error")

        # ── Act & Assert ──
        with pytest.raises(RuntimeError, match="Gateway unavailable"):
            await bench.run_compensator(
                action=CompensatedOrderAction(),
                compensator_name="rollback_charge_compensate",
                params=params,
                state_before=state_before,
                state_after=state_after,
                error=error,
            )

    @pytest.mark.anyio
    async def test_compensator_with_state_after_none(
        self,
        mock_payment: AsyncMock,
        mock_inventory: AsyncMock,
    ) -> None:
        """When state_after=None (the checker rejected the aspect result),
        the compensator receives None and may decide not to rollback.
        CompensatedOrderAction.rollback_charge_compensate skips
        refund() when state_after=None."""
        # ── Arrange ──
        mock_payment.refund.reset_mock()

        bench = TestBench(
            coordinator=Core.create_coordinator(),
            mocks={
                PaymentServiceResource: PaymentServiceResource(mock_payment),
                InventoryServiceResource: InventoryServiceResource(mock_inventory),
            },
            log_coordinator=AsyncMock(),
        )

        params = CompensateTestParams(
            user_id="user_none",
            amount=100.0,
        )
        state_before = BaseState()
        error = ValueError("Checker rejected")

        # ── Act ──
        await bench.run_compensator(
            action=CompensatedOrderAction(),
            compensator_name="rollback_charge_compensate",
            params=params,
            state_before=state_before,
            state_after=None,
            error=error,
        )

        # ── Assert ──
        mock_payment.refund.assert_not_awaited()


# ═════════════════════════════════════════════════════════════════════════════
#TestRunCompensatorValidation - validations
# ═════════════════════════════════════════════════════════════════════════════


class TestRunCompensatorValidation:
    """Checks the validations of run_compensator(): non-existent method,
    method without @compensate, no context for @context_requires."""

    @pytest.mark.anyio
    async def test_nonexistent_method_raises_value_error(self) -> None:
        """Non-existent method → ​​ValueError with a clear message."""
        # ── Arrange ──
        bench = TestBench(
            coordinator=Core.create_coordinator(),
            log_coordinator=AsyncMock(),
        )

        params = CompensateTestParams(user_id="u", amount=1.0)
        state_before = BaseState()
        error = ValueError("test")

        # ── Act & Assert ──
        with pytest.raises(ValueError, match="not found"):
            await bench.run_compensator(
                action=CompensatedOrderAction(),
                compensator_name="nonexistent_method",
                params=params,
                state_before=state_before,
                state_after=None,
                error=error,
            )

    @pytest.mark.anyio
    async def test_non_compensator_method_raises_value_error(self) -> None:
        """Method without @compensate decorator → ValueError.
        charge_aspect is a regular aspect, not a compensator."""
        # ── Arrange ──
        bench = TestBench(
            coordinator=Core.create_coordinator(),
            log_coordinator=AsyncMock(),
        )

        params = CompensateTestParams(user_id="u", amount=1.0)
        state_before = BaseState()
        error = ValueError("test")

        # ── Act & Assert ──
        #bench.run_compensator checks for the presence of _compensate_meta.
        #If a method is found, but is not a compensator -
        #The message may be "not a compensator" or "not found".
        with pytest.raises(ValueError):
            await bench.run_compensator(
                action=CompensatedOrderAction(),
                compensator_name="charge_aspect",
                params=params,
                state_before=state_before,
                state_after=None,
                error=error,
            )

    @pytest.mark.anyio
    async def test_context_requires_without_context_raises_value_error(self) -> None:
        """Compensator with @context_requires, but context not passed → ValueError.
        CompensateWithContextAction.rollback_charge_compensate requires
        Ctx.User.user_id - launch is impossible without context."""
        # ── Arrange ──
        mock_payment = AsyncMock(spec=PaymentService)
        bench = TestBench(
            coordinator=Core.create_coordinator(),
            mocks={PaymentServiceResource: PaymentServiceResource(mock_payment)},
            log_coordinator=AsyncMock(),
        )

        params = CompensateTestParams(user_id="u", amount=1.0)
        state_before = BaseState()
        state_after = make_state(txn_id="TXN-001")
        error = ValueError("test")

        # ── Act & Assert ──
        with pytest.raises(ValueError, match="context"):
            await bench.run_compensator(
                action=CompensateWithContextAction(),
                compensator_name="rollback_charge_compensate",
                params=params,
                state_before=state_before,
                state_after=state_after,
                error=error,
            )


# ═════════════════════════════════════════════════════════════════════════════
#TestRunCompensatorContext - integration with @context_requires
# ═════════════════════════════════════════════════════════════════════════════


class TestRunCompensatorContext:
    """Verifies that run_compensator() correctly creates the ContextView
    and passes it to the compensator with @context_requires."""

    @pytest.mark.anyio
    async def test_context_view_created_with_correct_keys(self) -> None:
        """ContextView is created with keys from @context_requires.
        ctx.get(Ctx.User.user_id) returns the value from the passed context."""
        # ── Arrange ──
        mock_payment = AsyncMock(spec=PaymentService)
        mock_payment.refund.reset_mock()

        bench = TestBench(
            coordinator=Core.create_coordinator(),
            mocks={PaymentServiceResource: PaymentServiceResource(mock_payment)},
            log_coordinator=AsyncMock(),
        ).with_user(user_id="ctx_user_99", roles=(StubTesterRole,))

        params = CompensateTestParams(
            user_id="ctx_user_99",
            amount=100.0,
        )
        state_before = BaseState()
        state_after = make_state(txn_id="TXN-CTX-001")
        error = ValueError("Test error")

        # ── Act ──
        await bench.run_compensator(
            action=CompensateWithContextAction(),
            compensator_name="rollback_charge_compensate",
            params=params,
            state_before=state_before,
            state_after=state_after,
            error=error,
            context={"user.user_id": "ctx_user_99"},
        )

        # ── Assert ──
        mock_payment.refund.assert_awaited_once_with("TXN-CTX-001")

    @pytest.mark.anyio
    async def test_context_values_accessible_in_compensator(self) -> None:
        """Compensator with @context_requires gets ctx with correct
        values. CtxCheckAction.rollback_compensate writes
        user_id from the context to the refund argument for verification."""
        # ── Arrange ──
        mock_payment = AsyncMock(spec=PaymentService)
        mock_payment.refund.reset_mock()

        #with_user() sets the user_id in the machine context.
        #run_compensator() uses this context to create
        #ContextView, not the context= argument.
        bench = TestBench(
            coordinator=Core.create_coordinator(),
            mocks={PaymentServiceResource: PaymentServiceResource(mock_payment)},
            log_coordinator=AsyncMock(),
        ).with_user(user_id="verified_user_42", roles=(StubTesterRole,))

        # ── Act ──
        await bench.run_compensator(
            action=CtxCheckAction(),
            compensator_name="rollback_compensate",
            params=CtxCheckParams(),
            state_before=BaseState(),
            state_after=make_state(txn_id="TXN-001"),
            error=ValueError("test"),
            context={"user.user_id": "verified_user_42"},
        )

        # ── Assert ──
        #refund called with user_id from context
        mock_payment.refund.assert_awaited_once_with("refund_for_verified_user_42")
        mock_payment.refund.assert_awaited_once_with("refund_for_verified_user_42")
