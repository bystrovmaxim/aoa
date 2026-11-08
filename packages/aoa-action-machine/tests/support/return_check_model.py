# packages/aoa-action-machine/tests/support/return_check_model.py
"""
The model of the return check — a shop database and the classes it may answer with.

It is shared by ``test_resource_entities_check`` (the plan, the walk, the wrapper and
the refusals) and ``test_resource_entities_bench`` (the loose cost guard): both read
the same declarations, so they live here rather than in one test module.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field

from aoa.action_machine.domain import (
    AssociationMany,
    AssociationOne,
    BaseCoreEntity,
    BaseDomain,
    BaseEnumEntity,
    BaseStateEntity,
    CompositeOne,
    NoInverse,
    value,
)
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.intents.aspects.regular_aspect_decorator import regular_aspect
from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.check_roles import GuestRole, check_roles
from aoa.action_machine.intents.checkers import result_string
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.entities import entities
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources import BaseGateway, BaseStorage, Connections
from aoa.action_machine.resources.sql.sql_storage_wrapper import SqlStorageWrapper
from aoa.action_machine.runtime.tools_box import ToolsBox

# ═════════════════════════════════════════════════════════════════════════════
# THE MODEL — a shop database that lists three entities, and a catalog outside it
# ═════════════════════════════════════════════════════════════════════════════


class ReturnCheckDomain(BaseDomain):
    """The domain of the return-check entities."""

    name = "return_check"
    description = "Return check"


@entity(description="A customer of the shop", domain=ReturnCheckDomain)
class CustomerCoreEntity(BaseCoreEntity):
    """A listed entity with no relations: the plan needs only its type checked."""

    id: str = Field(description="Customer id")


@entity(description="A product of the catalog database", domain=ReturnCheckDomain)
class ProductCoreEntity(BaseCoreEntity):
    """An entity of another database; the shop database does not list it."""

    id: str = Field(description="Product id")
    name: str = Field(description="Product name")


@entity(description="A currency of the model", domain=ReturnCheckDomain)
class CurrencyEnumEntity(BaseEnumEntity):
    """A dictionary member: the model's, not a database's — passes without being listed."""

    symbol: str = Field(default="", description="Currency symbol")
    EUR = value(code="eur", display_name="Euro", symbol="€")


@entity(description="The status of an order", domain=ReturnCheckDomain)
class OrderStateEntity(BaseStateEntity):
    """A lifecycle state: the model's, not a database's — passes without being listed."""

    DRAFT = value(code="draft", display_name="Draft")
    PAID = value(code="paid", display_name="Paid")


@entity(description="A line of an order", domain=ReturnCheckDomain)
class OrderLineCoreEntity(BaseCoreEntity):
    """A listed entity whose product relation leads out of the shop list."""

    id: str = Field(description="Line id")
    product: Annotated[AssociationOne[ProductCoreEntity], NoInverse()] = Field(description="Product of the line")


@entity(description="An order of the shop", domain=ReturnCheckDomain)
class OrderCoreEntity(BaseCoreEntity):
    """A listed entity that reaches the catalog through its lines."""

    id: str = Field(description="Order id")
    customer: Annotated[AssociationOne[CustomerCoreEntity], NoInverse()] = Field(description="Customer of the order")
    currency: Annotated[CompositeOne[CurrencyEnumEntity], NoInverse()] = Field(description="Currency of the order")
    lines: Annotated[AssociationMany[OrderLineCoreEntity], NoInverse()] = Field(description="Lines of the order")


@exclude_graph_model
class SpecialOrderCoreEntity(OrderCoreEntity):
    """A subclass of a listed class; not listed, so the exact-class rule refuses it."""


@entity(description="The status of a ticket", domain=ReturnCheckDomain)
class TicketStatusEnumEntity(BaseEnumEntity):
    """A dictionary member: a relation to it is not a way out of the list."""

    OPEN = value(code="open", display_name="Open")
    CLOSED = value(code="closed", display_name="Closed")


@entity(description="A support ticket", domain=ReturnCheckDomain)
class TicketCoreEntity(BaseCoreEntity):
    """A listed entity whose only entity relation is to a dictionary member."""

    id: str = Field(description="Ticket id")
    status: Annotated[AssociationOne[TicketStatusEnumEntity], NoInverse()] = Field(description="Status of the ticket")


# ═════════════════════════════════════════════════════════════════════════════
# ANSWERS — full, partial, referenced, loaded
# ═════════════════════════════════════════════════════════════════════════════


def make_line(*, product: ProductCoreEntity | None = None) -> OrderLineCoreEntity:
    """A line whose product is loaded (``product``) or a reference (``None``)."""
    return OrderLineCoreEntity(id="l1", product=AssociationOne(id="p1", entity=product))


def make_order(
    *,
    product: ProductCoreEntity | None = None,
    lines_loaded: bool = True,
    order_class: type[OrderCoreEntity] = OrderCoreEntity,
) -> OrderCoreEntity:
    """A full order; its line's product is a reference unless ``product`` is given."""
    lines: AssociationMany[OrderLineCoreEntity]
    if lines_loaded:
        lines = AssociationMany(ids=("l1",), entities=(make_line(product=product),), entities_loaded=True)
    else:
        lines = AssociationMany(ids=("l1",))
    return order_class(
        id="o1",
        customer=AssociationOne(id="c1", entity=CustomerCoreEntity(id="c1")),
        currency=CompositeOne(id="eur", entity=CurrencyEnumEntity.EUR),
        lines=lines,
    )


