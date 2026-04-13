# tests/scenarios/intents_with_runtime/test_saga_nested.py
"""Tests of nested calls and isolation of compensation stacks.
═══════════════════ ════════════════════ ════════════════════ ════════════════════
PURPOSE
═══════════════════ ════════════════════ ════════════════════ ════════════════════
Checks the architectural decision about local nested call stacks:

- Each _run_internal creates its own local stack. There is no global stack.
- The child Action (via box.run) unwinds ITS stack and forwards
  exception.
- If the parent aspect catches the child's error via try/except,
  for the parent, the aspect COMPLETED SUCCESSFULly - it is added to the parent's stack.
- If there is a subsequent error in the parent pipeline, the compensator for this
  aspect will be called.
═══════════════════ ════════════════════ ════════════════════ ════════════════════
STRUCTURE
═══════════════════ ════════════════════ ════════════════════ ════════════════════
TestNestedStacks - stack isolation, interaction with try/except"""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
from pydantic import Field

from action_machine.dependencies.depends_decorator import depends
from action_machine.intents.aspects.regular_aspect_decorator import regular_aspect
from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.auth import NoneRole, check_roles
from action_machine.intents.checkers import result_string
from action_machine.intents.compensate import compensate
from action_machine.intents.meta.meta_decorator import meta
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.model.base_state import BaseState
from action_machine.resources.base_resource_manager import BaseResourceManager
from action_machine.runtime.tools_box import ToolsBox
from action_machine.testing import TestBench
from tests.scenarios.domain_model.domains import TestDomain
from tests.scenarios.domain_model.services import InventoryService, PaymentService

# ═════════════════════════════════════════════════════════════════════════════
#Auxiliary Actions for nesting tests
# ═════════════════════════════════════════════════════════════════════════════


class NestedParams(BaseParams):
    """Options for nesting tests."""
    should_child_fail: bool = Field(
        default=False,
        description="If True, the child action will throw an exception",
    )
    should_parent_fail: bool = Field(
        default=False,
        description="If True, the parent action will throw an exception",
    )


class NestedResult(BaseResult):
    """Result for nesting tests."""
    status: str = Field(
        default="ok",
        description="Execution Status",
    )


@meta(description="Child activity that can fall", domain=TestDomain)
@check_roles(NoneRole)
@depends(InventoryService, description="Inventory service")
class FailableChildAction(BaseAction[NestedParams, NestedResult]):

    @regular_aspect("Reservation in child")
    @result_string("child_reservation_id", required=True)
    async def reserve_aspect(
        self, params, state, box, connections,
    ) -> dict[str, Any]:
        inventory = box.resolve(InventoryService)
        res_id = await inventory.reserve("CHILD-ITEM", 1)
        return {"child_reservation_id": res_id}

    @compensate("reserve_aspect", "Rolling back a reservation in a child")
    async def rollback_reserve_compensate(
        self, params, state_before, state_after, box, connections, error,
    ) -> None:
        if state_after is None:
            return
        inventory = box.resolve(InventoryService)
        await inventory.unreserve(state_after.child_reservation_id)

    @regular_aspect("Finalization of child")
    @result_string("child_final", required=True)
    async def finalize_child_aspect(
        self, params, state, box, connections,
    ) -> dict[str, Any]:
        if params.should_child_fail:
            raise ValueError("Child finalization error")
        return {"child_final": "done"}

    @summary_aspect("Formation of the result of the child")
    async def build_result_summary(
        self, params, state, box, connections,
    ) -> NestedResult:
        return NestedResult(status="child_ok")


