"""
05_mcp_tool.py — publish the same Action as an MCP tool.

Run from repository root:
    uv run python packages/aoa-action-machine/examples/05_mcp_tool.py

Requires:
    pip install "aoa-action-machine[mcp]"
"""

import asyncio

from pydantic import Field

from aoa.action_machine.auth import GuestRole, NoAuthCoordinator
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.checkers import result_float, result_int, result_string
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.mcp import McpAdapter


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


@meta(description="Create order draft", domain=OrderDomain)
@check_roles(GuestRole)
class CreateDraftAction(BaseAction[CreateDraftParams, CreateDraftResult]):

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
        return {"sku": state["sku"], "quantity": quantity, "total": total}

    @summary_aspect("Build draft result")
    async def build_summary(self, params, state, box, connections):
        return CreateDraftResult(
            sku=state["sku"],
            quantity=state["quantity"],
            total=state["total"],
            message=f"{state['quantity']}x {state['sku']} = ${state['total']}",
        )


def build_server():
    machine = ActionProductMachine()
    return (
        McpAdapter(machine=machine, auth_coordinator=NoAuthCoordinator(context=Context()), server_name="Orders MCP")
        .tool("orders.create_draft", CreateDraftAction)
        .build()
    )


def envelope(result) -> str:
    content = getattr(result, "content", result)
    block = content[0] if isinstance(content, (list, tuple)) else content
    text = getattr(block, "text", str(block))
    return f"isError={getattr(result, 'isError', None)}  {text}"


async def main() -> None:
    server = build_server()

    tools = await server.list_tools()
    print("Tools exposed to the agent:")
    for tool in tools:
        print(f"  {tool.name} required={tool.inputSchema.get('required')}")

    result = await server.call_tool(
        "orders.create_draft",
        {"raw_sku": "  sku-42  ", "quantity": 3, "unit_price": 19.99},
    )
    print("Call:")
    print(f"  orders.create_draft -> {envelope(result)}")


if __name__ == "__main__":
    asyncio.run(main())
