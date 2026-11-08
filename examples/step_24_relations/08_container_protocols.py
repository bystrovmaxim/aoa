"""A relation container is never its entity.

An order holds its customer through an AssociationOne. The container passes
ordinary names to the loaded customer, so order.customer.name reads the name,
but it answers Python's and Pydantic's own questions itself: a Python dump keeps
it, a JSON dump writes its form, a copy and a pickle give a container back,
loaded or not.

Run: uv run python examples/step_24_relations/08_container_protocols.py
"""

from __future__ import annotations

import copy
import pickle
from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationMany, AssociationOne, BaseCoreEntity, NoInverse
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entities import entities
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage


class ShopDomain(BaseDomain):
    """Group the shop model declarations."""

    name = "shop"
    description = "Shop model"


@entity(description="Customer", domain=ShopDomain)
class CustomerCoreEntity(BaseCoreEntity):
    """Describe a customer."""

    id: str = Field(description="Customer identifier")
    name: str = Field(description="Customer name")


@entity(description="Customer order", domain=ShopDomain)
class OrderCoreEntity(BaseCoreEntity):
    """Describe an order that points at its customer."""

    id: str = Field(description="Order identifier")
    customer: Annotated[AssociationOne[CustomerCoreEntity], NoInverse()] = Field(description="Customer")


@meta(description="Stores the shop entities")
@entities(
    CustomerCoreEntity,
    OrderCoreEntity,
)
class ShopStorage(BaseStorage):
    """Hold the shop entities."""


customer = CustomerCoreEntity(id="cust-1", name="Alice")
order = OrderCoreEntity(id="ord-1", customer=AssociationOne[CustomerCoreEntity](id="cust-1", entity=customer))

print("1) Names")
print("   order.customer.name:", order.customer.name)
try:
    _ = order.customer.__pydantic_serializer__
except AttributeError:
    print("   order.customer.__pydantic_serializer__ -> AttributeError")
else:
    raise AssertionError("A protocol name must not reach the customer")

print("2) Dumps")
print("   Python dump keeps the container:", order.model_dump()["customer"])
print("   JSON dump writes its form:", order.model_dump(mode="json")["customer"])

print("3) Copies")
deep = copy.deepcopy(order.customer)
print("   deepcopy:", deep, "| customer copied:", deep.entity == customer and deep.entity is not customer)
print("   model_copy(deep=True).customer:", order.model_copy(deep=True).customer)
print("   copy.copy is equal:", copy.copy(order.customer) == order.customer)

print("4) Pickle")
unloaded = AssociationOne[CustomerCoreEntity](id="cust-9")
back = pickle.loads(pickle.dumps(unloaded))
print("   unloaded one:", back, "| equal:", back == unloaded)
many = AssociationMany[CustomerCoreEntity](ids=("cust-1", "cust-2"))
print("   unloaded many:", pickle.loads(pickle.dumps(many)))
try:
    back.extra = 1
except AttributeError as exc:
    print("   still frozen:", exc)
