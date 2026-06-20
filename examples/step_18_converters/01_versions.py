"""
01_versions.py — Schema converters: two API versions, one Action

The external schema does not always match the operation's contract: a new API
version ships, the frontend renames a field, a partner needs cents instead of a
float. Changing the Action is unnecessary — the translation lives at the adapter
boundary:

  - request_model  + params_mapper(body)   -> Params   (incoming request -> contract)
  - response_model + response_mapper(result) -> response (contract -> outgoing shape)

Note: the arguments are `params_mapper` / `response_mapper` (the README's older
`params_converter` / `result_converter` names are out of date).

A guard runs at registration: if request_model/response_model differs from the
action's Params/Result and the matching mapper is missing, .post(...) raises
ValueError immediately.

This example uses FastAPI's in-process TestClient; the same arguments exist on
McpAdapter.tool(...).

Tutorial: ../../docs/tutorials/step-18-converters_draft.md  ·  topic: schema converters / API versions

Run:
    uv run python examples/step_18_converters/01_versions.py
"""

from pydantic import BaseModel, Field
from fastapi.testclient import TestClient

from aoa.action_machine.adapters.fastapi import FastApiAdapter
from aoa.action_machine.auth import NoAuthCoordinator, GuestRole
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class OrdersDomain(BaseDomain):
    name = "orders"
    description = "Orders domain"


# ── The operation: one contract, never changed across API versions ──────────
class CreateOrderParams(BaseParams):
    customer: str = Field(description="Customer name")
    amount: float = Field(gt=0, description="Order amount")


class CreateOrderResult(BaseResult):
    order_id: str = Field(description="Created order id")
    total: float = Field(description="Order total")


@meta(description="Create an order", domain=OrdersDomain)
@check_roles(GuestRole)
class CreateOrderAction(BaseAction[CreateOrderParams, CreateOrderResult]):

    @summary_aspect("Create order")
    async def create_summary(self, params, state, box, connections):
        return CreateOrderResult(order_id="ord-1", total=params.amount)


# ── v2 external schema: renamed fields, amount in cents ─────────────────────
class OrderV2Request(BaseModel):
    client: str = Field(description="Customer (v2 name)")
    sum_cents: int = Field(gt=0, description="Amount in cents (v2 unit)")


class OrderV2Response(BaseModel):
    id: str = Field(description="Order id (v2 name)")
    total_cents: int = Field(description="Total in cents (v2 unit)")


def build_app():
    return (
        FastApiAdapter(machine=ActionProductMachine(), auth_coordinator=NoAuthCoordinator(), title="Orders API")
        # v1 — native contract: Params and Result go through as-is, no converter
        .post("/api/v1/orders", CreateOrderAction, tags=["orders"])
        # v2 — different schema outside, same operation inside
        .post(
            "/api/v2/orders",
            CreateOrderAction,
            request_model=OrderV2Request,
            response_model=OrderV2Response,
            params_mapper=lambda body: CreateOrderParams(customer=body.client, amount=body.sum_cents / 100),
            response_mapper=lambda r: OrderV2Response(id=r.order_id, total_cents=round(r.total * 100)),
            tags=["orders"],
        )
        .build()
    )


def main() -> None:
    client = TestClient(build_app())

    print("v1 (native contract):")
    r = client.post("/api/v1/orders", json={"customer": "Alice", "amount": 99.5})
    print(f"  POST /api/v1/orders {{customer, amount}}  -> {r.status_code} {r.json()}")

    print("\nv2 (external schema, same Action):")
    r = client.post("/api/v2/orders", json={"client": "Bob", "sum_cents": 4200})
    print(f"  POST /api/v2/orders {{client, sum_cents}} -> {r.status_code} {r.json()}")

    print("\nRegistration guard (differing model without its mapper):")
    try:
        FastApiAdapter(machine=ActionProductMachine(), auth_coordinator=NoAuthCoordinator()).post(
            "/bad", CreateOrderAction, response_model=OrderV2Response,  # no response_mapper
        )
    except ValueError as exc:
        print(f"  .post(response_model=...) without response_mapper -> ValueError: {exc}")


if __name__ == "__main__":
    main()
