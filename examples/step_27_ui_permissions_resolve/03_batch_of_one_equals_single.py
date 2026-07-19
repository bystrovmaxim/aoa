"""
03_batch_of_one_equals_single.py — a single question is a batch of one, not a special case

machine.check_access_decide has two shapes under one name: a single (action,
params) pair, and a list of pairs. FR-2 says a single question must not be a
separate code path — the list form is the primitive, and the single-action
form is implemented by recursing into a list of exactly one item. This
example proves it directly: the single-action call and the one-item-batch
call produce byte-for-byte the same wire shape once printed via model_dump()
— here, AllowedVerdict, whose model_dump() shows exactly {kind}, the same
shape POST /permissions/resolve actually returns.

This is exactly why POST /permissions/resolve can be list-shaped from day
one (items/results) without a slower or different path for the common case
of "just one question" — there is no such separate path to be slower.

Tutorial: ../../docs/tutorials/step-27-ui-permissions-resolve_draft.md

Run:
    uv run python examples/step_27_ui_permissions_resolve/03_batch_of_one_equals_single.py
"""

import asyncio

from pydantic import Field

from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class StoreDomain(BaseDomain):
    name = "store"
    description = "Store domain"


class ManagerRole(ApplicationRole):
    name = "manager"
    description = "Can manage orders"


class OrderParams(BaseParams):
    order_id: int = Field(description="Order identifier")


class OrderResult(BaseResult):
    status: str = Field(description="New order status")


@meta(description="Cancel an order", domain=StoreDomain)
@check_roles(ManagerRole)
class CancelOrderAction(BaseAction[OrderParams, OrderResult]):

    @summary_aspect("Cancel the order")
    async def cancel_summary(self, params, state, box, connections):
        return OrderResult(status="cancelled")


async def main() -> None:
    machine = ActionProductMachine()
    manager = Context(user=UserInfo(user_id="m1", roles=(ManagerRole,)))
    params = OrderParams(order_id=7)

    # Single-action form.
    single_verdict = await machine.check_access_decide(manager, CancelOrderAction, params)

    # List form with exactly one item — this is what POST /permissions/resolve
    # actually calls, regardless of how many items the client sent.
    batch_verdicts = await machine.check_access_decide(manager, [(CancelOrderAction, params)])

    single_wire = single_verdict.model_dump()
    batch_wire = batch_verdicts[0].model_dump()

    print(f"single           = {single_wire!r}")
    print(f"batch[0]         = {batch_wire!r}")
    print(f"identical shape  = {single_wire == batch_wire}")


asyncio.run(main())
