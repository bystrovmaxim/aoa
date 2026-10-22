"""Declare an independent domain object.

An order has its own identity. Changing its total does not turn it into a different order. Choose Core because of that meaning, then use the matching class-name suffix.

Run: uv run python examples/step_20_entity/01_entity.py
"""

from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity, build
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity


class ShopDomain(BaseDomain):
    """Group the shop model declarations."""

    name = "shop"
    description = "Shop model"


@entity(description="Customer order", domain=ShopDomain)
class OrderCoreEntity(BaseCoreEntity):
    """Describe an order independently of its storage."""

    id: str = Field(description="Order identifier")
    total: float = Field(ge=0, description="Order total")

order = build({"id": "ord-1", "total": 1500.0}, OrderCoreEntity)
assert order.id == "ord-1"
assert order.total == 1500.0
print(type(order).__name__)
print(order.id, order.total)
