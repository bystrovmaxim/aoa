"""A resource cannot answer with an entity it does not list.

An entity whose exact class the resource's ``@entities`` does not name is refused with
``ResourceEntitiesError``, naming the resource, the method, the place in the answer and the
class. A subclass of a listed class is not listed either: a resource returns exactly the
classes it promised.

Run: uv run python examples/step_21_resource/11_return_unlisted.py
"""

from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model

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


@exclude_graph_model
class GiftOrderCoreEntity(OrderCoreEntity):
    """A subclass of a listed class; the shop database does not list it."""


@meta(description="The shop database")
@entities(OrderCoreEntity, OrderLineCoreEntity, CustomerCoreEntity)
class ShopDatabaseStorage(BaseStorage):
    """The shop database: orders, their lines and customers lie in it; products do not."""

    @classmethod
    def get_wrapper_class(cls) -> None:
        """No nesting wrapper: this example passes the resource itself."""
        return None

    def get_product(self) -> ProductCoreEntity:
        """A product, which lies in another database."""
        return ProductCoreEntity(id="p1", name="Tea")

    def list_items(self) -> list[object]:
        """An order and, by mistake, a product."""
        return [make_order(), ProductCoreEntity(id="p1", name="Tea")]

    def items_by_kind(self) -> dict[str, object]:
        """An order and, by mistake, a product, in a mapping."""
        return {"order": make_order(), "product": ProductCoreEntity(id="p1", name="Tea")}

    def get_gift_order(self) -> OrderCoreEntity:
        """A subclass of a listed class."""
        line = OrderLineCoreEntity(id="l1", product=AssociationOne(id="p1"))
        return GiftOrderCoreEntity(
            id="o2",
            customer=AssociationOne(id="c1"),
            currency=CompositeOne(id="eur", entity=CurrencyEnumEntity.EUR),
            lines=AssociationMany(ids=("l1",), entities=(line,), entities_loaded=True),
        )


# Run the case.
shop = ShopDatabaseStorage()
for method in (shop.get_product, shop.list_items, shop.items_by_kind, shop.get_gift_order):
    try:
        method()
    except ResourceEntitiesError as error:
        print(f"{type(error).__name__}: {error}")
    else:
        raise AssertionError(f"{method.__name__} was accepted")
print("a TypeError:", issubclass(ResourceEntitiesError, TypeError))
