# src/examples/fastapi_mcp_services/actions/get_order.py
"""
GetOrderAction — fetch an order by identifier.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Demonstrates a GET-style endpoint with a path parameter. FastAPI reads
``order_id`` from the URL and maps it into ``Params``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    GET /api/v1/orders/{order_id}
      |
      v
  Params(order_id from path)
      |
      v
  get_order_summary -> Result(order_id, status, total)

Nested ``Params`` and ``Result`` live on the action class. Action description
comes from ``@meta(description=...)``; aspect description from
``@summary_aspect("...")``.

"""

from pydantic import Field

from action_machine.auth import NoneRole
from action_machine.intents.aspects import summary_aspect
from action_machine.intents.check_roles import check_roles
from action_machine.intents.meta import meta
from action_machine.logging import Channel
from action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from action_machine.resources import BaseResource
from action_machine.runtime.tools_box import ToolsBox

from ..domains import OrdersDomain


@meta(description="Get order by identifier", domain=OrdersDomain)
@check_roles(NoneRole)
class GetOrderAction(BaseAction["GetOrderAction.Params", "GetOrderAction.Result"]):

    class Params(BaseParams):
        """
        Order lookup parameters.

        ``order_id`` is bound from the FastAPI path parameter.
        """
        order_id: str = Field(
            description="Unique order identifier",
            min_length=1,
            examples=["ORD-user_123-001"],
        )

    class Result(BaseResult):
        """Order fetch result payload."""
        order_id: str = Field(
            description="Order identifier",
            examples=["ORD-user_123-001"],
        )
        status: str = Field(
            description="Current order status",
            examples=["created", "paid", "shipped"],
        )
        total: float = Field(
            description="Final order total",
            ge=0,
            examples=[1500.0],
        )

    @summary_aspect("Load and return order data")
    async def get_order_summary(
        self,
        params: "GetOrderAction.Params",
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> "GetOrderAction.Result":
        """Return stub order data for the requested ``order_id``."""
        await box.info(
            Channel.business,
            "Order request: {%var.order_id}",
            order_id=params.order_id,
        )

        return GetOrderAction.Result(
            order_id=params.order_id,
            status="created",
            total=1500.0,
        )
