# tests/scenarios/domain_model/compensate_actions.py
"""
Actions with @compensate handlers for Saga tests.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

These Actions cover Saga rollback behavior: reverse-order compensation,
skipped frames, compensator-error suppression, interaction with `@on_error`,
and context-aware compensators.

═══════════════════════════════════════════════════════════════════════════════
SCENARIOS
═══════════════════════════════════════════════════════════════════════════════

- `CompensatedOrderAction` — baseline rollback.
- `PartialCompensateAction` — skipped frames without compensators.
- `CompensateErrorAction` — compensator raises but rollback continues.
- `CompensateAndOnErrorAction` — rollback before `@on_error`.
- `FirstRegularFailsOnErrorAction` — first regular fails; `@on_error` and empty state.
- `SecondRegularFailsOnErrorAction` — second regular fails; state only from the first step.
- `SummaryFailsOnErrorStateAction` — summary fails after regular; `@on_error` sees state.
- `CompensateWithContextAction` — `@context_requires` in compensator.
- `CheckerRejectionSagaAction` — second regular aspect fails checkers after
  `call()`; both compensators run (second first, `state_after=None` on second).

═══════════════════════════════════════════════════════════════════════════════
LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

This module is test-only and optimized for deterministic assertions, not
production-side domain modeling.
"""

from typing import Any

from pydantic import Field

from action_machine.intents.depends import depends
from action_machine.intents.aspects.regular_aspect_decorator import regular_aspect
from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.check_roles import NoneRole, check_roles
from action_machine.intents.checkers import result_string
from action_machine.intents.compensate import compensate
from action_machine.intents.context import Ctx, context_requires
from action_machine.intents.meta.meta_decorator import meta
from action_machine.intents.on_error import on_error
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.model.base_state import BaseState
from action_machine.resources.base_resource_manager import BaseResourceManager
from action_machine.runtime.tools_box import ToolsBox

from .domains import OrdersDomain
from .services import InventoryService, PaymentService, SagaCompensateTraceService

# ═════════════════════════════════════════════════════════════════════════════
# Shared Params / Result for compensating Actions
# ═════════════════════════════════════════════════════════════════════════════


class CompensateTestParams(BaseParams):
    """Parameters for compensating test Actions."""

    user_id: str = Field(description="User identifier")
    amount: float = Field(description="Order amount", gt=0)
    item_id: str = Field(default="ITEM-001", description="Product identifier")
    should_fail: bool = Field(
        default=False,
        description="If True, the final aspect raises an exception",
    )


class CompensateTestResult(BaseResult):
    """Result type for compensating test Actions."""

    status: str = Field(description="Execution status")
    detail: str = Field(default="", description="Result details")


# ═════════════════════════════════════════════════════════════════════════════
# CompensatedOrderAction — baseline Action with two compensators
# ═════════════════════════════════════════════════════════════════════════════


