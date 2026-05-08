# packages/aoa-examples/src/aoa/examples/fastapi_mcp_services/actions/create_order.py
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

"""

from typing import Any

from pydantic import Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.checkers import result_string
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.logging import Channel
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox

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
        connections: dict[str, BaseResource],
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
        connections: dict[str, BaseResource],
    ) -> "CreateOrderAction.Result":
        """
        Build final result from params and pipeline state.
        """
        return CreateOrderAction.Result(
            order_id=f"ORD-{state['validated_user']}-001",
            status="created",
            total=params.amount,
        )
