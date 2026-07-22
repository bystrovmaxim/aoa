"""
04_access_decide.py — access_decide: the object-level check

A role says who someone is; it knows nothing about the specific object a call
touches — the same CustomerRole covers every customer's order alike.
access_decide is the third, object-level check: it runs after the role has
already matched, loads or receives the concrete object, and decides based on
it. Its default (on BaseAction) is True — no extra restriction beyond roles.

This example has no grant(when=...) and no guard=, on purpose: the only thing
that can deny a call here is access_decide, so a denial is unambiguously the
result of the object check, not of something else in the cascade.

Tutorial: ../../docs/index_draft.md  ·  topic: Authorization and roles

Run:
    uv run python examples/step_03_authorization_and_roles/04_access_decide.py
"""

import asyncio

from pydantic import Field

from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.exceptions.authorization_error import AuthorizationError
from aoa.action_machine.intents.access_control import AllowedVerdict, FailSecurityVerdict
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.tools_box import ToolsBox


class StoreDomain(BaseDomain):
    name = "store"
    description = "Store domain"


class CustomerRole(ApplicationRole):
    name = "customer"
    description = "Regular customer"


# ---------------------------------------------------------------------------
# Params carries who the order actually belongs to (owner_user_id) — a real
# service would look this up via a connection instead; this example takes it
# directly to stay self-contained, same simplification as aoa-demo's own
# CancelOrderAction.
# ---------------------------------------------------------------------------

class OrderParams(BaseParams):
    order_id: str = Field(description="Order identifier")
    owner_user_id: str = Field(description="user_id of the order's owner")


class OrderResult(BaseResult):
    order_id: str = Field(description="Order identifier")
    action: str = Field(description="What was performed")


# ---------------------------------------------------------------------------
# Only CustomerRole is required (no grant when=, no guard=) — the sole thing
# left to decide access is access_decide's ownership check.
# ---------------------------------------------------------------------------

@meta(description="Cancel an order", domain=StoreDomain)
@check_roles(CustomerRole)
class CancelOrderAction(BaseAction[OrderParams, OrderResult]):

    async def access_decide(
        self,
        params: OrderParams,
        context: Context,
        box: ToolsBox,
        connections: dict,
    ) -> FailSecurityVerdict | AllowedVerdict:
        if params.owner_user_id == context.user.user_id:
            return AllowedVerdict()
        return FailSecurityVerdict("order does not belong to the caller")

    @summary_aspect("Cancel the order")
    async def cancel_summary(self, params, state, box, connections):
        return OrderResult(order_id=params.order_id, action="cancelled")


# ---------------------------------------------------------------------------
# Runner — same customer, own order vs. someone else's order.
# ---------------------------------------------------------------------------

async def main() -> None:
    machine = ActionProductMachine()
    alice = Context(user=UserInfo(user_id="alice", roles=(CustomerRole,)))

    cases = [
        ("alice, her own order", OrderParams(order_id="ord-001", owner_user_id="alice")),
        ("alice, bob's order", OrderParams(order_id="ord-002", owner_user_id="bob")),
    ]

    for label, params in cases:
        try:
            await machine.run(alice, CancelOrderAction(), params)
            print(f"{label:<24} -> allowed")
        except AuthorizationError:
            print(f"{label:<24} -> denied")


asyncio.run(main())