@meta(
    description="Order with two compensatable steps: payment and reservation",
    domain=OrdersDomain,
)
@check_roles(NoneRole)
@depends(PaymentService, description="Payment processing service")
@depends(InventoryService, description="Inventory service")
class CompensatedOrderAction(
    BaseAction[CompensateTestParams, CompensateTestResult],
):
    """
    Action with two regular aspects, both with compensators.

    Pipeline:
    1. charge_aspect (regular) — charges via PaymentService.
       Compensator: rollback_charge_compensate — calls refund().
    2. reserve_aspect (regular) — reserves stock via InventoryService.
       Compensator: rollback_reserve_compensate — calls unreserve().
    3. finalize_aspect (regular) — if should_fail=True, raises ValueError.
       No compensator.
    4. build_result_summary (summary) — builds Result.

    Test scenarios:
    - should_fail=False → normal Result(status="ok").
    - should_fail=True → ValueError in finalize_aspect →
      rollback_reserve_compensate (2nd) → rollback_charge_compensate (1st) →
      error propagates (no @on_error).
    """

    @regular_aspect("Charge payment")
    @result_string("txn_id", required=True, min_length=1)
    async def charge_aspect(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        """Charge funds via PaymentService."""
        payment = box.resolve(PaymentService)
        txn_id = await payment.charge(params.amount, "RUB")
        return {"txn_id": txn_id}

    @compensate("charge_aspect", "Rollback payment — refund")
    async def rollback_charge_compensate(
        self,
        params: CompensateTestParams,
        state_before: BaseState,
        state_after: BaseState | None,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        error: Exception,
    ) -> None:
        """
        Compensator for charge_aspect.

        Calls refund() on PaymentService with txn_id from state_after.
        If state_after is None (checker rejected) — skip rollback.
        """
        if state_after is None:
            return
        payment = box.resolve(PaymentService)
        await payment.refund(state_after["txn_id"])

    @regular_aspect("Reserve inventory")
    @result_string("reservation_id", required=True, min_length=1)
    async def reserve_aspect(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        """Reserve stock via InventoryService."""
        inventory = box.resolve(InventoryService)
        reservation_id = await inventory.reserve(params.item_id, 1)
        return {"reservation_id": reservation_id}

    @compensate("reserve_aspect", "Rollback reservation — release stock")
    async def rollback_reserve_compensate(
        self,
        params: CompensateTestParams,
        state_before: BaseState,
        state_after: BaseState | None,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        error: Exception,
    ) -> None:
        """
        Compensator for reserve_aspect.

        Calls unreserve() on InventoryService with reservation_id from
        state_after. If state_after is None — skip.
        """
        if state_after is None:
            return
        inventory = box.resolve(InventoryService)
        await inventory.unreserve(state_after["reservation_id"])

    @regular_aspect("Finalize order")
    @result_string("order_id", required=True)
    async def finalize_aspect(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        """Finalize order. When should_fail=True — raises ValueError."""
        if params.should_fail:
            raise ValueError(f"Finalize error for {params.user_id}")
        return {"order_id": f"ORD-{params.user_id}"}

    @summary_aspect("Build order result")
    async def build_result_summary(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> CompensateTestResult:
        """Build final Result from state."""
        return CompensateTestResult(
            status="ok",
            detail=f"order={state['order_id']}, txn={state['txn_id']}",
        )


# ═════════════════════════════════════════════════════════════════════════════
# PartialCompensateAction — compensator only on the first aspect
# ═════════════════════════════════════════════════════════════════════════════


@meta(
    description="Action with partial compensation — first aspect only",
    domain=OrdersDomain,
)
@check_roles(NoneRole)
@depends(PaymentService, description="Payment processing service")
class PartialCompensateAction(
    BaseAction[CompensateTestParams, CompensateTestResult],
):
    """
    Action with three regular aspects; only the first has a compensator.

    Exercises skipped frames: the second and third aspects have no compensator —
    their frames are skipped (skipped counter in SagaRollbackCompletedEvent).

    Pipeline:
    1. charge_aspect (regular, with compensator).
    2. log_aspect (regular, NO compensator).
    3. fail_aspect (regular, NO compensator) — raises ValueError.
    4. build_result_summary (summary).
    """

    @regular_aspect("Charge payment")
    @result_string("txn_id", required=True)
    async def charge_aspect(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        payment = box.resolve(PaymentService)
        txn_id = await payment.charge(params.amount, "RUB")
        return {"txn_id": txn_id}

    @compensate("charge_aspect", "Rollback payment")
    async def rollback_charge_compensate(
        self,
        params: CompensateTestParams,
        state_before: BaseState,
        state_after: BaseState | None,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        error: Exception,
    ) -> None:
        if state_after is None:
            return
        payment = box.resolve(PaymentService)
        await payment.refund(state_after["txn_id"])

    @regular_aspect("Log operation")
    @result_string("log_entry", required=True)
    async def log_aspect(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        """Log the operation. No compensator — log is not rolled back."""
        return {"log_entry": f"charged:{state['txn_id']}"}

    @regular_aspect("Failing aspect")
    @result_string("final_note", required=True)
    async def fail_aspect(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        """Always raises ValueError to drive unwind."""
        raise ValueError("Intentional failure for rollback test")

    @summary_aspect("Build result")
    async def build_result_summary(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> CompensateTestResult:
        return CompensateTestResult(status="ok")


# ═════════════════════════════════════════════════════════════════════════════
# CompensateErrorAction — compensator raises
# ═════════════════════════════════════════════════════════════════════════════


@meta(
    description="Action whose compensator raises an exception",
    domain=OrdersDomain,
)
@check_roles(NoneRole)
@depends(PaymentService, description="Payment processing service")
@depends(InventoryService, description="Inventory service")
class CompensateErrorAction(
    BaseAction[CompensateTestParams, CompensateTestResult],
):
    """
    Action whose first compensator raises RuntimeError.

    Exercises silent compensator error suppression:
    - rollback_charge_compensate raises RuntimeError.
    - Unwind CONTINUES — rollback_reserve_compensate still runs.
    - Compensator failure is visible via CompensateFailedEvent.
    - Original aspect error (ValueError) still propagates outward.

    Pipeline:
    1. charge_aspect (compensator raises RuntimeError).
    2. reserve_aspect (compensator succeeds).
    3. fail_aspect — raises ValueError.
    4. build_result_summary.
    """

    @regular_aspect("Charge payment")
    @result_string("txn_id", required=True)
    async def charge_aspect(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        payment = box.resolve(PaymentService)
        txn_id = await payment.charge(params.amount, "RUB")
        return {"txn_id": txn_id}

    @compensate("charge_aspect", "Rollback payment — raises error")
    async def rollback_charge_compensate(
        self,
        params: CompensateTestParams,
        state_before: BaseState,
        state_after: BaseState | None,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        error: Exception,
    ) -> None:
        """Compensator that intentionally raises RuntimeError."""
        raise RuntimeError("Payment gateway unavailable during compensating rollback")

    @regular_aspect("Reserve inventory")
    @result_string("reservation_id", required=True)
    async def reserve_aspect(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        inventory = box.resolve(InventoryService)
        reservation_id = await inventory.reserve(params.item_id, 1)
        return {"reservation_id": reservation_id}

    @compensate("reserve_aspect", "Rollback reservation — succeeds")
    async def rollback_reserve_compensate(
        self,
        params: CompensateTestParams,
        state_before: BaseState,
        state_after: BaseState | None,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        error: Exception,
    ) -> None:
        """Compensator that succeeds (does not raise)."""
        if state_after is None:
            return
        inventory = box.resolve(InventoryService)
        await inventory.unreserve(state_after["reservation_id"])

    @regular_aspect("Finalize with error")
    @result_string("order_id", required=True)
    async def fail_aspect(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        raise ValueError("Finalize error")

    @summary_aspect("Build result")
    async def build_result_summary(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> CompensateTestResult:
        return CompensateTestResult(status="ok")


# ═════════════════════════════════════════════════════════════════════════════
# CompensateAndOnErrorAction — compensators + @on_error
# ═════════════════════════════════════════════════════════════════════════════


@meta(
    description="Action with compensators and an @on_error handler",
    domain=OrdersDomain,
)
@check_roles(NoneRole)
@depends(PaymentService, description="Payment processing service")
@depends(InventoryService, description="Inventory service")
class CompensateAndOnErrorAction(
    BaseAction[CompensateTestParams, CompensateTestResult],
):
    """
    Action with compensators and @on_error(ValueError).

    Error handling order:
    1. fail_aspect raises ValueError.
    2. _rollback_saga() — unwind (rollback_reserve_compensate → rollback_charge_compensate).
    3. _handle_aspect_error() → @on_error(ValueError) → Result.

    @on_error receives the ORIGINAL aspect error (ValueError),
    not a compensator error (even if a compensator failed).
    """

    @regular_aspect("Charge payment")
    @result_string("txn_id", required=True)
    async def charge_aspect(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        payment = box.resolve(PaymentService)
        txn_id = await payment.charge(params.amount, "RUB")
        return {"txn_id": txn_id}

    @compensate("charge_aspect", "Rollback payment")
    async def rollback_charge_compensate(
        self,
        params: CompensateTestParams,
        state_before: BaseState,
        state_after: BaseState | None,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        error: Exception,
    ) -> None:
        if state_after is None:
            return
        payment = box.resolve(PaymentService)
        await payment.refund(state_after["txn_id"])

    @regular_aspect("Reserve inventory")
    @result_string("reservation_id", required=True)
    async def reserve_aspect(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        inventory = box.resolve(InventoryService)
        reservation_id = await inventory.reserve(params.item_id, 1)
        return {"reservation_id": reservation_id}

    @compensate("reserve_aspect", "Rollback reservation")
    async def rollback_reserve_compensate(
        self,
        params: CompensateTestParams,
        state_before: BaseState,
        state_after: BaseState | None,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        error: Exception,
    ) -> None:
        if state_after is None:
            return
        inventory = box.resolve(InventoryService)
        await inventory.unreserve(state_after["reservation_id"])

    @regular_aspect("Finalize with error")
    @result_string("order_id", required=True)
    async def fail_aspect(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        raise ValueError(f"Finalize error for {params.user_id}")

    @summary_aspect("Build result")
    async def build_result_summary(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> CompensateTestResult:
        return CompensateTestResult(status="ok")

    @on_error(ValueError, description="Handle finalize error")
    async def handle_finalize_on_error(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        error: Exception,
    ) -> CompensateTestResult:
        """
        Error handler. Runs AFTER compensation unwind completes.
        Receives the ORIGINAL aspect error.

        ``pipeline_txn`` / ``pipeline_res`` echo state keys so tests assert the
        ``BaseState`` passed into this handler matches the failing aspect's input.
        """
        return CompensateTestResult(
            status="handled_after_compensate",
            detail=(
                f"{error}|pipeline_txn={state.get('txn_id')!r}|"
                f"pipeline_res={state.get('reservation_id')!r}"
            ),
        )


# ═════════════════════════════════════════════════════════════════════════════
# FirstRegularFailsOnErrorAction — first regular raises; @on_error empty state
# ═════════════════════════════════════════════════════════════════════════════


@meta(
    description="First regular aspect raises; @on_error sees empty incoming state",
    domain=OrdersDomain,
)
@check_roles(NoneRole)
class FirstRegularFailsOnErrorAction(
    BaseAction[CompensateTestParams, CompensateTestResult],
):
    """
    ValueError in the first regular aspect.

    The ``BaseState`` passed into that aspect is empty; ``@on_error`` must receive
    the same (no txn / reservation keys).
    """

    @regular_aspect("Fail immediately")
    async def boom_first_aspect(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        raise ValueError("first_regular_failed")

    @summary_aspect("Unreachable in failure path")
    async def build_result_summary(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> CompensateTestResult:
        return CompensateTestResult(status="ok")

    @on_error(ValueError, description="Observe pipeline state at first failure")
    async def handle_first_fail_on_error(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        error: Exception,
    ) -> CompensateTestResult:
        return CompensateTestResult(
            status="handled_first_regular",
            detail=(
                f"txn={state.get('txn_id')!r}|"
                f"res={state.get('reservation_id')!r}|err={error!s}"
            ),
        )


# ═════════════════════════════════════════════════════════════════════════════
# SecondRegularFailsOnErrorAction — second regular raises; state from charge only
# ═════════════════════════════════════════════════════════════════════════════


@meta(
    description="Charge succeeds, second regular raises; @on_error sees charge state",
    domain=OrdersDomain,
)
@check_roles(NoneRole)
@depends(PaymentService, description="Payment processing service")
class SecondRegularFailsOnErrorAction(
    BaseAction[CompensateTestParams, CompensateTestResult],
):
    """
    First regular adds ``txn_id``; second raises before any reservation.

    ``@on_error`` must receive the ``BaseState`` **passed into** the failing second
    aspect (has ``txn_id``, no ``reservation_id``).
    """

    @regular_aspect("Charge payment")
    @result_string("txn_id", required=True)
    async def charge_aspect(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        payment = box.resolve(PaymentService)
        txn_id = await payment.charge(params.amount, "RUB")
        return {"txn_id": txn_id}

    @compensate("charge_aspect", "Rollback payment")
    async def rollback_charge_compensate(
        self,
        params: CompensateTestParams,
        state_before: BaseState,
        state_after: BaseState | None,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        error: Exception,
    ) -> None:
        if state_after is None:
            return
        payment = box.resolve(PaymentService)
        await payment.refund(state_after["txn_id"])

    @regular_aspect("Second fails")
    async def boom_second_aspect(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        raise ValueError("second_regular_failed")

    @summary_aspect("Unreachable in failure path")
    async def build_result_summary(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> CompensateTestResult:
        return CompensateTestResult(status="ok")

    @on_error(ValueError, description="Observe pipeline state at second failure")
    async def handle_second_fail_on_error(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        error: Exception,
    ) -> CompensateTestResult:
        return CompensateTestResult(
            status="handled_second_regular",
            detail=(
                f"txn={state.get('txn_id')!r}|"
                f"res={state.get('reservation_id')!r}|err={error!s}"
            ),
        )


# ═════════════════════════════════════════════════════════════════════════════
# SummaryFailsOnErrorStateAction — summary error; @on_error must see state
# ═════════════════════════════════════════════════════════════════════════════


@meta(
    description="Regular succeeds, summary raises; @on_error reads pipeline state",
    domain=OrdersDomain,
)
@check_roles(NoneRole)
@depends(PaymentService, description="Payment processing service")
@depends(InventoryService, description="Inventory service")
class SummaryFailsOnErrorStateAction(
    BaseAction[CompensateTestParams, CompensateTestResult],
):
    """
    All regular aspects complete; ``summary_aspect`` raises.

    Used to assert ``@on_error`` receives the accumulated ``BaseState`` from the
    regular pipeline (not an empty ``BaseState()``).
    """

    @regular_aspect("Charge payment")
    @result_string("txn_id", required=True)
    async def charge_aspect(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        payment = box.resolve(PaymentService)
        txn_id = await payment.charge(params.amount, "RUB")
        return {"txn_id": txn_id}

    @compensate("charge_aspect", "Rollback payment")
    async def rollback_charge_compensate(
        self,
        params: CompensateTestParams,
        state_before: BaseState,
        state_after: BaseState | None,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        error: Exception,
    ) -> None:
        if state_after is None:
            return
        payment = box.resolve(PaymentService)
        await payment.refund(state_after["txn_id"])

    @regular_aspect("Reserve inventory")
    @result_string("reservation_id", required=True)
    async def reserve_aspect(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        inventory = box.resolve(InventoryService)
        reservation_id = await inventory.reserve(params.item_id, 1)
        return {"reservation_id": reservation_id}

    @compensate("reserve_aspect", "Rollback reservation")
    async def rollback_reserve_compensate(
        self,
        params: CompensateTestParams,
        state_before: BaseState,
        state_after: BaseState | None,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        error: Exception,
    ) -> None:
        if state_after is None:
            return
        inventory = box.resolve(InventoryService)
        await inventory.unreserve(state_after["reservation_id"])

    @regular_aspect("Finalize order")
    @result_string("order_id", required=True)
    async def finalize_aspect(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        return {"order_id": f"ORD-{params.user_id}"}

    @summary_aspect("Build result")
    async def build_result_summary(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> CompensateTestResult:
        raise ValueError("summary failed")

    @on_error(ValueError, description="Handle summary failure with state")
    async def handle_summary_on_error(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        error: Exception,
    ) -> CompensateTestResult:
        return CompensateTestResult(
            status="handled_summary_error",
            detail=(
                f"txn={state.get('txn_id')!s}|"
                f"order={state.get('order_id')!s}|"
                f"err={error!s}"
            ),
        )


# ═════════════════════════════════════════════════════════════════════════════
# CheckerRejectionSagaAction — checker failure still registers saga frame
# ═════════════════════════════════════════════════════════════════════════════


@meta(
    description="Two aspects: first succeeds; second fails result checkers",
    domain=OrdersDomain,
)
@check_roles(NoneRole)
@depends(PaymentService, description="Payment processing service")
@depends(SagaCompensateTraceService, description="Test trace for second compensator")
class CheckerRejectionSagaAction(
    BaseAction[CompensateTestParams, CompensateTestResult],
):
    """
    First aspect charges payment; second returns a dict that fails ``min_length``.

    Used to assert that a ``SagaFrame`` with ``state_after=None`` is pushed for
    the second aspect and its compensator runs before the first aspect's
    compensator.
    """

    @regular_aspect("First step — charge")
    @result_string("txn_id", required=True, min_length=1)
    async def first_aspect(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        payment = box.resolve(PaymentService)
        txn_id = await payment.charge(params.amount, "RUB")
        return {"txn_id": txn_id}

    @compensate("first_aspect", "Rollback first — refund")
    async def rollback_first_aspect_compensate(
        self,
        params: CompensateTestParams,
        state_before: BaseState,
        state_after: BaseState | None,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        error: Exception,
    ) -> None:
        if state_after is None:
            return
        payment = box.resolve(PaymentService)
        await payment.refund(state_after["txn_id"])

    @regular_aspect("Second step — invalid token length")
    @result_string("token", required=True, min_length=5)
    async def second_aspect(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        return {"token": "bad"}

    @compensate("second_aspect", "Rollback second — trace only")
    async def rollback_second_aspect_compensate(
        self,
        params: CompensateTestParams,
        state_before: BaseState,
        state_after: BaseState | None,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        error: Exception,
    ) -> None:
        trace = box.resolve(SagaCompensateTraceService)
        await trace.record_second_rollback(state_after_none=(state_after is None))

    @summary_aspect("Unreachable summary")
    async def build_result_summary(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> CompensateTestResult:
        return CompensateTestResult(status="ok")


# ═════════════════════════════════════════════════════════════════════════════
# CompensateWithContextAction — compensator with @context_requires
# ═════════════════════════════════════════════════════════════════════════════


@meta(
    description="Action with a compensator that uses @context_requires",
    domain=OrdersDomain,
)
@check_roles(NoneRole)
@depends(PaymentService, description="Payment processing service")
class CompensateWithContextAction(
    BaseAction[CompensateTestParams, CompensateTestResult],
):
    """
    Action with a compensator that uses @context_requires.

    rollback_charge_compensate declares access to Ctx.User.user_id.
    The machine builds a ContextView and passes it as the 8th parameter (ctx).
    The compensator calls ctx.get(Ctx.User.user_id) for logging.

    Pipeline:
    1. charge_aspect (regular, compensator + @context_requires).
    2. fail_aspect (regular, raises ValueError).
    3. build_result_summary (summary).
    """

    @regular_aspect("Charge payment")
    @result_string("txn_id", required=True)
    async def charge_aspect(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        payment = box.resolve(PaymentService)
        txn_id = await payment.charge(params.amount, "RUB")
        return {"txn_id": txn_id}

    @compensate("charge_aspect", "Rollback payment with context")
    @context_requires(Ctx.User.user_id)
    async def rollback_charge_compensate(
        self,
        params: CompensateTestParams,
        state_before: BaseState,
        state_after: BaseState | None,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        error: Exception,
        ctx: Any,
    ) -> None:
        """
        Compensator with context access.

        Uses ctx.get(Ctx.User.user_id) and calls refund() on PaymentService.
        """
        _ = ctx.get(Ctx.User.user_id)
        if state_after is None:
            return
        payment = box.resolve(PaymentService)
        await payment.refund(state_after["txn_id"])

    @regular_aspect("Finalize with error")
    @result_string("order_id", required=True)
    async def fail_aspect(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        raise ValueError("Finalize error")

    @summary_aspect("Build result")
    async def build_result_summary(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> CompensateTestResult:
        return CompensateTestResult(status="ok")
