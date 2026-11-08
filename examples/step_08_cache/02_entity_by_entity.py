"""
Cache a collection entity by entity: one order, one entry, shared by two actions.

GetOrderAction and ListOrdersAction both build the key "a:order:<id>:row" for an
order, so with layout=CacheLayout.ENTITIES they keep one entry of it. Changing o1
drops that entry alone: o2 keeps hitting, and the list misses once. A new order
drops the customer's list through its tag.

Run:
    uv run python examples/step_08_cache/02_entity_by_entity.py
"""

import asyncio
import json

from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain import BaseCoreEntity
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.cache import CacheLayout, cache_entity_key, cache_invalidate, cache_key, cache_write
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.entities import entities
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.resources.base_storage import BaseStorage
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.cache_coordinator import CacheCoordinator
from aoa.action_machine.runtime.cache_entity import CachedEntity
from aoa.action_machine.runtime.cache_tag import CacheTag
from aoa.action_machine.runtime.tools_box import ToolsBox

# The storage the actions read, and how many times each pipeline ran.
ORDERS = {"o1": ("c1", 10.0), "o2": ("c1", 20.0)}
RUNS: dict[str, int] = {}


def ran(action: str) -> None:
    RUNS[action] = RUNS.get(action, 0) + 1


class ShopDomain(BaseDomain):
    name = "shop"
    description = "Shop domain"


@entity(description="An order", domain=ShopDomain)
class OrderCoreEntity(BaseCoreEntity):
    id: str = Field(description="Order id")
    total: float = Field(description="Total")


@entity(description="A customer, owner of a list of orders", domain=ShopDomain)
class CustomerCoreEntity(BaseCoreEntity):
    id: str = Field(description="Customer id")


@meta(description="Stores the shop entities")
@entities(
    OrderCoreEntity,
    CustomerCoreEntity,
)
class ShopStorage(BaseStorage):
    """Hold the shop entities."""


class OrderIdParams(BaseParams):
    order_id: str = Field(description="Order id")


class CustomerIdParams(BaseParams):
    customer_id: str = Field(description="Customer id")


class OrderResult(BaseResult):
    order: OrderCoreEntity = Field(description="Order")


class OrderListResult(BaseResult):
    orders: list[OrderCoreEntity] = Field(description="Orders")
    total_count: int = Field(description="How many")


def load(order_id: str) -> OrderCoreEntity:
    return OrderCoreEntity(id=order_id, total=ORDERS[order_id][1])


@meta(description="Get one order", domain=ShopDomain)
@check_roles(GuestRole)
class GetOrderAction(BaseAction[OrderIdParams, OrderResult]):
    @cache_key("One order")
    async def order_cache_key(self, params: OrderIdParams, box: ToolsBox, connections: Connections) -> str | None:
        return f"a:get:{params.order_id}"

    @cache_entity_key("An order, as a row")
    async def order_cache_entity_key(
        self, params: OrderIdParams, box: ToolsBox, connections: Connections, entity: OrderCoreEntity
    ) -> str:
        return f"a:order:{entity.id}:row"

    @cache_write("Keep the order", tags=(OrderCoreEntity,), layout=CacheLayout.ENTITIES)
    async def order_cache_write(
        self, params: OrderIdParams, box: ToolsBox, connections: Connections, result: OrderResult, duration_ms: float
    ) -> list[CacheTag] | None:
        return []

    @summary_aspect("Load the order")
    async def load_summary(self, params: OrderIdParams, state: BaseState, box: ToolsBox, connections: Connections) -> OrderResult:
        ran("GetOrderAction")
        return OrderResult(order=load(params.order_id))


