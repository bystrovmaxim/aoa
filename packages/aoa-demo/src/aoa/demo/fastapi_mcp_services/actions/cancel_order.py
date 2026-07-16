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
    3. Fact     — ``access_decide``: a customer may only cancel their *own*
                  order (``params.owner_user_id == context.user.user_id``).

A real service would look the order's owner up via a connection
(``connections["orders_db"].get(params.order_id)``); this demo takes it
directly as a ``Params`` field to stay self-contained, matching
``CreateOrderAction``/``GetOrderAction``'s hardcoded result data.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    POST /api/v1/orders/{order_id}/cancel
      |
      v
  RoleChecker.check   -> CustomerRole? guard passes (order not locked)?
      |
      v
  access_decide        -> params.owner_user_id == context.user.user_id ?
      |
      v
  cancel_summary       -> Result(order_id, status="cancelled")

"""

from pydantic import Field

from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.context import Context
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


@meta(description="Cancel an order", domain=OrdersDomain)
@check_roles(
    grant(CustomerRole),
    guard=lambda user, params: not params.order_id.startswith("LOCKED-"),
)
class CancelOrderAction(BaseAction["CancelOrderAction.Params", "CancelOrderAction.Result"]):

    class Params(BaseParams):
        """Order cancellation input parameters."""

        order_id: str = Field(
            description="Unique identifier of the order to cancel",
            min_length=1,
            examples=["ORD-user_123-001"],
        )
        owner_user_id: str = Field(
            description="user_id of the order's owner (stands in for an orders_db lookup)",
            min_length=1,
            examples=["user_123"],
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
    ) -> bool:
        """Level 3: the order must belong to the caller."""
        return params.owner_user_id == context.user.user_id

    @summary_aspect("Cancel the order")
    async def cancel_summary(
        self,
        params: "CancelOrderAction.Params",
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> "CancelOrderAction.Result":
        return CancelOrderAction.Result(order_id=params.order_id, status="cancelled")
