"""Each resource class is checked by its own list.

The check reads the list of the class that answered. A subclass with its own ``@entities``
answers with its own entities, even through a method it inherits; a subclass that declares
none lists nothing. A gateway, too, lists the entities it may return and is checked the same
way as a storage.

Run: uv run python examples/step_21_resource/15_return_inherited.py
"""

from aoa.action_machine.resources import BaseGateway

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
        """An order."""
        return make_order()

    def get_customer(self) -> CustomerCoreEntity:
        """A customer."""
        return CustomerCoreEntity(id="c1")


@meta(description="The customer register: a database of customers only")
@entities(CustomerCoreEntity)
class CustomerRegisterStorage(ShopDatabaseStorage):
    """Inherits the shop's methods but lists only customers."""


@meta(description="A copy of the shop database that declares no list")
class ShopCopyStorage(ShopDatabaseStorage):
    """Inherits the shop's methods and declares no @entities."""


@meta(description="The catalog service")
@entities(ProductCoreEntity)
class CatalogGateway(BaseGateway):
    """Someone else's service; it reports products."""

    @classmethod
    def get_wrapper_class(cls) -> None:
        """No wrapper: a gateway is passed as it is."""
        return None

    def get_product(self) -> ProductCoreEntity:
        """A product of the catalog."""
        return ProductCoreEntity(id="p1", name="Tea")

    def get_customer(self) -> CustomerCoreEntity:
        """A customer, which the catalog does not list."""
        return CustomerCoreEntity(id="c1")


# Run the case.
register = CustomerRegisterStorage()
print("register, customer:", register.get_customer().id)
catalog = CatalogGateway()
print("gateway, product:", catalog.get_product().name)
for method in (register.get_order, ShopCopyStorage().get_order, catalog.get_customer):
    try:
        method()
    except ResourceEntitiesError as error:
        print(f"{type(error).__name__}: {error}")
    else:
        raise AssertionError(f"{method.__qualname__} was accepted")
