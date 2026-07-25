"""
10_object_level_generic_deny_and_honest_error.py — oracle safety and honest errors

access_decide (the object-level check) has two easy-to-get-wrong spots:

1. "no such object" and "object belongs to someone else" must answer
   identically -- otherwise the reason text becomes an oracle for which
   object IDs exist. Both cases return the exact same shared verdict,
   FORBIDDEN_OBJECT (aoa.action_machine.intents.access_control), not two
   separate FailSecurityVerdict("...") calls with different text.
2. A crash inside access_decide (a bug, an unreachable connection) is not a
   denial -- it is "could not check". check_access_decide already turns any
   unexpected exception into FailErrorVerdict("EVALUATION_FAILED"), never a
   denial, and never cached as one.

This example runs four cases against the same action, in one batch: the
caller's own order, someone else's order, a missing order, and an order
whose check crashes -- foreign and missing print the exact same verdict, and
the crash does not affect the other three items.

Tutorial: ../../docs/tutorials/step-03-authorization-and-roles_draft.md

Run:
    uv run python examples/step_27_ui_permissions_resolve/10_object_level_generic_deny_and_honest_error.py
"""

import asyncio

from pydantic import Field

from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.access_control import FORBIDDEN_OBJECT, AllowedVerdict, FailSecurityVerdict
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


# The owner is resolved server-side, never taken from Params: anything the request
# can set cannot be the thing the request is checked against. Same shape as
# aoa-demo's own CancelOrderAction (audit-11 finding 2, and this file's own
# omission -- narrow-audit finding 4).
ORDERS = {"ORD-1": "alice", "ORD-2": "bob"}


class OrderParams(BaseParams):
    order_id: str = Field(description="Order identifier")


class OrderResult(BaseResult):
    status: str = Field(description="New order status")


@meta(description="Cancel an order", domain=StoreDomain)
@check_roles(CustomerRole)
class CancelOrderAction(BaseAction[OrderParams, OrderResult]):

    async def access_decide(self, params, context, box, connections) -> FailSecurityVerdict | AllowedVerdict:
        if params.order_id.startswith("CRASH-"):
            raise RuntimeError("orders_db unreachable")  # a genuine bug/outage, not a denial
        owner = ORDERS.get(params.order_id)
        # Existence and ownership in one branch, one shared verdict: "no such order" and
        # "someone else's order" must be indistinguishable.
        if owner is None or owner != context.user.user_id:
            return FORBIDDEN_OBJECT
        return AllowedVerdict()

    @summary_aspect("Cancel the order")
    async def cancel_summary(self, params, state, box, connections):
        return OrderResult(status="cancelled")


async def main() -> None:
    machine = ActionProductMachine()
    alice = Context(user=UserInfo(user_id="alice", roles=(CustomerRole,)))

    cases = [
        ("own order", OrderParams(order_id="ORD-1")),
        ("foreign order", OrderParams(order_id="ORD-2")),  # belongs to bob
        ("missing order", OrderParams(order_id="NO-SUCH-ORDER")),
        ("crash during check", OrderParams(order_id="CRASH-1")),
    ]

    verdicts = await machine.check_access_decide(alice, [(CancelOrderAction, params) for _, params in cases])

    for (label, _), verdict in zip(cases, verdicts, strict=True):
        print(f"{label:<20} -> kind={verdict.kind!r} reason={getattr(verdict, 'reason', None)!r}")

    foreign_verdict, missing_verdict = verdicts[1], verdicts[2]
    assert foreign_verdict is FORBIDDEN_OBJECT
    assert missing_verdict is FORBIDDEN_OBJECT
    print("\nforeign and missing gave the exact same verdict object -- no oracle.")
    print("the crash on item 4 did not affect items 1-3 -- per-item isolation.")


asyncio.run(main())
