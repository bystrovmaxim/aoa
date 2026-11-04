"""Send an entity with relations as JSON and read it back.

An order points at its customer and holds its lines. In JSON a One relation is
its id, with the entity when it is loaded; a Many relation is its ids, with the
entities when they are loaded. The same forms are read back from JSON and from a
dict, and each id takes the type of the target's id field.

Run: uv run python examples/step_24_relations/10_relation_json_form.py
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from pydantic import Field, ValidationError

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, BaseDetailEntity, CompositeMany, NoInverse
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity


class ShopDomain(BaseDomain):
    """Group the shop model declarations."""

    name = "shop"
    description = "Shop model"


@entity(description="Customer", domain=ShopDomain)
class CustomerCoreEntity(BaseCoreEntity):
    """A customer identified by a UUID."""

    id: UUID = Field(description="Customer identifier")
    name: str = Field(description="Customer name")


@entity(description="Order line", domain=ShopDomain)
class LineDetailEntity(BaseDetailEntity):
    """One line of an order."""

    id: str = Field(description="Line identifier")
    qty: int = Field(description="Quantity")


@entity(description="Customer order", domain=ShopDomain)
class OrderCoreEntity(BaseCoreEntity):
    """An order with its customer and its lines."""

    id: str = Field(description="Order identifier")
    customer: Annotated[AssociationOne[CustomerCoreEntity], NoInverse()] = Field(description="Customer")
    lines: Annotated[CompositeMany[LineDetailEntity], NoInverse()] = Field(description="Lines")


CUSTOMER_ID = "00000000-0000-0000-0000-000000000001"

print("1) Ids only")
order = OrderCoreEntity(
    id="ord-1",
    customer=AssociationOne[CustomerCoreEntity](id=CUSTOMER_ID),
    lines=CompositeMany[LineDetailEntity](ids=("l1", "l2")),
)
print("   JSON:", order.model_dump(mode="json"))
print("   customer id type:", type(order.customer.id).__name__)

print("2) Loaded")
loaded = OrderCoreEntity(
    id="ord-2",
    customer=AssociationOne[CustomerCoreEntity](
        id=CUSTOMER_ID, entity=CustomerCoreEntity.partial(id=UUID(CUSTOMER_ID), name="Alice")
    ),
    lines=CompositeMany[LineDetailEntity](ids=("l1",), entities=(LineDetailEntity(id="l1", qty=2),)),
)
print("   JSON:", loaded.model_dump(mode="json"))

print("3) Loaded with zero lines, and not loaded")
none_loaded = CompositeMany[LineDetailEntity](ids=(), entities=(), entities_loaded=True)
print("   zero lines:", order.model_copy(update={"lines": none_loaded}).model_dump(mode="json")["lines"])
print("   not loaded:", order.model_copy(update={"lines": CompositeMany[LineDetailEntity](ids=())}).model_dump(mode="json")["lines"])

print("4) Read back")
back = OrderCoreEntity.model_validate_json(loaded.model_dump_json())
print("   equal:", back == loaded, "| customer:", back.customer.name, "| lines loaded:", back.lines.is_loaded)
from_dict = OrderCoreEntity.model_validate({"id": "ord-3", "customer": {"id": CUSTOMER_ID}, "lines": {"ids": ["l9"]}})
print("   from a dict:", from_dict.customer, from_dict.lines)

print("5) An id of the wrong type")
try:
    OrderCoreEntity.model_validate({"id": "ord-4", "customer": {"id": "abc"}, "lines": {"ids": []}})
except ValidationError as exc:
    error = exc.errors()[0]
    print("   ValidationError at", error["loc"], "-", error["type"])
else:
    raise AssertionError("A customer id must be a UUID")