@meta(description="List the orders of a customer", domain=ShopDomain)
@check_roles(GuestRole)
class ListOrdersAction(BaseAction[CustomerIdParams, OrderListResult]):
    @cache_key("Orders of a customer")
    async def orders_cache_key(self, params: CustomerIdParams, box: ToolsBox, connections: Connections) -> str | None:
        return f"a:customer:{params.customer_id}"

    @cache_entity_key("One order of the list, as a row")
    async def order_cache_entity_key(
        self, params: CustomerIdParams, box: ToolsBox, connections: Connections, entity: OrderCoreEntity
    ) -> str:
        return f"a:order:{entity.id}:row"

    @cache_write("Keep the list order by order", tags=(CustomerCoreEntity,), layout=CacheLayout.ENTITIES)
    async def orders_cache_write(
        self, params: CustomerIdParams, box: ToolsBox, connections: Connections, result: OrderListResult, duration_ms: float
    ) -> list[CacheTag] | None:
        return [CacheTag(type=CustomerCoreEntity, key=params.customer_id)]

    @summary_aspect("List the orders")
    async def list_summary(self, params: CustomerIdParams, state: BaseState, box: ToolsBox, connections: Connections) -> OrderListResult:
        ran("ListOrdersAction")
        ids = sorted(order_id for order_id, (customer_id, _total) in ORDERS.items() if customer_id == params.customer_id)
        return OrderListResult(orders=[load(order_id) for order_id in ids], total_count=len(ids))


class TotalParams(BaseParams):
    order_id: str = Field(description="Order id")
    total: float = Field(description="Total")


class NewOrderParams(BaseParams):
    order_id: str = Field(description="Order id")
    customer_id: str = Field(description="Customer id")
    total: float = Field(description="Total")


@meta(description="Change an order", domain=ShopDomain)
@check_roles(GuestRole)
class UpdateOrderAction(BaseAction[TotalParams, OrderResult]):
    @cache_invalidate("Drop the changed order", tags=(OrderCoreEntity,))
    async def order_cache_invalidate(
        self, params: TotalParams, box: ToolsBox, connections: Connections, result: OrderResult
    ) -> list[CacheTag] | None:
        return [CacheTag(type=OrderCoreEntity, key=params.order_id)]

    @summary_aspect("Store the total")
    async def update_summary(self, params: TotalParams, state: BaseState, box: ToolsBox, connections: Connections) -> OrderResult:
        ORDERS[params.order_id] = (ORDERS[params.order_id][0], params.total)
        return OrderResult(order=load(params.order_id))


@meta(description="Add an order", domain=ShopDomain)
@check_roles(GuestRole)
class CreateOrderAction(BaseAction[NewOrderParams, OrderResult]):
    @cache_invalidate("A new order changes the customer's list", tags=(CustomerCoreEntity,))
    async def order_cache_invalidate(
        self, params: NewOrderParams, box: ToolsBox, connections: Connections, result: OrderResult
    ) -> list[CacheTag] | None:
        return [CacheTag(type=CustomerCoreEntity, key=params.customer_id)]

    @summary_aspect("Store the order")
    async def create_summary(self, params: NewOrderParams, state: BaseState, box: ToolsBox, connections: Connections) -> OrderResult:
        ORDERS[params.order_id] = (params.customer_id, params.total)
        return OrderResult(order=load(params.order_id))


async def main() -> None:
    store = CacheCoordinator()
    machine = ActionProductMachine(log_coordinator=LogCoordinator(loggers=[]), cache_coordinator=store)

    async def listed() -> list[tuple[str, float]]:
        result = await machine.run(Context(), ListOrdersAction(), CustomerIdParams(customer_id="c1"))
        return [(one.id, one.total) for one in result.orders]

    async def got(order_id: str) -> float:
        return (await machine.run(Context(), GetOrderAction(), OrderIdParams(order_id=order_id))).order.total

    print("1) The list and both orders")
    print("   list:", await listed(), "| o1:", await got("o1"), "| o2:", await got("o2"))
    print("   entries:", store.size, "| runs:", RUNS)
    list_entry = await store.get_entry(ListOrdersAction, "a:customer:c1")
    print("   a:customer:c1 ->", json.loads(list_entry.payload))
    o1_entry = await store.get_entry(CachedEntity, "a:order:o1:row")
    print("   a:order:o1:row ->", json.loads(o1_entry.payload))

    print("2) UpdateOrderAction(o1) drops the entry of o1 alone")
    await machine.run(Context(), UpdateOrderAction(), TotalParams(order_id="o1", total=11.0))
    print("   o2:", await got("o2"), "| runs:", RUNS)
    print("   list:", await listed(), "| o1:", await got("o1"), "| runs:", RUNS)

    print("3) CreateOrderAction drops the customer's list")
    await machine.run(Context(), CreateOrderAction(), NewOrderParams(order_id="o3", customer_id="c1", total=30.0))
    print("   list:", await listed(), "| runs:", RUNS)


asyncio.run(main())
