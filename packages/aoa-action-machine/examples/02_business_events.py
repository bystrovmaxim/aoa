"""
02_business_events.py — order draft action with a business event.

Run from repository root:
    uv run python packages/aoa-action-machine/examples/02_business_events.py
"""

import asyncio

from pydantic import Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.checkers import result_float, result_int, result_string
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.logging import Channel, ConsoleLogger
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class OrderDomain(BaseDomain):
    name = "orders"
    description = "Order processing domain"


class CreateDraftParams(BaseParams):
    raw_sku: str = Field(description="SKU exactly as received from a client")
    quantity: int = Field(description="Requested quantity")
    unit_price: float = Field(description="Unit price for this request")


class CreateDraftResult(BaseResult):
    sku: str = Field(description="Normalised SKU")
    quantity: int = Field(description="Validated quantity")
    total: float = Field(description="Line total")
    message: str = Field(description="Human-readable summary")


@meta(description="Create order draft with business event", domain=OrderDomain)
@check_roles(NoneRole)
class CreateDraftWithEventAction(BaseAction[CreateDraftParams, CreateDraftResult]):

    @regular_aspect("Normalise SKU")
    @result_string("sku", required=True, min_length=3)
    async def normalise_aspect(self, params, state, box, connections):
        return {"sku": params.raw_sku.strip().upper()}

    @regular_aspect("Calculate total")
    @result_string("sku", required=True, min_length=3)
    @result_int("quantity", required=True, min_value=1)
    @result_float("total", required=True, min_value=0.01)
    async def calculate_aspect(self, params, state, box, connections):
        quantity = params.quantity
        total = round(quantity * params.unit_price, 2)
        return {
            "sku": state["sku"],
            "quantity": quantity,
            "total": total,
        }

    @summary_aspect("Build draft result")
    async def build_summary(self, params, state, box, connections):
        await box.info(
            Channel.business,
            "draft created: sku={%var.sku} quantity={%var.quantity} total={%var.total}",
            sku=state["sku"],
            quantity=state["quantity"],
            total=state["total"],
        )
        return CreateDraftResult(
            sku=state["sku"],
            quantity=state["quantity"],
            total=state["total"],
            message=f"{state['quantity']}x {state['sku']} = ${state['total']}",
        )


async def main() -> None:
    machine = ActionProductMachine(
        log_coordinator=LogCoordinator(loggers=[ConsoleLogger()]),
    )
    result = await machine.run(
        Context(),
        CreateDraftWithEventAction(),
        CreateDraftParams(raw_sku="  sku-42  ", quantity=3, unit_price=19.99),
    )
    print(f"Result: {result.message}")


asyncio.run(main())