def make_product() -> ProductCoreEntity:
    """A full product of the catalog database."""
    return ProductCoreEntity(id="p1", name="Tea")


# ═════════════════════════════════════════════════════════════════════════════
# RESOURCES — every entry point the wrapper must check, and every one it must not
# ═════════════════════════════════════════════════════════════════════════════


@meta(description="The shop database of the return-check tests")
@entities(OrderCoreEntity, OrderLineCoreEntity, CustomerCoreEntity)
class ShopDatabaseStorage(BaseStorage):
    """One database listing three entities; the catalog product is outside its list."""

    @classmethod
    def get_wrapper_class(cls) -> None:
        return None

    # ── listed answers ───────────────────────────────────────────────────────
    def fetch_order(self) -> OrderCoreEntity:
        """A full order whose product relation is a reference: passes."""
        return make_order()

    def fetch_order_without_lines(self) -> OrderCoreEntity:
        """An order whose lines are not loaded: passes."""
        return make_order(lines_loaded=False)

    def fetch_partial_order(self) -> OrderCoreEntity:
        """A partial answer of a listed class: passes."""
        return OrderCoreEntity.partial(id="o1")

    def fetch_orders(self) -> list[OrderCoreEntity]:
        """A list of listed entities: every element is checked."""
        return [make_order(), make_order()]

    def fetch_orders_tuple(self) -> tuple[OrderCoreEntity, ...]:
        """A tuple of listed entities: every element is checked."""
        return (make_order(),)

    def fetch_orders_mapping(self) -> dict[str, OrderCoreEntity]:
        """A mapping of listed entities: every value is checked."""
        return {"first": make_order()}

    def fetch_entity_free(self) -> dict[str, int]:
        """An answer without entities: passes at the cost of one type check."""
        return {"count": 2}

    def fetch_currency(self) -> CurrencyEnumEntity:
        """A dictionary member: passes without being listed."""
        return CurrencyEnumEntity.EUR

    def fetch_state(self) -> OrderStateEntity:
        """A lifecycle state: passes without being listed."""
        return OrderStateEntity.DRAFT

    # ── refused answers ──────────────────────────────────────────────────────
    def fetch_product(self) -> ProductCoreEntity:
        """An entity of another database at the root: refused."""
        return make_product()

    def fetch_order_with_loaded_product(self) -> OrderCoreEntity:
        """A loaded relation to a class outside the list: refused."""
        return make_order(product=make_product())

    def fetch_order_with_id_only_product(self) -> OrderCoreEntity:
        """A loaded id-only entity of a class outside the list: refused as loaded."""
        return make_order(product=ProductCoreEntity.partial(id="p1"))

    def fetch_orders_with_product(self) -> list[Any]:
        """A list carrying an outside entity: the path names the element."""
        return [make_order(), make_product()]

    def fetch_orders_mapping_with_product(self) -> dict[str, Any]:
        """A mapping carrying an outside entity: the path names the key."""
        return {"first": make_order(), "bad": make_product()}

    def fetch_special_order(self) -> OrderCoreEntity:
        """A subclass of a listed class: refused, the comparison is by exact class."""
        return make_order(order_class=SpecialOrderCoreEntity)

    # ── coroutines and async iterators ───────────────────────────────────────
    async def fetch_order_async(self) -> OrderCoreEntity:
        """A coroutine's listed answer passes."""
        return make_order()

    async def fetch_product_async(self) -> ProductCoreEntity:
        """A coroutine's unlisted answer is refused."""
        return make_product()

    async def stream_orders(self) -> Any:
        """An async iterator: the first element passes, the second is refused as it yields."""
        yield make_order()
        yield make_product()

    async def stream_one_order(self) -> Any:
        """An async iterator whose consumer may stop early."""
        yield make_order()
        yield make_product()

    # ── what the wrapper must not touch ──────────────────────────────────────
    def _fetch_private_product(self) -> ProductCoreEntity:
        """A private method: not wrapped, so an outside entity passes."""
        return make_product()

    @classmethod
    def fetch_class_product(cls) -> ProductCoreEntity:
        """A class method: not wrapped."""
        return make_product()

    @staticmethod
    def fetch_static_product() -> ProductCoreEntity:
        """A static method: not wrapped."""
        return make_product()

    @property
    def product_property(self) -> ProductCoreEntity:
        """A property: not wrapped."""
        return make_product()

    def iterate_products(self) -> Any:
        """A plain generator: not wrapped, so its elements are not checked."""
        yield make_product()

    def defer_product(self) -> Any:
        """A plain function returning an awaitable: the answer behind it is not checked."""
        async def _inner() -> ProductCoreEntity:
            return make_product()

        return _inner()


