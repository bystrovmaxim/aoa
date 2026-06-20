"""
04_fastapi_api.py — publish the same Action as a FastAPI endpoint.

Run from repository root:
    uv run python packages/aoa-action-machine/examples/04_fastapi_api.py

Requires:
    pip install "aoa-action-machine[fastapi]"
"""

from fastapi.testclient import TestClient
from pydantic import Field

from aoa.action_machine.adapters.fastapi import FastApiAdapter
from aoa.action_machine.auth import NoAuthCoordinator, GuestRole
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.checkers import result_float, result_int, result_string
from aoa.action_machine.intents.meta import meta
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


def build_app():
    machine = ActionProductMachine()
    return (
        FastApiAdapter(machine=machine, auth_coordinator=NoAuthCoordinator(), title="Orders API")
        .post("/drafts", CreateDraftAction, tags=["orders"])
        .build()
    )


def main() -> None:
    client = TestClient(build_app())

    response = client.post(
        "/drafts",
        json={"raw_sku": "  sku-42  ", "quantity": 3, "unit_price": 19.99},
    )
    print(f"POST /drafts -> {response.status_code} {response.json()}")

    schema = client.get("/openapi.json").json()
    business_paths = [path for path in schema["paths"] if path != "/health"]
    print(f"OpenAPI title: {schema['info']['title']}")
    print(f"Registered paths: {business_paths}")


if __name__ == "__main__":
    main()
