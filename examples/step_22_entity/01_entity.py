"""Declare an independent domain object.

An order has its own identity. Changing its total does not turn it into a different order. Choose Core because of that meaning, then use the matching class-name suffix.

Run: uv run python examples/step_22_entity/01_entity.py
"""

from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity, build
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage
from aoa.action_machine.resources import InMemoryDataSource


class ShopDomain(BaseDomain):
    """Group the shop model declarations."""

    name = "shop"
    description = "Shop model"


@meta(description="Where ShopStorage keeps its rows")
class ShopDataSource(InMemoryDataSource):
    """The store ShopStorage works with."""


@meta(description="Stores the shop entities", domain=ShopDomain)
class ShopStorage(BaseStorage[ShopDataSource]):
    """Hold the shop entities."""


@entity(description="Customer order", resource=ShopStorage)
class OrderCoreEntity(BaseCoreEntity):
    """Describe an order independently of its storage."""

    id: str = Field(description="Order identifier")
    total: float = Field(ge=0, description="Order total")

order = build({"id": "ord-1", "total": 1500.0}, OrderCoreEntity)
assert order.id == "ord-1"
assert order.total == 1500.0
print(type(order).__name__)
print(order.id, order.total)