@meta(description="A shop database that declares no @entities")
class UndeclaredDatabaseStorage(BaseStorage):
    """A resource without the declaration refuses every entity it returns."""

    @classmethod
    def get_wrapper_class(cls) -> None:
        return None

    def fetch_order(self) -> OrderCoreEntity:
        """Any entity is refused, saying the declaration is missing."""
        return make_order()


@meta(description="A database with an empty @entities list")
@entities()
class EmptyDatabaseStorage(BaseStorage):
    """An empty declaration declares a resource that returns no entity."""

    @classmethod
    def get_wrapper_class(cls) -> None:
        return None

    def fetch_order(self) -> OrderCoreEntity:
        """Any entity is refused because the list is empty."""
        return make_order()


@meta(description="A database listing only the customer")
@entities(CustomerCoreEntity)
class CustomerOnlyDatabaseStorage(ShopDatabaseStorage):
    """A subclass with its own list; the inherited ``fetch_order`` is checked by this list."""

    @classmethod
    def get_wrapper_class(cls) -> None:
        return None

    def fetch_customer(self) -> CustomerCoreEntity:
        """The subclass's own listed entity: passes."""
        return CustomerCoreEntity(id="c1")


@meta(description="A database that inherits a declaration but declares none")
class InheritingShopDatabaseStorage(ShopDatabaseStorage):
    """A subclass never inherits its parent's plan: it declares nothing, so refuses every entity."""

    @classmethod
    def get_wrapper_class(cls) -> None:
        return None


@meta(description="The catalog gateway")
@entities(ProductCoreEntity)
class CatalogGateway(BaseGateway):
    """A gateway is a database too: it lists the entities it may return."""

    @classmethod
    def get_wrapper_class(cls) -> None:
        return None

    def fetch_product(self) -> ProductCoreEntity:
        """A listed entity: passes."""
        return make_product()

    def fetch_customer(self) -> CustomerCoreEntity:
        """A class outside the gateway's list: refused."""
        return CustomerCoreEntity(id="c1")


@meta(description="A ticket database whose only relation is a dictionary")
@entities(TicketCoreEntity)
class TicketDatabaseStorage(BaseStorage):
    """A relation to a dictionary member is not a way out of the list."""

    @classmethod
    def get_wrapper_class(cls) -> None:
        return None

    def fetch_ticket(self) -> TicketCoreEntity:
        """A listed ticket with its dictionary member loaded: passes."""
        return TicketCoreEntity(id="t1", status=AssociationOne(id="open", entity=TicketStatusEnumEntity.OPEN))


# ═════════════════════════════════════════════════════════════════════════════
# THE NESTING WRAPPER — a nested action's answers come from the wrapped resource
# ═════════════════════════════════════════════════════════════════════════════


@exclude_graph_model
class PlanningShopStorageWrapper(SqlStorageWrapper):
    """An application's ``…StorageWrapper``: its own methods answer for the wrapped database."""

    async def fetch_unchecked(self) -> Any:
        """Ask the wrapped resource for an outside entity without its own wrapper running."""
        return self._connection_manager._fetch_unchecked()

    async def fetch_listed_unchecked(self) -> Any:
        """Ask the wrapped resource for a listed entity without its own wrapper running."""
        return self._connection_manager._fetch_listed_unchecked()

    @classmethod
    def get_wrapper_class(cls) -> type[PlanningShopStorageWrapper]:
        """Keep the same wrapper for deeper nesting levels."""
        return PlanningShopStorageWrapper


