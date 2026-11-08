"""Keep an unloaded field unloaded, even when it has a default.

A list query loaded only the order identifier. The currency has a default and
the code is made from the identifier, but neither was loaded: the partial
instance holds neither, reads neither, dumps neither and runs no code for them.

Run: uv run python examples/step_22_entity/12_partial_defaults.py
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
    """Describe an order whose fields have a default and a default factory."""

    id: str = Field(description="Order identifier")
    currency: str = Field(default="RUB", description="Currency code")
    code: str = Field(default_factory=lambda data: data["id"].upper(), description="Order code made from the identifier")


@meta(description="Stores the shop entities")
@entities(
    OrderCoreEntity,
)
class ShopStorage(BaseStorage):
    """Hold the shop entities."""


order = OrderCoreEntity.partial(id="ord-4")
print("currency loaded:", order.is_field_loaded("currency"))
try:
    print(order.currency)
except FieldNotLoadedError as exc:
    print("reading currency:", type(exc).__name__)
else:
    raise AssertionError("An unloaded currency must not be readable")
print("Python dump:", order.model_dump())
print("JSON dump:", order.model_dump(mode="json"))

nothing = OrderCoreEntity.partial()
print("nothing loaded:", nothing.model_dump())

full = OrderCoreEntity(id="ord-4")
print("full entity:", full.model_dump())
