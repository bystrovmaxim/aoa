# packages/aoa-action-machine/tests/support/shop_cache_model.py
"""
A small shop that caches entity by entity, for the tests of issue #413.

``GetOrderAction`` reads one order, ``ListOrdersAction`` the orders of a customer; both
build the key ``a:order:<id>:row`` for an order, so they share its entry.
``UpdateOrderAction`` changes an order and drops ``(ShopOrderCoreEntity, id)``;
``CreateOrderAction`` adds one and drops the customer's list by
``(ShopCustomerCoreEntity, customer_id)``. ``DATABASE`` and ``RUNS`` stand in for the
storage and count the pipeline runs.
"""

from __future__ import annotations

from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity
from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.cache import (
    CacheLayout,
    cache_entity_key,
    cache_invalidate,
    cache_key,
    cache_read,
    cache_write,
)
from aoa.action_machine.intents.check_roles import GuestRole, check_roles
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.cache_entry import CacheEntry
from aoa.action_machine.runtime.cache_tag import CacheTag
from aoa.action_machine.runtime.tools_box import ToolsBox

from .domain_model.domains import OrdersDomain

DATABASE: dict[str, dict[str, object]] = {}
RUNS: dict[str, int] = {}
READS: list[object] = []  # what each hit of ListOrdersAction handed @cache_read


def reset(orders: dict[str, tuple[str, float]] | None = None) -> None:
    """Fill the stand-in storage with ``{order id: (customer id, total)}`` and zero the run counts."""
    DATABASE.clear()
    for order_id, (customer_id, total) in (orders or {"o1": ("c1", 10.0), "o2": ("c1", 20.0)}).items():
        DATABASE[order_id] = {"customer_id": customer_id, "total": total}
    RUNS.clear()
    READS.clear()


def _ran(action: str) -> None:
    RUNS[action] = RUNS.get(action, 0) + 1


@entity(description="A shop order, cached entity by entity", domain=OrdersDomain)
class ShopOrderCoreEntity(BaseCoreEntity):
    """An order."""

    id: str = Field(description="Order id")
    total: float = Field(description="Total")


@entity(description="A shop customer, owner of a list", domain=OrdersDomain)
class ShopCustomerCoreEntity(BaseCoreEntity):
    """A customer."""

    id: str = Field(description="Customer id")


class OrderIdParams(BaseParams):
    """One order."""

    order_id: str = Field(description="Order id")


class CustomerIdParams(BaseParams):
    """One customer."""

    customer_id: str = Field(description="Customer id")


class OrderResult(BaseResult):
    """One order."""

    order: ShopOrderCoreEntity = Field(description="Order")


class OrderListResult(BaseResult):
    """The orders of a customer and how many."""

    orders: list[ShopOrderCoreEntity] = Field(description="Orders")
    total_count: int = Field(description="How many")


def order(order_id: str) -> ShopOrderCoreEntity:
    """The order as the storage holds it now."""
    row = DATABASE[order_id]
    return ShopOrderCoreEntity(id=order_id, total=float(row["total"]))  # type: ignore[arg-type]


