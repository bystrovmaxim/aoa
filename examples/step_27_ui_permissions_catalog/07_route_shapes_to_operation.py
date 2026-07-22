"""
07_route_shapes_to_operation.py — every route shape becomes one operation string

An operation is nothing more than the HTTP method plus the path TEMPLATE, joined
by a single space: f"{method} {path}". This example registers four deliberately
different route shapes — a plain path, a nested path, a dashed path, and a path
with an {order_id} parameter — then reads back the operation each one yields in
GET /client-manifest.json. The path parameter stays literally "{order_id}" in the
operation; it is a template, never a substituted value. This is the server half
of the client "route-shapes map": chapter 5 builds api[method]["/path"] from
exactly these strings.

Tutorial: ../../docs/tutorials/step-27-ui-permissions-resolve_draft.md

Run:
    uv run python examples/step_27_ui_permissions_catalog/07_route_shapes_to_operation.py
"""

from fastapi.testclient import TestClient
from pydantic import Field

from aoa.action_machine.auth.auth_coordinator import NoAuthCoordinator
from aoa.action_machine.auth.guest_role import GuestRole
from aoa.action_machine.context.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.fastapi.adapter import FastApiAdapter


class StoreDomain(BaseDomain):
    name = "store"
    description = "Store domain"


class EmptyParams(BaseParams):
    pass


class NewOrderParams(BaseParams):
    item: str = Field(description="Item to order")


class OrderIdParams(BaseParams):
    order_id: int = Field(description="Order identifier")


class OrderResult(BaseResult):
    status: str = Field(description="Order status")


class PingResult(BaseResult):
    message: str = Field(description="Liveness message")


@meta(description="Create an order", domain=StoreDomain)
@check_roles(GuestRole)
class CreateOrderAction(BaseAction[NewOrderParams, OrderResult]):

    @summary_aspect("Create the order")
    async def create_summary(self, params, state, box, connections):
        return OrderResult(status="created")


@meta(description="Liveness probe", domain=StoreDomain)
@check_roles(GuestRole)
class PingAction(BaseAction[EmptyParams, PingResult]):

    @summary_aspect("Answer the probe")
    async def ping_summary(self, params, state, box, connections):
        return PingResult(message="pong")


@meta(description="Cancel an order", domain=StoreDomain)
@check_roles(GuestRole)
class CancelOrderAction(BaseAction[OrderIdParams, OrderResult]):

    @summary_aspect("Cancel the order")
    async def cancel_summary(self, params, state, box, connections):
        return OrderResult(status="cancelled")


@meta(description="Fetch one order by id", domain=StoreDomain)
@check_roles(GuestRole)
class GetOrderAction(BaseAction[OrderIdParams, OrderResult]):

    @summary_aspect("Return the order")
    async def get_summary(self, params, state, box, connections):
        return OrderResult(status="open")


def main() -> None:
    # NoAuthCoordinator(context=Context()) resolves a real anonymous Context, so the
    # catalog answers 200 — the manifest itself is role-independent anyway.
    adapter = FastApiAdapter(
        machine=ActionProductMachine(loggers=[]),
        auth_coordinator=NoAuthCoordinator(context=Context()),
    )

    # Four deliberately different route shapes — one projection rule for all of them.
    adapter.post("/orders", CreateOrderAction)            # plain path
    adapter.get("/b/c/ping", PingAction)                  # nested path
    adapter.post("/cancel-order", CancelOrderAction)      # a dash in the path
    adapter.get("/orders/{order_id}", GetOrderAction)     # a path parameter

    client = TestClient(adapter.build())
    manifest = client.get("/client-manifest.json").json()

    # operation is literally "{method} {path}", one per registered route, in
    # registration order (bespoke routes like /health are never listed).
    operations = [endpoint["operation"] for endpoint in manifest["endpoints"]]
    print("operations, in registration order:")
    for operation in operations:
        print(f"    {operation}")

    assert operations == [
        "POST /orders",
        "GET /b/c/ping",
        "POST /cancel-order",
        "GET /orders/{order_id}",
    ]

    # The path parameter survives as a TEMPLATE — "{order_id}", not a value.
    get_order = next(e for e in manifest["endpoints"] if e["name"] == "GetOrderAction")
    print()
    print(f"route split : {get_order['route']}")
    print(f"operation   : {get_order['operation']}")
    assert get_order["route"] == {"method": "GET", "path": "/orders/{order_id}"}
    assert get_order["operation"] == "GET /orders/{order_id}"  # {order_id} stays literal
    assert "{order_id}" in get_order["operation"]

    # operation == "{method} {path}" holds for every entry, no exceptions — this is
    # the exact rule chapter 5's client uses to key api[method]["/path"].
    for endpoint in manifest["endpoints"]:
        assert endpoint["operation"] == f"{endpoint['route']['method']} {endpoint['route']['path']}"


main()
