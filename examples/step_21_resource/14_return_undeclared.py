"""A resource that lists no entity answers with none.

A resource without ``@entities``, or with an empty one, refuses every entity it returns, and
the refusal says it declares no ``@entities``. Methods whose names start with ``_`` are its own
business and are not checked; neither are class methods, static methods and properties.

Run: uv run python examples/step_21_resource/14_return_undeclared.py
"""

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import (
    AssociationMany,
    AssociationOne,
    BaseCoreEntity,
    BaseEnumEntity,
    CompositeOne,
    NoInverse,
    value,
)
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.exceptions import ResourceEntitiesError
from aoa.action_machine.intents.entities import entities
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseStorage


class ShopDomain(BaseDomain):
    """Group the shop's declarations."""

    name = "shop"
    description = "Shop"


@entity(description="A customer of the shop", domain=ShopDomain)
class CustomerCoreEntity(BaseCoreEntity):
    """A customer; the shop database keeps it."""

    id: str = Field(description="Customer identifier")


@entity(description="A product of the catalog", domain=ShopDomain)
class ProductCoreEntity(BaseCoreEntity):
    """A product; it lies in the catalog database, not in the shop database."""

    id: str = Field(description="Product identifier")
    name: str = Field(description="Product name")


@entity(description="A currency", domain=ShopDomain)
class CurrencyEnumEntity(BaseEnumEntity):
    """A dictionary member: it belongs to the model, not to a database."""

    EUR = value(code="eur", display_name="Euro")


@entity(description="A line of an order", domain=ShopDomain)
class OrderLineCoreEntity(BaseCoreEntity):
    """A line; its product relation leads out of the shop database."""

    id: str = Field(description="Line identifier")
    product: Annotated[AssociationOne[ProductCoreEntity], NoInverse()] = Field(description="Product of the line")


@entity(description="An order of the shop", domain=ShopDomain)
class OrderCoreEntity(BaseCoreEntity):
    """An order with its customer, its currency and its lines."""

    id: str = Field(description="Order identifier")
    customer: Annotated[AssociationOne[CustomerCoreEntity], NoInverse()] = Field(description="Customer of the order")
    currency: Annotated[CompositeOne[CurrencyEnumEntity], NoInverse()] = Field(description="Currency of the order")
    lines: Annotated[AssociationMany[OrderLineCoreEntity], NoInverse()] = Field(description="Lines of the order")


def make_order(product: ProductCoreEntity | None = None) -> OrderCoreEntity:
    """An order whose line holds the product loaded, or only its id when ``product`` is None."""
    line = OrderLineCoreEntity(id="l1", product=AssociationOne(id="p1", entity=product))
    return OrderCoreEntity(
        id="o1",
        customer=AssociationOne(id="c1", entity=CustomerCoreEntity(id="c1")),
        currency=CompositeOne(id="eur", entity=CurrencyEnumEntity.EUR),
        lines=AssociationMany(ids=("l1",), entities=(line,), entities_loaded=True),
    )


@meta(description="A reports database that lists no entity")
class ReportsDatabaseStorage(BaseStorage):
    """Declares no @entities."""

    @classmethod
    def get_wrapper_class(cls) -> None:
        """No nesting wrapper: this example passes the resource itself."""
        return None

    def get_order(self) -> OrderCoreEntity:
        """An order, though the resource lists none."""
        return make_order()

    def _load_order(self) -> OrderCoreEntity:
        """A private helper: not checked."""
        return make_order()

    def count_orders(self) -> int:
        """An answer with no entity passes."""
        return len([self._load_order()])


@meta(description="A database that declares an empty list")
@entities()
class EmptyDatabaseStorage(BaseStorage):
    """Declares an empty @entities: it returns no entity."""

    @classmethod
    def get_wrapper_class(cls) -> None:
        """No nesting wrapper: this example passes the resource itself."""
        return None

    def get_order(self) -> OrderCoreEntity:
        """An order, though the list is empty."""
        return make_order()


# Run the case.
reports = ReportsDatabaseStorage()
print("private helper:", type(reports._load_order()).__name__)
print("no entity:", reports.count_orders())
for resource in (reports, EmptyDatabaseStorage()):
    try:
        resource.get_order()
    except ResourceEntitiesError as error:
        print(f"{type(error).__name__}: {error}")
    else:
        raise AssertionError(f"{type(resource).__name__} answered with an entity")
