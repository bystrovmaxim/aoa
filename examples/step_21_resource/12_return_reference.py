"""A relation that leads out of the database comes back as a reference.

An order line points at a product of the catalog database. The shop database may answer with
that line only while the relation is unloaded — it holds the product's id and no entity. A
loaded product is refused, even a partial one that holds only its id.

Run: uv run python examples/step_21_resource/12_return_reference.py
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


@meta(description="The shop database")
@entities(OrderCoreEntity, OrderLineCoreEntity, CustomerCoreEntity)
class ShopDatabaseStorage(BaseStorage):
    """The shop database: orders, their lines and customers lie in it; products do not."""

    @classmethod
    def get_wrapper_class(cls) -> None:
        """No nesting wrapper: this example passes the resource itself."""
        return None

    def get_order(self) -> OrderCoreEntity:
        """The product is a reference: the relation holds its id only."""
        return make_order()

    def get_order_with_product(self) -> OrderCoreEntity:
        """The product is loaded into the line."""
        return make_order(product=ProductCoreEntity(id="p1", name="Tea"))

    def get_order_with_product_id(self) -> OrderCoreEntity:
        """A partial product that holds only its id is still a loaded entity."""
        return make_order(product=ProductCoreEntity.partial(id="p1"))


# Run the case.
shop = ShopDatabaseStorage()
line = shop.get_order().lines.entities[0]
print("reference:", line.product.id, "loaded:", line.product.entity is not None)
for method in (shop.get_order_with_product, shop.get_order_with_product_id):
    try:
        method()
    except ResourceEntitiesError as error:
        print(f"{method.__name__}: {error}")
    else:
        raise AssertionError(f"{method.__name__} was accepted")
