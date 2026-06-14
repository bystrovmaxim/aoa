"""
Domain model example: Entity, relations, Lifecycle, Resource, Action.

Demonstrates:
  - BaseEntity with fields and lifecycle
  - AssociationOne/Many with Inverse (bidirectional, checked at startup)
  - CompositeMany — order lines owned by an order
  - NoInverse — cross-domain reference (product from catalog)
  - PostgresResource as transport layer
  - OrderResource as domain-level API wrapping transport
  - CreateOrderAction using OrderResource — business logic separate from transport

Run:
    uv run python examples/08_domain_model.py
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Annotated

from pydantic import Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain import (
    AssociationMany,
    AssociationOne,
    BaseEntity,
    CompositeMany,
    Inverse,
    Lifecycle,
    Rel,
    build,
)
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine

# ---------------------------------------------------------------------------
# Domain
# ---------------------------------------------------------------------------


class StoreDomain(BaseDomain):
    name = "store"
    description = "E-commerce store domain"


# ---------------------------------------------------------------------------
# Lifecycles
# ---------------------------------------------------------------------------


class OrderLifecycle(Lifecycle):
    _template = (
        Lifecycle()
        .state("new", "New").to("confirmed", "cancelled").initial()
        .state("confirmed", "Confirmed").to("shipped", "cancelled").intermediate()
        .state("shipped", "Shipped").to("delivered").intermediate()
        .state("delivered", "Delivered").final()
        .state("cancelled", "Cancelled").final()
    )


class OrderLineLifecycle(Lifecycle):
    _template = (
        Lifecycle()
        .state("pending", "Pending").to("reserved", "cancelled").initial()
        .state("reserved", "Reserved").to("shipped").intermediate()
        .state("shipped", "Shipped").to("delivered").intermediate()
        .state("delivered", "Delivered").final()
        .state("cancelled", "Cancelled").final()
    )


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------

# Forward-reference pattern: all three classes are declared in one module
# so Inverse() can reference partner types at class-body time.


@entity(description="Registered customer account", domain=StoreDomain)
class CustomerEntity(BaseEntity):
    id: str = Field(description="Customer identifier")
    name: str = Field(description="Display name")
    email: str = Field(description="Contact email")

    # association many — customer exists independently of any order
    orders: Annotated[
        AssociationMany[OrderEntity],
        Inverse(OrderEntity, "customer"),
    ] = Rel(description="Orders placed by this customer")


@entity(description="Customer order", domain=StoreDomain)
class OrderEntity(BaseEntity):
    id: str = Field(description="Order identifier")
    total: float = Field(description="Order total", ge=0)
    currency: str = Field(description="Currency code", default="RUB")
    lifecycle: OrderLifecycle = Field(description="Order lifecycle state")

    # association one-to-one — order and customer exist independently
    customer: Annotated[
        AssociationOne[CustomerEntity],
        Inverse(CustomerEntity, "orders"),
    ] = Rel(description="Customer who placed the order")

    # composition one-to-many — order lines cannot exist without this order
    lines: Annotated[
        CompositeMany[OrderLineEntity],
        Inverse(OrderLineEntity, "order"),
    ] = Rel(description="Line items of the order")


@entity(description="Single line item within an order", domain=StoreDomain)
class OrderLineEntity(BaseEntity):
    id: str = Field(description="Line item identifier")
    product_id: str = Field(description="Product identifier")
    product_name: str = Field(description="Product display name")
    quantity: int = Field(description="Quantity ordered", ge=1)
    unit_price: float = Field(description="Unit price at the time of order", ge=0)
    lifecycle: OrderLineLifecycle = Field(description="Line item lifecycle state")

    # association back to parent order
    order: Annotated[
        AssociationOne[OrderEntity],
        Inverse(OrderEntity, "lines"),
    ] = Rel(description="Parent order")


# Rebuild forward references after all three classes are defined
CustomerEntity.model_rebuild()
OrderEntity.model_rebuild()
OrderLineEntity.model_rebuild()


# ---------------------------------------------------------------------------
# Resource — transport layer, no business logic
# ---------------------------------------------------------------------------


class OrderResource(BaseResource):
    """In-memory stub; production version wraps PostgresResource."""

    def __init__(self) -> None:
        self._orders: dict[str, dict] = {}
        self._customers: dict[str, dict] = {
            "cust-001": {"id": "cust-001", "name": "Alice", "email": "alice@example.com"},
        }

    async def load_customer(self, customer_id: str) -> CustomerEntity:
        row = self._customers.get(customer_id)
        if row is None:
            raise KeyError(f"Customer {customer_id!r} not found")
        return build(row, CustomerEntity)

    async def save_order(
        self,
        order_id: str,
        customer_id: str,
        total: float,
        currency: str,
    ) -> None:
        self._orders[order_id] = {
            "id": order_id,
            "customer_id": customer_id,
            "total": total,
            "currency": currency,
            "status": "new",
        }


# ---------------------------------------------------------------------------
# Params & Result
# ---------------------------------------------------------------------------


class CreateOrderParams(BaseParams):
    customer_id: str = Field(description="Customer placing the order")
    items: list[dict] = Field(description="Line items: [{product_id, name, qty, price}]")
    currency: str = Field(description="Currency code", default="RUB")


class CreateOrderResult(BaseResult):
    order_id: str = Field(description="Created order identifier")
    total: float = Field(description="Order total")
    customer_name: str = Field(description="Customer display name")


# ---------------------------------------------------------------------------
# Action — business logic only
# ---------------------------------------------------------------------------


@meta(description="Create a new customer order", domain=StoreDomain)
@check_roles(NoneRole)
class CreateOrderAction(BaseAction[CreateOrderParams, CreateOrderResult]):

    @regular_aspect("Load and validate customer")
    async def load_customer_aspect(self, params, state, box, connections):
        repo = box.resolve(OrderResource)
        state.customer = await repo.load_customer(params.customer_id)

    @regular_aspect("Calculate order total")
    async def calculate_total_aspect(self, params, state, box, connections):
        state.total = sum(
            item["qty"] * item["price"] for item in params.items
        )

    @regular_aspect("Persist order")
    async def persist_order_aspect(self, params, state, box, connections):
        repo = box.resolve(OrderResource)
        state.order_id = f"ord-{uuid.uuid4().hex[:8]}"
        await repo.save_order(
            order_id=state.order_id,
            customer_id=params.customer_id,
            total=state.total,
            currency=params.currency,
        )

    @summary_aspect("Build result")
    async def final_summary(self, params, state, box, connections):
        return CreateOrderResult(
            order_id=state.order_id,
            total=state.total,
            customer_name=state.customer.name,
        )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


async def main() -> None:
    order_resource = OrderResource()

    machine = ActionProductMachine(
        resources={OrderResource: order_resource},
    )

    result = await machine.run(
        Context(),
        CreateOrderAction(),
        CreateOrderParams(
            customer_id="cust-001",
            items=[
                {"product_id": "sku-1", "name": "Wireless Headphones", "qty": 1, "price": 8990.0},
                {"product_id": "sku-2", "name": "USB-C Cable", "qty": 2, "price": 490.0},
            ],
        ),
    )

    print(f"order_id:      {result.order_id}")
    print(f"total:         {result.total} RUB")
    print(f"customer_name: {result.customer_name}")


asyncio.run(main())