@meta(description="Get one order", domain=OrdersDomain)
@check_roles(GuestRole)
class GetOrderAction(BaseAction[OrderIdParams, OrderResult]):
    """Caches one order entity by entity."""

    @cache_key("One order")
    async def order_cache_key(self, params: OrderIdParams, box: ToolsBox, connections: Connections) -> str | None:
        return f"a:get:{params.order_id}"

    @cache_entity_key("An order, as a row")
    async def order_cache_entity_key(
        self, params: OrderIdParams, box: ToolsBox, connections: Connections, entity: ShopOrderCoreEntity
    ) -> str:
        return f"a:order:{entity.id}:row"

    @cache_write("Keep the order", tags=(ShopOrderCoreEntity,), layout=CacheLayout.ENTITIES)
    async def order_cache_write(
        self, params: OrderIdParams, box: ToolsBox, connections: Connections, result: OrderResult, duration_ms: float
    ) -> list[CacheTag] | None:
        return []

    @summary_aspect("Load the order")
    async def load_summary(
        self, params: OrderIdParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> OrderResult:
        _ran("GetOrderAction")
        return OrderResult(order=order(params.order_id))


@meta(description="List the orders of a customer", domain=OrdersDomain)
@check_roles(GuestRole)
class ListOrdersAction(BaseAction[CustomerIdParams, OrderListResult]):
    """Caches the list entity by entity; the list belongs to its customer."""

    @cache_key("Orders of a customer")
    async def orders_cache_key(self, params: CustomerIdParams, box: ToolsBox, connections: Connections) -> str | None:
        return f"a:customer:{params.customer_id}"

    @cache_entity_key("One order of the list, as a row")
    async def order_cache_entity_key(
        self, params: CustomerIdParams, box: ToolsBox, connections: Connections, entity: ShopOrderCoreEntity
    ) -> str:
        return f"a:order:{entity.id}:row"

    @cache_read("Record what a hit assembled, and keep it")
    async def orders_cache_read(
        self, params: CustomerIdParams, box: ToolsBox, connections: Connections, entry: CacheEntry
    ) -> OrderListResult | None:
        READS.append(entry.result)
        return entry.result  # type: ignore[no-any-return]

    @cache_write("Keep the list order by order", tags=(ShopCustomerCoreEntity,), layout=CacheLayout.ENTITIES)
    async def orders_cache_write(
        self, params: CustomerIdParams, box: ToolsBox, connections: Connections, result: OrderListResult, duration_ms: float
    ) -> list[CacheTag] | None:
        return [CacheTag(type=ShopCustomerCoreEntity, key=params.customer_id)]

    @summary_aspect("List the orders")
    async def list_summary(
        self, params: CustomerIdParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> OrderListResult:
        _ran("ListOrdersAction")
        ids = sorted(order_id for order_id, row in DATABASE.items() if row["customer_id"] == params.customer_id)
        return OrderListResult(orders=[order(order_id) for order_id in ids], total_count=len(ids))


class TotalParams(BaseParams):
    """A new total for an order."""

    order_id: str = Field(description="Order id")
    total: float = Field(description="Total")


class NewOrderParams(BaseParams):
    """A new order."""

    order_id: str = Field(description="Order id")
    customer_id: str = Field(description="Customer id")
    total: float = Field(description="Total")


@meta(description="Change an order", domain=OrdersDomain)
@check_roles(GuestRole)
class UpdateOrderAction(BaseAction[TotalParams, OrderResult]):
    """Drops the changed order's entity entry."""

    @cache_invalidate("Drop the changed order", tags=(ShopOrderCoreEntity,))
    async def order_cache_invalidate(
        self, params: TotalParams, box: ToolsBox, connections: Connections, result: OrderResult
    ) -> list[CacheTag] | None:
        return [CacheTag(type=ShopOrderCoreEntity, key=params.order_id)]

    @summary_aspect("Store the total")
    async def update_summary(
        self, params: TotalParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> OrderResult:
        DATABASE[params.order_id]["total"] = params.total
        return OrderResult(order=order(params.order_id))


@meta(description="Add an order", domain=OrdersDomain)
@check_roles(GuestRole)
class CreateOrderAction(BaseAction[NewOrderParams, OrderResult]):
    """A new order changes the customer's list."""

    @cache_invalidate("A new order changes the customer's list", tags=(ShopCustomerCoreEntity,))
    async def order_cache_invalidate(
        self, params: NewOrderParams, box: ToolsBox, connections: Connections, result: OrderResult
    ) -> list[CacheTag] | None:
        return [CacheTag(type=ShopCustomerCoreEntity, key=params.customer_id)]

    @summary_aspect("Store the order")
    async def create_summary(
        self, params: NewOrderParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> OrderResult:
        DATABASE[params.order_id] = {"customer_id": params.customer_id, "total": params.total}
        return OrderResult(order=order(params.order_id))
