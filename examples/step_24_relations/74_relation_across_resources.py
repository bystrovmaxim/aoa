"""Keep every relation inside one resource.

A relation is a join or a foreign key, and a join exists only inside one database. When two
entities are stored by different resources, the model refuses to relate them; when they share
a resource, the same field is accepted.

Run: uv run python examples/step_24_relations/74_relation_across_resources.py
"""

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, EntityResourceError, NoInverse
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class StoreDomain(BaseDomain):
    """Group the shop model declarations."""

    name = "store"
    description = "Store"


@meta(description="Primary relational store", domain=StoreDomain)
class StorefrontDatabase(BaseStorage):
    """The database the orders live in."""


@meta(description="Support desk store", domain=StoreDomain)
class SupportDatabase(BaseStorage):
    """The database the support tickets live in."""


@entity(description="Customer order", resource=StorefrontDatabase)
class SalesOrderCoreEntity(BaseCoreEntity):
    """A customer's order."""

    id: str = Field(description="Order identifier")


@entity(description="Support ticket", resource=SupportDatabase)
class SupportTicketCoreEntity(BaseCoreEntity):
    """A ticket that tries to point at an order in another database."""

    id: str = Field(description="Ticket identifier")
    order: Annotated[AssociationOne[SalesOrderCoreEntity], NoInverse()] = Field(description="Order")


@entity(description="Order note", resource=StorefrontDatabase)
class OrderNoteCoreEntity(BaseCoreEntity):
    """A note stored beside the order, so it may point at it."""

    id: str = Field(description="Note identifier")
    order: Annotated[AssociationOne[SalesOrderCoreEntity], NoInverse()] = Field(description="Order")


SupportTicketCoreEntity.model_rebuild()
OrderNoteCoreEntity.model_rebuild()

# Run the case.
try:
    ActionProductMachine(loggers=[])
except EntityResourceError as error:
    print(type(error).__name__ + ":", error)
else:
    raise AssertionError("A relation across resources was accepted")
