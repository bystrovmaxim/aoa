# packages/aoa-demo/src/aoa/demo/fastapi_mcp_services/actions/cancel_order.py
"""
CancelOrderAction — the full three-level access cascade (role, guard, access_decide).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Unlike ``CreateOrderAction``/``GetOrderAction`` (open to ``GuestRole``), cancelling
an order needs all three levels of the access-control cascade:

    1. Role     — ``grant(CustomerRole)``: caller must be a customer.
    2. Guard    — a locked order (``order_id`` starting with ``"LOCKED-"``)
                  cannot be cancelled by anyone, regardless of role.
    3. Fact     — ``access_decide``: the order must exist and belong to the
                  caller. Both failure causes — no such order, or someone
                  else's order — return the exact same ``FORBIDDEN_OBJECT``
                  verdict, so probing order IDs cannot distinguish "doesn't
                  exist" from "exists but isn't yours" (oracle safety).

The owner is looked up **server-side**, in the module-level ``_ORDERS`` table
below, and is deliberately *not* a ``Params`` field. A real service would do
the same lookup through a connection
(``connections["orders_db"].get(params.order_id)``); the in-module table keeps
this demo self-contained, matching ``CreateOrderAction``/``GetOrderAction``'s
hardcoded result data, without making the check forgeable.

That distinction is the whole point, not a detail: an earlier version of this
action took ``owner_user_id`` as a ``Params`` field, so the caller *claimed*
ownership rather than proving it. Sending ``owner_user_id`` set to one's own id
was enough to walk straight past level 3 and cancel someone else's order
(audit-11 finding 2). Anything the request can set cannot be the thing the
request is checked against.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    POST /api/v1/orders/{order_id}/cancel
      |
      v
  RoleChecker.check   -> CustomerRole? guard passes (order not locked)?
      |
      v
  access_decide        -> order in _ORDERS and belongs to caller?
                           both "no" cases -> FORBIDDEN_OBJECT
      |
      v
  cancel_summary       -> Result(order_id, status="cancelled")

"""

from collections.abc import Mapping
from typing import Final, NamedTuple

from pydantic import Field

from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.context import Context
from aoa.action_machine.intents.access_control import FORBIDDEN_OBJECT, AllowedVerdict, FailSecurityVerdict
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles, grant
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox

from ..orders_domain import OrdersDomain


class CustomerRole(ApplicationRole):
    """A regular, authenticated customer — may cancel only their own orders."""

    name = "customer"
    description = "Regular customer."


class _OrderRow(NamedTuple):
    """One row of the stand-in orders table: who owns the order, and its status."""

    owner_user_id: str
    status: str


# The stand-in for a real orders table (``connections["orders_db"]`` in a real
# service). Deliberately module-level and not reachable from Params: the caller
# must not be able to state who owns an order -- see the module docstring.
_ORDERS: Final[Mapping[str, _OrderRow]] = {
    "ORD-1": _OrderRow(owner_user_id="alice", status="pending"),
    "ORD-2": _OrderRow(owner_user_id="bob", status="pending"),
    "LOCKED-1": _OrderRow(owner_user_id="alice", status="pending"),
    "CANCELLED-1": _OrderRow(owner_user_id="alice", status="cancelled"),
}


@meta(description="Cancel an order", domain=OrdersDomain)
@check_roles(
    grant(CustomerRole),
    guard=lambda user, params: not params.order_id.startswith("LOCKED-"),
    reason=FailSecurityVerdict("order is locked"),
)
class CancelOrderAction(BaseAction["CancelOrderAction.Params", "CancelOrderAction.Result"]):

    class Params(BaseParams):
        """Order cancellation input parameters."""

        order_id: str = Field(
            description="Unique identifier of the order to cancel",
            min_length=1,
            examples=["ORD-1"],
        )

    class Result(BaseResult):
        """Order cancellation result payload."""

        order_id: str = Field(description="Order identifier", examples=["ORD-user_123-001"])
        status: str = Field(description="Order status after cancellation", examples=["cancelled"])

    async def access_decide(
        self,
        params: "CancelOrderAction.Params",
        context: Context,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> FailSecurityVerdict | AllowedVerdict:
        """Level 3: the order must exist and belong to the caller.

        Existence and ownership are checked together, in one branch, on
        purpose — see ``FORBIDDEN_OBJECT``'s own comment for why a separate
        "does it exist" step followed by a separate "is it yours" step is the
        wrong shape here, even though both currently return the same verdict.
        Once ownership is confirmed, a more specific reason ("already
        cancelled") is safe to reveal: the caller *has* proven this is their
        own order — the owner came from ``_ORDERS``, not from the request — so
        a specific reason no longer helps them enumerate anyone else's.
        """
        order = _ORDERS.get(params.order_id)
        if order is None or order.owner_user_id != context.user.user_id:
            return FORBIDDEN_OBJECT
        if order.status == "cancelled":
            return FailSecurityVerdict("order is already cancelled")
        return AllowedVerdict()

    @summary_aspect("Cancel the order")
    async def cancel_summary(
        self,
        params: "CancelOrderAction.Params",
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> "CancelOrderAction.Result":
        return CancelOrderAction.Result(order_id=params.order_id, status="cancelled")