@meta(description="Parent action calling child via box.run", domain=TestDomain)
@check_roles(NoneRole)
@depends(PaymentService, description="Payment service")
@depends(InventoryService, description="Inventory service")
class ParentWithNestedCallAction(BaseAction[NestedParams, NestedResult]):
    """A parent action with three regular aspects:
    1. charge_aspect — debiting funds (with compensator).
    2. call_child_aspect - calls FailableChildAction via box.run(),
       wraps in try/except. Has a compensator.
    3. finalize_aspect - when should_parent_fail=True throws a ValueError.
       Without compensator."""

    @regular_aspect("Write-off of funds in the parent")
    @result_string("parent_txn_id", required=True)
    async def charge_aspect(
        self,
        params: NestedParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        payment = box.resolve(PaymentService)
        txn_id = await payment.charge(100.0, "RUB")
        return {"parent_txn_id": txn_id}

    @compensate("charge_aspect", "Rollback payment in parent")
    async def rollback_charge_compensate(
        self,
        params: NestedParams,
        state_before: BaseState,
        state_after: BaseState | None,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        error: Exception,
    ) -> None:
        if state_after is None:
            return
        payment = box.resolve(PaymentService)
        await payment.refund(state_after.parent_txn_id)

    @regular_aspect("Calling a Child Action")
    @result_string("child_status", required=True)
    async def call_child_aspect(
        self,
        params: NestedParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        """Calls FailableChildAction via box.run().
        Wraps in try/except: if the child fails, returns
        fallback value. For the parent, the aspect ended SUCCESSFULLY."""
        try:
            child_result = await box.run_child(
                FailableChildAction(),
                params,
            )
            return {"child_status": child_result.status}
        except ValueError:
            return {"child_status": "child_failed_handled"}

    @compensate("call_child_aspect", "Rolling back a child call")
    async def rollback_call_child_compensate(
        self,
        params: NestedParams,
        state_before: BaseState,
        state_after: BaseState | None,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        error: Exception,
    ) -> None:
        """Compensator for call_child_aspect.
        We use unreserve as a marker for calling the compensator."""
        inventory = box.resolve(InventoryService)
        await inventory.unreserve("PARENT-CHILD-ROLLBACK")

    @regular_aspect("Finalization in parent")
    @result_string("parent_order_id", required=True)
    async def finalize_aspect(
        self,
        params: NestedParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        if params.should_parent_fail:
            raise ValueError("Error finalizing parent")
        return {"parent_order_id": "PARENT-ORD-001"}

    @summary_aspect("Formation of the result of the parent")
    async def build_result_summary(
        self,
        params: NestedParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> NestedResult:
        return NestedResult(status="parent_ok")


# ═════════════════════════════════════════════════════════════════════════════
# TestNestedStacks
# ═════════════════════════════════════════════════════════════════════════════


class TestNestedStacks:
    """Checks the isolation of compensation stacks for nested calls.

    Each _run_internal creates its own stack. The child unwinds his own,
    parent - yours. Stacks do not intersect."""

    @pytest.mark.anyio
    async def test_child_stack_isolated_from_parent(
        self,
        mock_payment: AsyncMock,
        mock_inventory: AsyncMock,
    ) -> None:
        """The child Action unwinds ITS stack upon error.
        The parent catches the error via try/except - for the parent
        aspect completed successfully. The parent's stack is not affected."""
        # ── Arrange ──
        bench = TestBench(
            mocks={
                PaymentService: mock_payment,
                InventoryService: mock_inventory,
            },
            log_coordinator=AsyncMock(),
        )

        params = NestedParams(
            should_child_fail=True,
            should_parent_fail=False,
        )

        # ── Act ──
        result = await bench.run(
            ParentWithNestedCallAction(),
            params,
            rollup=False,
        )

        # ── Assert ──
        assert result.status == "parent_ok"

        #The child compensator called unreserve (the child stack is unwinded).
        #The parent compensator is NOT called (the parent did not fall).
        #We use call_count - TestBench.run() runs two cars.
        assert mock_inventory.unreserve.call_count >= 1
        assert mock_payment.refund.call_count == 0

    @pytest.mark.anyio
    async def test_parent_compensates_after_child_caught(
        self,
        mock_payment: AsyncMock,
        mock_inventory: AsyncMock,
    ) -> None:
        """If the child action fell and the parent took over, then
        PARENT fell - parent compensators are called for everyone
        successful aspects, including the one that caught the child's error."""
        # ── Arrange ──
        bench = TestBench(
            mocks={
                PaymentService: mock_payment,
                InventoryService: mock_inventory,
            },
            log_coordinator=AsyncMock(),
        )

        params = NestedParams(
            should_child_fail=True,
            should_parent_fail=True,
        )

        # ── Act ──
        with pytest.raises(ValueError, match="Error finalizing parent"):
            await bench.run(
                ParentWithNestedCallAction(),
                params,
                rollup=False,
            )

        # ── Assert ──
        #unreserve is called at least twice (from each machine run):
        #1. Child: unreserve("RES-TEST-001") - unwinding the child stack.
        #2. Parent: unreserve("PARENT-CHILD-ROLLBACK") - unwinding the parent.
        #With two runs - doubling.
        unreserve_args = [c[0][0] for c in mock_inventory.unreserve.call_args_list]
        assert "PARENT-CHILD-ROLLBACK" in unreserve_args

        #refund called - parent compensator charge_aspect
        assert mock_payment.refund.call_count >= 1
        assert mock_payment.refund.call_count >= 1