@meta(description="The shop database a nested action receives through a wrapper")
@entities(OrderCoreEntity, OrderLineCoreEntity, CustomerCoreEntity)
class PlanningShopDatabaseStorage(BaseStorage):
    """A database whose nested actions see a ``SqlStorageWrapper`` subclass."""

    @classmethod
    def get_wrapper_class(cls) -> type[PlanningShopStorageWrapper]:
        return PlanningShopStorageWrapper

    async def check_rollup_support(self) -> bool:
        """Answer the nested action's lifecycle probe."""
        return True

    def _fetch_unchecked(self) -> ProductCoreEntity:
        """The outside answer the wrapper's own method forwards."""
        return make_product()

    def _fetch_listed_unchecked(self) -> OrderCoreEntity:
        """The listed answer the wrapper's own method forwards."""
        return make_order()


# ═════════════════════════════════════════════════════════════════════════════
# ACTIONS — a test-bench substitute, and a nested action through the wrapper
# ═════════════════════════════════════════════════════════════════════════════


@meta(description="Fetch an entity through a resource resolved from the box", domain=ReturnCheckDomain)
@check_roles(GuestRole)
class FetchThroughResourceAction(BaseAction["FetchThroughResourceAction.Params", "FetchThroughResourceAction.Result"]):
    """Resolve the resource from the box and call a public method on it."""

    class Params(BaseParams):
        """No input."""

    class Result(BaseResult):
        """The value the resource answered with."""

        value: str = Field(description="Id of the answered entity")

    @regular_aspect("Fetch through the resource")
    @result_string("value", required=True)
    async def fetch_aspect(
        self,
        params: FetchThroughResourceAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> dict:
        """Call the resource's public method; a resource instance checks its own answer."""
        storage = await box.resolve(ShopDatabaseStorage)
        answer = storage.fetch_product()
        return {"value": answer.id}

    @summary_aspect("Build result")
    async def build_result_summary(
        self,
        params: FetchThroughResourceAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> FetchThroughResourceAction.Result:
        """Build the Result from state."""
        return FetchThroughResourceAction.Result(value=state["value"])


@meta(description="Run a nested action against a wrapped database", domain=ReturnCheckDomain)
@check_roles(GuestRole)
@connection(PlanningShopDatabaseStorage, key="db")
class NestedProbeAction(BaseAction["NestedProbeAction.Params", "NestedProbeAction.Result"]):
    """Hand the connection to a child action, which receives the wrapper."""

    class Params(BaseParams):
        """The child's probe mode."""

        mode: Literal["identity", "fetch"] = Field(description="What the child should do")

    class Result(BaseResult):
        """The child's answer."""

        value: str = Field(description="Answer of the child action")

    @regular_aspect("Run the child action")
    @result_string("value", required=True)
    async def run_child_aspect(
        self,
        params: NestedProbeAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> dict:
        """Pass the connections to the child action."""
        child = await box.run(
            NestedChildAction,
            NestedChildAction.Params(mode=params.mode),
            connections=connections,
        )
        return {"value": child.value}

    @summary_aspect("Build result")
    async def build_result_summary(
        self,
        params: NestedProbeAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> NestedProbeAction.Result:
        """Build the Result from state."""
        return NestedProbeAction.Result(value=state["value"])


@meta(description="The child of the nested wrapper probe", domain=ReturnCheckDomain)
@check_roles(GuestRole)
@connection(PlanningShopDatabaseStorage, key="db")
class NestedChildAction(BaseAction["NestedChildAction.Params", "NestedChildAction.Result"]):
    """Probe the wrapper a nested action receives."""

    class Params(BaseParams):
        """The probe mode."""

        mode: Literal["identity", "fetch"] = Field(description="What to do with the connection")

    class Result(BaseResult):
        """The probe's answer."""

        value: str = Field(description="Identity or id of the answered entity")

    @regular_aspect("Probe the wrapper")
    @result_string("value", required=True)
    async def probe_aspect(
        self,
        params: NestedChildAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> dict:
        """The nested action sees a ``SqlStorageWrapper`` and its answers use the wrapped plan."""
        connection_value = connections["db"]
        if not isinstance(connection_value, SqlStorageWrapper):
            raise TypeError(f"expected a SqlStorageWrapper, got {type(connection_value).__name__}")
        if params.mode == "identity":
            rollup = await connection_value.check_rollup_support()
            return {"value": f"{type(connection_value).__name__}:{rollup}"}
        answer = await connection_value.fetch_unchecked()
        return {"value": answer.id}

    @summary_aspect("Build result")
    async def build_result_summary(
        self,
        params: NestedChildAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> NestedChildAction.Result:
        """Build the Result from state."""
        return NestedChildAction.Result(value=state["value"])
