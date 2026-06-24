"""
01_testbench.py — TestBench at every altitude (one test per altitude)

AOA tests run the SAME Action through the SAME machine — pipeline, checkers,
roles, @depends, plugins all real — and swap only the reality around it. Because
an Action holds no state between calls, a test just assembles the input and
environment, then runs at whatever altitude the risk warrants:

  bench.run(action, params, rollup=)                  — the whole Action
  bench.run_aspect(action, "name", params=, state=)   — one @regular_aspect
  bench.run_summary(action, params=, state=)          — the @summary_aspect alone
  bench.run_compensator(action, "name", params=, state_before=, state_after=, error=)
  (no run_on_error — @on_error is exercised by a full run that triggers the error)

Environment substitution (with_mocks / connections=) is the next chapter; context
(with_user/...) the one after. Here with_user is used minimally so @check_roles passes.

Tutorial: ../../docs/tutorials/step-23-testbench_draft.md  ·  topic: TestBench altitudes

Run:
    uv run python examples/step_23_testbench/01_testbench.py
"""

import asyncio
from unittest.mock import AsyncMock

from pydantic import Field

from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.checkers import result_string
from aoa.action_machine.intents.compensate import compensate
from aoa.action_machine.intents.depends import depends
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.intents.on_error import on_error
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.testing import TestBench


class BillingDomain(BaseDomain):
    name = "billing"
    description = "Billing domain"


class AdminRole(ApplicationRole):
    name = "admin"
    description = "Administrator"


@meta(description="Payment gateway", domain=BillingDomain)
class PaymentService(BaseResource):
    async def charge(self, amount: float) -> str:
        raise NotImplementedError("real gateway — mocked in tests")

    async def refund(self, txn_id: str) -> None:
        raise NotImplementedError("real gateway — mocked in tests")

    def get_wrapper_class(self) -> type[BaseResource] | None:
        return None


class ChargeParams(BaseParams):
    amount: float = Field(gt=0, description="Amount to charge")


class ChargeResult(BaseResult):
    txn_id: str = Field(description="Transaction id")
    amount: float = Field(description="Charged amount")


@meta(description="Charge a payment", domain=BillingDomain)
@check_roles(AdminRole)
@depends(PaymentService)
class ChargeAction(BaseAction[ChargeParams, ChargeResult]):

    @regular_aspect("Charge via gateway")
    @result_string("txn_id", required=True)
    async def charge_aspect(self, params, state, box, connections):
        gateway = await box.resolve(PaymentService)
        return {"txn_id": await gateway.charge(params.amount)}

    @compensate(charge_aspect, "Refund the charge")
    async def charge_compensate(self, params, state_before, state_after, box, connections, error):
        gateway = await box.resolve(PaymentService)
        await gateway.refund(state_after["txn_id"])

    @summary_aspect("Build result")
    async def build_summary(self, params, state, box, connections):
        return ChargeResult(txn_id=state["txn_id"], amount=params.amount)

    @on_error(ValueError, description="Reject when the gateway declines")
    async def declined_on_error(self, params, state, box, connections, error):
        return ChargeResult(txn_id="declined", amount=0.0)


def make_bench(gateway: AsyncMock) -> TestBench:
    return (
        TestBench()
        .with_user(user_id="admin", roles=(AdminRole,))   # so @check_roles passes (context: ch.25)
        .with_mocks({PaymentService: gateway})            # mock @depends (ch.24)
    )


async def main() -> None:
    params = ChargeParams(amount=1500.0)

    # ── 1. Whole Action ──────────────────────────────────────────────────────
    gw = AsyncMock(spec=PaymentService)
    gw.charge.return_value = "txn-001"
    result = await make_bench(gw).run(ChargeAction(), params, rollup=False)
    print(f"1) run (whole Action)        -> txn={result.txn_id} amount={result.amount}")

    # ── 2. One regular aspect ────────────────────────────────────────────────
    gw = AsyncMock(spec=PaymentService)
    gw.charge.return_value = "txn-002"
    state_after = await make_bench(gw).run_aspect(
        ChargeAction(), "charge_aspect", params=params, state={}, rollup=False,
    )
    print(f"2) run_aspect (charge_aspect)-> state.txn_id={state_after['txn_id']}")

    # ── 3. Summary alone (state supplied; gateway never touched) ──────────────
    gw = AsyncMock(spec=PaymentService)
    result = await make_bench(gw).run_summary(
        ChargeAction(), params=params, state={"txn_id": "txn-pre"}, rollup=False,
    )
    print(f"3) run_summary               -> txn={result.txn_id}  (charge called: {gw.charge.await_count > 0})")

    # ── 4. Compensator as a unit (does NOT suppress exceptions) ───────────────
    gw = AsyncMock(spec=PaymentService)
    await make_bench(gw).run_compensator(
        ChargeAction(), "charge_compensate",
        params=params,
        state_before=BaseState(),
        state_after=BaseState(txn_id="txn-004"),
        error=RuntimeError("later step failed"),
    )
    print(f"4) run_compensator           -> gateway.refund('txn-004') called: {gw.refund.await_count == 1}")

    # ── 5. @on_error via a full run that triggers the error ───────────────────
    gw = AsyncMock(spec=PaymentService)
    gw.charge.side_effect = ValueError("card declined")
    result = await make_bench(gw).run(ChargeAction(), params, rollup=False)
    print(f"5) run + @on_error(ValueError) -> txn={result.txn_id}  (handler returned a Result)")


if __name__ == "__main__":
    asyncio.run(main())
