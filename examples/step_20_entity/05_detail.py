"""Identify a part within its owner.

Line 3 of order ord-1 is a part of that order. A storage UUID and a quantity do not change this dependence.

Run: uv run python examples/step_20_entity/05_detail.py
"""

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, BaseDetailEntity, CompositeMany, Inverse, Rel
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity


class ShopDomain(BaseDomain):
    """Group the shop model declarations."""

    name = "shop"
    description = "Shop model"


@entity(description="Customer order", domain=ShopDomain)
class OrderCoreEntity(BaseCoreEntity):
    """Own the lines of one order."""

    id: str = Field(description="Order identifier")
    lines: Annotated[CompositeMany["OrderLineDetailEntity"], Inverse(field_name="order")] = Rel(description="Owned lines")


@entity(description="One line of an order", domain=ShopDomain)
class OrderLineDetailEntity(BaseDetailEntity):
    """Identify a part within its particular order."""

    id: str = Field(description="Storage identifier of the line")
    number: int = Field(description="Line number within the order")
    quantity: int = Field(gt=0, description="Ordered quantity")
    order: Annotated[AssociationOne[OrderCoreEntity], Inverse(OrderCoreEntity, "lines")] = Rel(description="Owning order")


OrderCoreEntity.model_rebuild()

line = OrderLineDetailEntity(
    id="line-uuid", number=3, quantity=2,
    order=AssociationOne[OrderCoreEntity](id="ord-1"),
)
assert (line.order.id, line.number) == ("ord-1", 3)
print("domain identity:", line.order.id, line.number)
print("storage key:", line.get_primary_key())
