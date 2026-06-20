"""
Saga (@compensate): two regular aspects, rollback in reverse order.

Tutorial: ../../docs/index_draft.md  ·  topic: Saga and compensations

Run:
    uv run python examples/step_04_saga_and_compensations/01_saga_compensate.py
"""
import asyncio

from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.checkers import result_string
from aoa.action_machine.intents.compensate import compensate
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.logging import Channel, ConsoleLogger
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class RootDomain(BaseDomain):
    name = "root"
    description = "Root domain"


class OrderParams(BaseParams):
    order_id: str = Field(description="Order ID")


class OrderResult(BaseResult):
    order_id: str = Field(description="Order ID")
    status: str = Field(description="Status")


@meta(description="Fulfill order (saga)", domain=RootDomain)
@check_roles(GuestRole)
class FulfillOrderAction(BaseAction[OrderParams, OrderResult]):

    @regular_aspect("Reserve inventory")
    @result_string("reservation_id", required=True)
    async def reserve_aspect(self, params, state, box, connections):
        await box.info(
            Channel.business,
            "regular: reserve order={%var.order_id}",
            order_id=params.order_id,
        )
        return {"reservation_id": f"res-{params.order_id}"}

    @compensate("reserve_aspect", "Release reservation")
    async def reserve_compensate(self, params, state_before, state_after, box, connections, error):
        rid = state_after["reservation_id"] if state_after else "?"
        await box.info(
            Channel.business,
            "compensate: release reservation {%var.rid}",
            rid=rid,
        )

    @regular_aspect("Charge payment")
    @result_string("txn_id", required=True)
    async def charge_aspect(self, params, state, box, connections):
        await box.info(
            Channel.business,
            "regular: charge order={%var.order_id}",
            order_id=params.order_id,
        )
        return {"txn_id": f"txn-{params.order_id}"}

    @compensate("charge_aspect", "Refund payment")
    async def charge_compensate(self, params, state_before, state_after, box, connections, error):
        txn = state_after["txn_id"] if state_after else "?"
        await box.info(
            Channel.business,
            "compensate: refund {%var.txn}",
            txn=txn,
        )

    @summary_aspect("Confirm order")
    async def confirm_summary(self, params, state, box, connections):
        raise ValueError("order service unavailable")


async def main() -> None:
    machine = ActionProductMachine(
        log_coordinator=LogCoordinator(loggers=[ConsoleLogger()])
    )
    print("Sample 04 saga compensate\n")
    try:
        await machine.run(
            Context(),
            FulfillOrderAction(),
            params=OrderParams(order_id="ord-001"),
        )
    except ValueError as e:
        print("\n" + str(e))


asyncio.run(main())
