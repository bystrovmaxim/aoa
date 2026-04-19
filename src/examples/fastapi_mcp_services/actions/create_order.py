# src/examples/fastapi_mcp_services/actions/create_order.py
"""
CreateOrderAction for order creation.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Demonstrates an action with request validation via Pydantic ``Field``
constraints. Constraints are propagated into OpenAPI schema and enforced by
FastAPI during request deserialization.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    POST /api/v1/orders
      |
      v
  Params validation (Pydantic/FastAPI)
      |
      v
  validate_aspect -> {"validated_user": user_id}
      |
      v
  build_result_summary -> Result(order_id, status, total)

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``user_id`` is a non-empty string.
- ``amount`` is a float strictly greater than zero (``gt=0``).
- ``currency`` matches ISO-like uppercase code pattern ``^[A-Z]{3}$``.
- ``validated_user`` must be produced by regular aspect before summary phase.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    Request body:
    {"user_id": "user_123", "amount": 1500.0, "currency": "RUB"}

    Response body:
    {"order_id": "ORD-user_123-001", "status": "created", "total": 1500.0}

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- FastAPI returns 422 for payloads violating field constraints.
- Example action is intentionally simple and uses static order-id suffix.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Example shared action for HTTP and MCP transports.
CONTRACT: Validate input early and build deterministic result payload.
INVARIANTS: Summary consumes state produced by regular aspect.
═══════════════════════════════════════════════════════════════════════════════
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from typing import Any

from pydantic import Field

from action_machine.auth.none_role import NoneRole
from action_machine.intents.aspects.regular_aspect_decorator import regular_aspect
from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.check_roles.check_roles_decorator import check_roles
from action_machine.intents.checkers import result_string
from action_machine.intents.meta.meta_decorator import meta
from action_machine.logging.channel import Channel
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.model.base_state import BaseState
from action_machine.resources.base_resource_manager import BaseResourceManager
from action_machine.runtime.tools_box import ToolsBox

from ..domains import OrdersDomain


@meta(description="Create new order", domain=OrdersDomain)
@check_roles(NoneRole)
class CreateOrderAction(BaseAction["CreateOrderAction.Params", "CreateOrderAction.Result"]):

    class Params(BaseParams):
        """
        Order creation input parameters.
        """
        user_id: str = Field(
            description="Identifier of the user creating the order",
            min_length=1,
            examples=["user_123"],
        )
        amount: float = Field(
            description="Order amount in selected currency. Must be positive",
            gt=0,
            examples=[1500.0, 99.99],
        )
        currency: str = Field(
            default="RUB",
            description="Currency code in ISO 4217 format (3 uppercase letters)",
            pattern=r"^[A-Z]{3}$",
            examples=["RUB", "USD", "EUR"],
        )

    class Result(BaseResult):
        """Order creation result payload."""
        order_id: str = Field(
            description="Unique identifier of created order",
            examples=["ORD-user_123-001"],
        )
        status: str = Field(
            description="Order status after creation",
            examples=["created"],
        )
        total: float = Field(
            description="Final order total",
            ge=0,
            examples=[1500.0],
        )

    @regular_aspect("Validate order data")
    @result_string("validated_user", required=True)
    async def validate_aspect(
        self,
        params: "CreateOrderAction.Params",
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        """
        Validate input and write user id into state.
        """
        await box.info(
            Channel.business,
            "Order validation: user={%var.user_id}, amount={%var.amount}",
            user_id=params.user_id,
            amount=params.amount,
        )
        return {"validated_user": params.user_id}

    @summary_aspect("Build order creation result")
    async def build_result_summary(
        self,
        params: "CreateOrderAction.Params",
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> "CreateOrderAction.Result":
        """
        Build final result from params and pipeline state.
        """
        return CreateOrderAction.Result(
            order_id=f"ORD-{state['validated_user']}-001",
            status="created",
            total=params.amount,
        )
