"""Map a storage row into the same domain type.

The database calls its columns order_id and amount. The domain calls them id and total. A mapper translates that storage vocabulary at the boundary.

Run: uv run python examples/step_20_entity/02_mapping.py
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

row = {"order_id": "ord-2", "amount": 99.5}
order = build(row, OrderCoreEntity, lambda fields, row: {
    fields.id: row["order_id"],
    fields.total: row["amount"],
})
assert order.id == "ord-2" and order.total == 99.5
print(order.id, order.total)
