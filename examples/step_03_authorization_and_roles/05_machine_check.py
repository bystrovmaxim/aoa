"""
05_machine_check.py — machine.check_access_decide: "can it run?" without running it

A frontend deciding whether to show a "Cancel" button, or grey it out, cannot
find out by actually trying to cancel the order. machine.check_access_decide
answers "would this be allowed?" — evaluating the exact same role/guard/
access_decide cascade as machine.run(), but never running the aspect pipeline:
a denial here is AccessVerdict(kind=ResolveItemKind.SECURITY, reason=...), not
an exception.

This example reuses the same access-controlled action as 04_access_decide.py
(role + access_decide only) — it does not redefine the three levels again, it
only demonstrates the two shapes of machine.check_access_decide: one action at
a time, and a list of (action, params) pairs at once.

Tutorial: ../../docs/index_draft.md  ·  topic: Authorization and roles

Run:
    uv run python examples/step_03_authorization_and_roles/05_machine_check.py
"""

import asyncio

from pydantic import Field

from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.access_control import ResolveItemKind
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class StoreDomain(BaseDomain):
    name = "store"
    description = "Store domain"


class CustomerRole(ApplicationRole):
    name = "customer"
    description = "Regular customer"


class OrderParams(BaseParams):
    order_id: str = Field(description="Order identifier")
    owner_user_id: str = Field(description="user_id of the order's owner")


class OrderResult(BaseResult):
    order_id: str = Field(description="Order identifier")
    action: str = Field(description="What was performed")


@meta(description="Cancel an order", domain=StoreDomain)
@check_roles(CustomerRole)
class CancelOrderAction(BaseAction[OrderParams, OrderResult]):

    async def access_decide(self, params, context, box, connections) -> bool:
        return params.owner_user_id == context.user.user_id

    @summary_aspect("Cancel the order")
    async def cancel_summary(self, params, state, box, connections):
        return OrderResult(order_id=params.order_id, action="cancelled")


# ---------------------------------------------------------------------------
# Runner — single form, then list form. Neither call executes cancel_summary.
# ---------------------------------------------------------------------------

async def main() -> None:
    machine = ActionProductMachine()
    alice = Context(user=UserInfo(user_id="alice", roles=(CustomerRole,)))

    print("Single form — should the 'Cancel' button be shown for ord-001?")
    verdict = await machine.check_access_decide(
        alice, CancelOrderAction, OrderParams(order_id="ord-001", owner_user_id="alice")
    )
    allowed = verdict.kind == ResolveItemKind.SUCCESS
    print(f"  kind={verdict.kind}  ->  {'show button' if allowed else 'grey out button'}")

    print("\nList form — checking three orders in Alice's order history at once:")
    verdicts = await machine.check_access_decide(
        alice,
        [
            (CancelOrderAction, OrderParams(order_id="ord-001", owner_user_id="alice")),
            (CancelOrderAction, OrderParams(order_id="ord-002", owner_user_id="bob")),
            (CancelOrderAction, OrderParams(order_id="ord-003", owner_user_id="alice")),
        ],
    )
    for order_id, verdict in zip(("ord-001", "ord-002", "ord-003"), verdicts, strict=True):
        print(f"  {order_id:<10} kind={verdict.kind}  reason={verdict.reason!r}")


asyncio.run(main())
