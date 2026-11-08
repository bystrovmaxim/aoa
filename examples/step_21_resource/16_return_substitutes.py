"""A wrapper and a test substitute are checked too.

A nested action receives the resource's wrapper; the wrapper lists nothing of its own, and its
answers are checked by the list of the resource it wraps. A test bench substitute that is a
resource instance is checked like the real resource; a bare ``Mock`` is not a resource and is
not checked.

Run: uv run python examples/step_21_resource/16_return_substitutes.py
"""

import asyncio
from unittest.mock import AsyncMock

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.checkers import result_string
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.resources.sql import SqlStorageWrapper
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.action_machine.testing import TestBench

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
class ShopStorageWrapper(SqlStorageWrapper):
    """What a nested action receives: it reads through the wrapped database."""

    async def read_product(self) -> ProductCoreEntity:
        """Pass on what the wrapped database read."""
        return self._connection_manager._read_product()

    @classmethod
    def get_wrapper_class(cls) -> type["ShopStorageWrapper"]:
        """Deeper nesting receives the same wrapper."""
        return ShopStorageWrapper


@meta(description="The shop database")
@entities(OrderCoreEntity, OrderLineCoreEntity, CustomerCoreEntity)
class ShopDatabaseStorage(BaseStorage):
    """The shop database: orders, their lines and customers lie in it; products do not."""

    @classmethod
    def get_wrapper_class(cls) -> type[ShopStorageWrapper]:
        """A nested action receives the wrapper."""
        return ShopStorageWrapper

    async def check_rollup_support(self) -> bool:
        """The wrapper asks; this example never rolls up."""
        return True

    def _read_product(self) -> ProductCoreEntity:
        """A private read: not checked here."""
        return ProductCoreEntity(id="p1", name="Tea")

    def get_product(self) -> ProductCoreEntity:
        """A product, which this database does not list."""
        return self._read_product()


class ProductIdParams(BaseParams):
    """No input."""


class ProductIdResult(BaseResult):
    """The product id the action read."""

    product_id: str = Field(description="Id of the product read")


@meta(description="Read a product through the shop database", domain=ShopDomain)
@check_roles(GuestRole)
class ReadProductAction(BaseAction[ProductIdParams, ProductIdResult]):
    """Resolve the shop database from the box and read a product."""

    @regular_aspect("Read the product")
    @result_string("product_id", required=True)
    async def read_aspect(self, params: ProductIdParams, state: BaseState, box: ToolsBox, connections: Connections) -> dict:
        """Ask the resolved resource for a product."""
        storage = await box.resolve(ShopDatabaseStorage)
        return {"product_id": storage.get_product().id}

    @summary_aspect("Build the result")
    async def build_summary(self, params: ProductIdParams, state: BaseState, box: ToolsBox, connections: Connections) -> ProductIdResult:
        """Return the product id."""
        return ProductIdResult(product_id=state["product_id"])


async def main() -> None:
    """Check the wrapper's answer, then run the action with two substitutes."""
    wrapper = ShopStorageWrapper(ShopDatabaseStorage())
    try:
        await wrapper.read_product()
    except ResourceEntitiesError as error:
        print(f"wrapper: {error}")

    bench = TestBench(mocks={ShopDatabaseStorage: ShopDatabaseStorage()})
    try:
        await bench.run(ReadProductAction(), ProductIdParams(), rollup=False)
    except ResourceEntitiesError as error:
        print(f"resource substitute: {error}")

    mock = AsyncMock(spec=ShopDatabaseStorage)
    mock.get_product = lambda: ProductCoreEntity(id="p1", name="Tea")
    result = await TestBench(mocks={ShopDatabaseStorage: mock}).run(ReadProductAction(), ProductIdParams(), rollup=False)
    print("bare Mock, not checked:", result.product_id)


asyncio.run(main())
