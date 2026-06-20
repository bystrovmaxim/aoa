"""
01_complex_input.py — Accept complex data in Params (collections, nested objects, JSON by schema)

A request rarely carries just a couple of scalars. AOA accepts complex input the
same way it accepts simple input: Params is a Pydantic model, so every Pydantic
shape works as a field — and the adapters (FastAPI body, MCP inputSchema) surface
that shape automatically. This example shows the variants in one Params:

  - nested object   -> a field whose type is another BaseModel (address)
  - collection      -> list[NestedModel] (lines) and list[str] (tags)
  - JSON by schema  -> a JsonSchemaValue field holding arbitrary JSON validated
                       against a strict JSON Schema (metadata)

The same Params is accepted in-code (model_validate), over HTTP (FastAPI
TestClient, in-process), and described to an agent (MCP inputSchema) — without a
server or LLM.

Tutorial: ../../docs/tutorials/step-16-complex-input_draft.md  ·  topic: complex request input

Run:
    uv run python examples/step_16_complex_input/01_complex_input.py
"""

import asyncio

from fastapi.testclient import TestClient
from pydantic import BaseModel, Field, ValidationError

from aoa.action_machine.adapters.fastapi import FastApiAdapter
from aoa.action_machine.adapters.mcp import McpAdapter
from aoa.action_machine.auth import NoAuthCoordinator, GuestRole
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, JsonSchemaValue
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class OrdersDomain(BaseDomain):
    name = "orders"
    description = "Orders domain"


# ── nested object and collection element are ordinary Pydantic models ────────
class Address(BaseModel):
    city: str = Field(description="City")
    zip: str = Field(description="Postal code")


class LineItem(BaseModel):
    sku: str = Field(description="Product code")
    qty: int = Field(ge=1, description="Quantity")


# ── arbitrary JSON validated against a strict schema ─────────────────────────
OrderMeta = JsonSchemaValue.define(
    name="OrderMeta",
    schema={
        "type": "object",
        "properties": {"source": {"type": "string"}, "ab_test": {"type": "string"}},
        "required": ["source"],
        "additionalProperties": False,
    },
)


class CreateOrderParams(BaseParams):
    customer: str = Field(description="Customer name")
    address: Address = Field(description="Shipping address (nested object)")
    lines: list[LineItem] = Field(description="Order lines (collection of objects)")
    tags: list[str] = Field(default_factory=list, description="Free-form tags (collection of strings)")
    metadata: OrderMeta = Field(description="Arbitrary JSON validated by schema")


class CreateOrderResult(BaseResult):
    order_id: str = Field(description="Created order id")
    item_count: int = Field(description="Number of lines")


@meta(description="Create an order from a structured request", domain=OrdersDomain)
@check_roles(GuestRole)
class CreateOrderAction(BaseAction[CreateOrderParams, CreateOrderResult]):

    @summary_aspect("Create order")
    async def create_summary(self, params, state, box, connections):
        return CreateOrderResult(order_id="ord-1", item_count=len(params.lines))


PAYLOAD = {
    "customer": "Alice",
    "address": {"city": "Berlin", "zip": "10115"},
    "lines": [{"sku": "A1", "qty": 2}, {"sku": "B2", "qty": 1}],
    "tags": ["priority", "gift"],
    "metadata": {"source": "web", "ab_test": "v2"},
}


def main() -> None:
    # 1) In-code: a complex dict validates straight into typed Params.
    print("1) In-code (model_validate):")
    p = CreateOrderParams.model_validate(PAYLOAD)
    print(f"   address -> {type(p.address).__name__}(city={p.address.city!r})")
    print(f"   lines   -> list[{type(p.lines[0]).__name__}] x{len(p.lines)}; tags={p.tags}")
    print(f"   metadata-> {p.metadata} (validated by JSON Schema)")
    try:
        CreateOrderParams.model_validate({**PAYLOAD, "metadata": {"ab_test": "v2"}})  # no required 'source'
    except ValidationError:
        print("   bad metadata -> ValidationError (schema requires 'source')")

    # 2) Over HTTP: the same complex JSON body is accepted by the FastAPI adapter.
    print("\n2) Over HTTP (FastAPI TestClient):")
    app = (
        FastApiAdapter(machine=ActionProductMachine(), auth_coordinator=NoAuthCoordinator(), title="Orders API")
        .post("/orders", CreateOrderAction, tags=["orders"])
        .build()
    )
    r = TestClient(app).post("/orders", json=PAYLOAD)
    print(f"   POST /orders -> {r.status_code} {r.json()}")

    # 3) To an agent: MCP derives the nested inputSchema from Params.
    print("\n3) To an agent (MCP inputSchema):")
    server = (
        McpAdapter(machine=ActionProductMachine(), auth_coordinator=NoAuthCoordinator(), server_name="Orders MCP")
        .tool("orders.create", CreateOrderAction)
        .build()
    )
    tool = asyncio.run(server.list_tools())[0]
    props = tool.inputSchema["properties"]
    print(f"   properties: {list(props)}")
    print(f"   lines -> type={props['lines'].get('type')}; address -> {'$ref' if '$ref' in props['address'] else props['address'].get('type')}")


if __name__ == "__main__":
    main()
