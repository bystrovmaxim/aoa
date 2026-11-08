"""A resource answers with the entities it lists.

Every public method of a resource is checked when it returns. An answer made of listed
entities passes and reaches the caller unchanged — whole, partial, in a list or a mapping. A
dictionary member belongs to the model and passes without being listed, and an answer with
no entity costs one type check.

Run: uv run python examples/step_21_resource/10_return_listed.py
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
        """A whole order; its line's product is held by id only."""
        return make_order()

    def get_order_summary(self) -> OrderCoreEntity:
        """A partial order of a listed class."""
        return OrderCoreEntity.partial(id="o1")

    def list_orders(self) -> list[OrderCoreEntity]:
        """Orders in a list."""
        return [make_order(), make_order()]

    def orders_by_customer(self) -> dict[str, OrderCoreEntity]:
        """Orders in a mapping."""
        return {"c1": make_order()}

    def get_currency(self) -> CurrencyEnumEntity:
        """A dictionary member."""
        return CurrencyEnumEntity.EUR

    def count_orders(self) -> int:
        """An answer with no entity."""
        return 2


# Run the case.
shop = ShopDatabaseStorage()
order = shop.get_order()
print("whole order:", type(order).__name__, order.id)
print("partial order:", type(shop.get_order_summary()).__name__)
print("list:", [type(item).__name__ for item in shop.list_orders()])
print("mapping:", {key: type(item).__name__ for key, item in shop.orders_by_customer().items()})
print("dictionary member:", shop.get_currency().code)
print("no entity:", shop.count_orders())
