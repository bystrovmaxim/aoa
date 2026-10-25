# packages/aoa-demo/src/aoa/demo/fastapi_mcp_services/actions/cancel_order.py
"""
CancelOrderAction — a role gate and an object rule together.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Unlike ``CreateOrderAction``/``GetOrderAction`` (open to ``GuestRole``), cancelling
an order needs a role and an object rule:

    1. Role   — ``@check_roles(CustomerRole)``: the caller must be a customer.
    2. Rule   — ``@access_decide``: a locked order (``order_id`` starting with
                ``"LOCKED-"``) cannot be cancelled by anyone, and a customer may
                cancel only their *own* order.

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
  RoleChecker.check   -> CustomerRole?
      |
      v
  access_decide       -> locked? owner_user_id == user.user_id?
      |
      v
  cancel_summary      -> Result(order_id, status="cancelled")

"""

from pydantic import Field

from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.context.context_view import ContextView
from aoa.action_machine.intents.access_control import FORBIDDEN_OBJECT, Allowed, Refused, Verdict
from aoa.action_machine.intents.access_decide import access_decide
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.context_requires import context_requires
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox

from ..orders_domain import OrdersDomain


class CustomerRole(ApplicationRole):
    """A regular, authenticated customer — may cancel only their own orders."""

    name = "customer"
    description = "Regular customer."


@meta(description="Cancel an order", domain=OrdersDomain)
@check_roles(CustomerRole)
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

    @access_decide("Refuse a locked order, or one that is not the caller's")
    @context_requires("user.user_id")
    async def cancel_order_access_decide(
        self,
        params: "CancelOrderAction.Params",
        box: ToolsBox,
        connections: Connections,
        ctx: ContextView,
    ) -> Verdict:
        """A locked order is refused for everyone; anyone else's order is refused, too."""
        if params.order_id.startswith("LOCKED-"):
            return Refused("ORDER_LOCKED")
        if params.owner_user_id == ctx.get("user.user_id"):
            return Allowed()
        return FORBIDDEN_OBJECT

    @summary_aspect("Cancel the order")
    async def cancel_summary(
        self,
        params: "CancelOrderAction.Params",
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> "CancelOrderAction.Result":
        return CancelOrderAction.Result(order_id=params.order_id, status="cancelled")
