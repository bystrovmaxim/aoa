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

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``order_id`` is a non-empty string (``min_length=1``).
- This example returns a stub payload, not persisted data.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    GET /api/v1/orders/ORD-user_123-001

    Response:
    {"order_id": "ORD-user_123-001", "status": "created", "total": 1500.0}

    Edge case: invalid or empty ``order_id`` fails Pydantic validation at the
    transport layer (e.g. FastAPI 422).

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- In a real app, data would load from a database via ``connections``.
- This sample always returns ``status="created"`` and ``total=1500.0``.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Example read action for shared FastAPI/MCP transports.
CONTRACT: Path-bound identifier in; structured order snapshot out.
INVARIANTS: Summary-only pipeline; no regular aspects or state mutations.
═══════════════════════════════════════════════════════════════════════════════
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from pydantic import Field

from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.check_roles import NoneRole, check_roles
from action_machine.logging.channel import Channel
from action_machine.intents.meta.meta_decorator import meta
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.model.base_state import BaseState
from action_machine.resources.base_resource_manager import BaseResourceManager
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
        connections: dict[str, BaseResourceManager],
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
