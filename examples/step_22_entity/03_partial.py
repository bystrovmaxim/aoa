"""Read a field that was not loaded.

A list query loaded only the order identifier. The total still belongs to the declared type, but its value is unavailable in this instance.

Run: uv run python examples/step_22_entity/03_partial.py
"""

from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity, FieldNotLoadedError
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entities import entities
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage


class ShopDomain(BaseDomain):
    """Group the shop model declarations."""

    name = "shop"
    description = "Shop model"


@entity(description="Customer order", domain=ShopDomain)
class OrderCoreEntity(BaseCoreEntity):
    """Describe an order independently of its storage."""

    id: str = Field(description="Order identifier")
    total: float = Field(ge=0, description="Order total")


@meta(description="Stores the shop entities")
@entities(
    OrderCoreEntity,
)
class ShopStorage(BaseStorage):
    """Hold the shop entities."""

order = OrderCoreEntity.partial(id="ord-3")
print("total loaded:", order.is_field_loaded("total"))
assert not order.is_field_loaded("total")
try:
    print(order.total)
except FieldNotLoadedError as exc:
    print(type(exc).__name__)
else:
    raise AssertionError("An unloaded total must not be readable")
