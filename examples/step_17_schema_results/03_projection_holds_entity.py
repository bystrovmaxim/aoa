"""Return and receive a part of an entity through a projection.

A projection, OrderCoreEntity.schema(schema={...}), holds the entity itself: a
partial OrderCoreEntity with exactly the projection's fields. It takes the full
entity, a partial one or a dict, and checks each value by the projection's
schema and by the entity's own field types. A field typed by the entity itself
takes a full entity; a part of one goes through a projection.

Run: uv run python examples/step_17_schema_results/03_projection_holds_entity.py
"""

from pydantic import Field, ValidationError

from aoa.action_machine.domain import BaseCoreEntity, FieldNotLoadedError
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entities import entities
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseParams, BaseResult
from aoa.action_machine.resources.base_storage import BaseStorage


class ShopDomain(BaseDomain):
    """Group the shop model declarations."""

    name = "shop"
    description = "Shop model"


@entity(description="Customer order", domain=ShopDomain)
class OrderCoreEntity(BaseCoreEntity):
    """An order with a field the projection leaves out."""

    id: str = Field(description="Order identifier")
    status: str = Field(description="Order status")
    total: float = Field(ge=0, description="Order total")
    customer_email: str = Field(description="Customer email, never sent with the summary")


@meta(description="Stores the shop entities")
@entities(
    OrderCoreEntity,
)
class ShopStorage(BaseStorage):
    """Hold the shop entities."""


ORDER_WIRE = {
    "type": "object",
    "properties": {"id": {"type": "string"}, "status": {"type": "string"}, "total": {"type": "number"}},
    "required": ["id", "status", "total"],
    "additionalProperties": False,
}


class OrderSummaryResult(BaseResult):
    """Return the summary of an order."""

    order: OrderCoreEntity.schema(schema=ORDER_WIRE) = Field(description="Order summary")  # type: ignore[valid-type]


class OrderSummaryParams(BaseParams):
    """Receive the summary of an order."""

    order: OrderCoreEntity.schema(schema=ORDER_WIRE) = Field(description="Order summary")  # type: ignore[valid-type]


class OrderResult(BaseResult):
    """Return a whole order."""

    order: OrderCoreEntity = Field(description="Order")


order = OrderCoreEntity(id="ord-1", status="paid", total=99.5, customer_email="ann@example.com")

print("1) Return the entity through the projection")
summary = OrderSummaryResult(order=order)
print("   JSON:", summary.model_dump(mode="json"))
print("   held:", type(summary.order).__name__, "| status:", summary.order.status)
try:
    print(summary.order.customer_email)
except FieldNotLoadedError as exc:
    print("   customer_email ->", type(exc).__name__)
else:
    raise AssertionError("A field outside the projection is not held")

print("2) Receive the projection as an entity")
params = OrderSummaryParams.model_validate({"order": {"id": "ord-2", "status": "new", "total": 10}})
print("   held:", type(params.order).__name__, "| id:", params.order.id, "| by key:", params.order["id"])
try:
    OrderSummaryParams.model_validate({"order": {"id": "ord-3", "status": "new", "total": -1}})
except ValidationError as exc:
    print("   total -1 ->", exc.errors()[0]["msg"])
else:
    raise AssertionError("The entity's own field type refuses a negative total")

print("3) A projection names only fields of its entity")
try:
    OrderCoreEntity.schema(schema={"type": "object", "properties": {"secret": {"type": "string"}}})
except ValueError as exc:
    print("   ValueError:", exc)
else:
    raise AssertionError("secret is not a field of the order")

print("4) A field typed by the entity takes a full one")
try:
    OrderResult(order=OrderCoreEntity.partial(id="ord-4"))
except ValidationError as exc:
    print("   ValidationError:", exc.errors()[0]["msg"])
else:
    raise AssertionError("A partial order is not a whole one")
