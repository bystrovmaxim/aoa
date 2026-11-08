"""What ``@entities`` and a resource's ``@meta`` refuse.

Every class ``@entities`` lists must be an ``@entity``, and it is listed once. Only a resource
declares ``@entities``. A resource's ``@meta`` takes no domain. Each refusal happens when the
class is declared and names what is wrong.

Run: uv run python examples/step_21_resource/09_entities_refusals.py
"""

from pydantic import BaseModel, Field

from aoa.action_machine.domain import BaseCoreEntity
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.exceptions import DecoratorArgumentTypeError, EntitiesDecoratorError
from aoa.action_machine.intents.entities import entities
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseStorage


class StoreDomain(BaseDomain):
    """Group the shop's orders."""

    name = "store"
    description = "Store"


@entity(description="Customer order", domain=StoreDomain)
class OrderCoreEntity(BaseCoreEntity):
    """An order of the store."""

    id: str = Field(description="Order identifier")


class OrderRow(BaseModel):
    """A plain model: not an entity of the domain."""

    id: str


class ReportBuilder:
    """A plain class: not a resource."""


# Run the case.
try:

    @entities(OrderRow)
    class RowsStorage(BaseStorage):
        """Lists a plain model."""

except EntitiesDecoratorError as error:
    print("not an entity:", error)

try:

    @entities(OrderCoreEntity, OrderCoreEntity)
    class TwiceStorage(BaseStorage):
        """Lists one entity twice."""

except EntitiesDecoratorError as error:
    print("listed twice:", error)

try:
    entities(OrderCoreEntity)(ReportBuilder)
except EntitiesDecoratorError as error:
    print("not a resource:", error)

try:

    @meta(description="The shop database", domain=StoreDomain)
    class ShopDatabaseStorage(BaseStorage):
        """Names a domain, as a resource no longer does."""

except DecoratorArgumentTypeError as error:
    print("a resource with a domain:", error)
