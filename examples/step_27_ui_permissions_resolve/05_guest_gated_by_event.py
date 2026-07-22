"""
05_guest_gated_by_event.py — GuestRole gates the question, access_decide gates the answer

@check_roles(GuestRole) only means "anyone may ask this question" — it says
nothing about what the answer is. TrackOrderAction below lets a guest track a
package by a tracking_token from an email, with no login at all — but
access_decide (level 3) still bases allowed on real facts: the token must
match the specific order, AND the order must have actually reached the
"shipped" event. Before that event happens, even a guest holding the exact
right token gets an honest FailSecurityVerdict — not because they are the
wrong person, but because the event has not happened yet.

access_decide is not limited to "is this your object" checks — it can
condition the answer on anything computable from params/context/connections:
here, time/state, not ownership. access_decide returns FailSecurityVerdict/
AllowedVerdict directly, with whatever reason its author chose — the same
clean-reason mechanism as the role-gate's FORBIDDEN_ROLE or a
grant(when=..., reason=...)'s declared string, no more raw cascade text.

Tutorial: ../../docs/tutorials/step-27-ui-permissions-resolve_draft.md

Run:
    uv run python examples/step_27_ui_permissions_resolve/05_guest_gated_by_event.py
"""

import asyncio
from dataclasses import dataclass

from pydantic import Field

from aoa.action_machine.auth.guest_role import GuestRole
from aoa.action_machine.context.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.access_control import AllowedVerdict, FailSecurityVerdict
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class StoreDomain(BaseDomain):
    name = "store"
    description = "Store domain"


@dataclass(frozen=True)
class Order:
    tracking_token: str
    status: str  # "created" | "paid" | "shipped" | "in_transit" | "delivered"


# A tiny in-memory "orders_db" stand-in — real code would be a real connection.
_ORDERS = {7: Order(tracking_token="secret-token-7", status="paid")}


class TrackOrderParams(BaseParams):
    order_id: int = Field(description="Order identifier")
    tracking_token: str = Field(description="Secret token from the shipping confirmation email")


class TrackOrderResult(BaseResult):
    status: str = Field(description="Order status")


@meta(description="Track an order by its tracking token", domain=StoreDomain)
@check_roles(GuestRole)  # role-gate: anyone may ask — access_decide still decides the answer
class TrackOrderAction(BaseAction[TrackOrderParams, TrackOrderResult]):

    async def access_decide(
        self, params: TrackOrderParams, context, box, connections
    ) -> FailSecurityVerdict | AllowedVerdict:
        order = _ORDERS[params.order_id]
        if order.tracking_token != params.tracking_token:
            return FailSecurityVerdict("tracking token does not match this order")  # wrong secret
        if order.status in ("shipped", "in_transit", "delivered"):
            return AllowedVerdict()
        return FailSecurityVerdict("order has not shipped yet")  # the "shipped" event hasn't fired yet

    @summary_aspect("Return the order status")
    async def track_summary(self, params, state, box, connections):
        return TrackOrderResult(status=_ORDERS[params.order_id].status)


async def main() -> None:
    machine = ActionProductMachine()
    guest = Context()  # no login at all — GuestRole covers this
    params = TrackOrderParams(order_id=7, tracking_token="secret-token-7")

    before = await machine.check_access_decide(guest, TrackOrderAction, params)
    print(f"before shipped: kind={before.kind!r} reason={getattr(before, 'reason', '')!r}")

    _ORDERS[7] = Order(tracking_token="secret-token-7", status="shipped")  # the real-world event fires

    after = await machine.check_access_decide(guest, TrackOrderAction, params)
    print(f"after shipped:  kind={after.kind!r} reason={getattr(after, 'reason', '')!r}")  # same guest, same token, no client-side change


asyncio.run(main())
