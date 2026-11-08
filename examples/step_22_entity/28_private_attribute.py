"""
Keep a private attribute on an entity and read it.

A private attribute (PrivateAttr) is not a field: it is never validated and never
dumped. An entity reads it as any Pydantic model does, full or partial; a declared
field a partial entity does not hold still raises FieldNotLoadedError.

Run:
    uv run python examples/step_22_entity/28_private_attribute.py
"""

from pydantic import Field, PrivateAttr

from aoa.action_machine.domain import BaseCoreEntity, FieldNotLoadedError
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entities import entities
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage


class ShopDomain(BaseDomain):
    name = "shop"
    description = "Shop domain"


@entity(description="Customer order", domain=ShopDomain)
class OrderCoreEntity(BaseCoreEntity):
    id: str = Field(description="Order id")
    total: float = Field(default=0.0, description="Total")
    _source: str = PrivateAttr(default="storage")


@meta(description="Stores the shop entities")
@entities(
    OrderCoreEntity,
)
class ShopStorage(BaseStorage):
    """Hold the shop entities."""


order = OrderCoreEntity(id="o1", total=99.5)
print("full order    _source:", order._source)
print("dump          :", order.model_dump())

partial = OrderCoreEntity.partial(id="o2")
print("partial order _source:", partial._source)
try:
    print(partial.total)
except FieldNotLoadedError as error:
    print("partial order total  :", type(error).__name__)
