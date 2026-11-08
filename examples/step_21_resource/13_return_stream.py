"""An async iterator is checked element by element.

A resource that streams its answer is checked as it yields: the caller receives every listed
entity before the first entity the resource does not list, and the refusal comes at that
element. A coroutine is checked when it returns.

Run: uv run python examples/step_21_resource/13_return_stream.py
"""

import asyncio

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

    async def get_order(self) -> OrderCoreEntity:
        """A coroutine: its answer is checked when it returns."""
        return make_order()

    async def stream_items(self):
        """Two orders, then a product by mistake."""
        yield make_order()
        yield make_order()
        yield ProductCoreEntity(id="p1", name="Tea")


async def main() -> None:
    """Read a coroutine's answer, then consume the stream until the refusal."""
    shop = ShopDatabaseStorage()
    print("coroutine:", type(await shop.get_order()).__name__)
    received = []
    try:
        async for item in shop.stream_items():
            received.append(type(item).__name__)
    except ResourceEntitiesError as error:
        print("received before the refusal:", received)
        print(f"{type(error).__name__}: {error}")


asyncio.run(main())
