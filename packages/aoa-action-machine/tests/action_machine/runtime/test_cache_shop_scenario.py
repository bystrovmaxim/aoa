# packages/aoa-action-machine/tests/action_machine/runtime/test_cache_shop_scenario.py
"""
The shop of issue #413 through the machine: a shared order, one changed order, a new order.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Cases 12.1 and 12.4. ``GetOrderAction`` and ``ListOrdersAction`` share the entry of
``o1``; ``UpdateOrderAction(o1)`` drops that entry alone, so ``GetOrderAction(o2)``
keeps hitting while the list misses once and writes ``o1`` again; ``CreateOrderAction``
drops the customer's list through its tag, and the next list shows the new order.
"""

from __future__ import annotations

from aoa.action_machine.context.context import Context
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.cache_coordinator import CacheCoordinator
from aoa.action_machine.runtime.cache_entity import CachedEntity

from ...support import shop_cache_model as shop


class _Shop:
    """One machine and one store over the shop, with a call per action."""

    def __init__(self) -> None:
        self.store = CacheCoordinator()
        self.machine = ActionProductMachine(log_coordinator=LogCoordinator(loggers=[]), cache_coordinator=self.store)

    async def get(self, order_id: str) -> float:
        result = await self.machine.run(Context(), shop.GetOrderAction(), shop.OrderIdParams(order_id=order_id))
        return result.order.total

    async def list(self, customer_id: str = "c1") -> list[tuple[str, float]]:
        result = await self.machine.run(Context(), shop.ListOrdersAction(), shop.CustomerIdParams(customer_id=customer_id))
        return [(one.id, one.total) for one in result.orders]

    async def update(self, order_id: str, total: float) -> None:
        await self.machine.run(Context(), shop.UpdateOrderAction(), shop.TotalParams(order_id=order_id, total=total))

    async def create(self, order_id: str, total: float, customer_id: str = "c1") -> None:
        await self.machine.run(
            Context(), shop.CreateOrderAction(), shop.NewOrderParams(order_id=order_id, customer_id=customer_id, total=total)
        )


async def test_a_changed_order_drops_its_entry_alone() -> None:
    """12.1: before, both entries went and both actions ran again; now o2 keeps hitting, the list misses once, and its write serves o1 to the get."""
    shop.reset()
    store = _Shop()
    assert await store.list() == [("o1", 10.0), ("o2", 20.0)]
    assert (await store.get("o1"), await store.get("o2")) == (10.0, 20.0)
    assert store.store.size == 5  # the list, two gets, o1 and o2 — o1 stored once for both actions
    assert shop.RUNS == {"ListOrdersAction": 1, "GetOrderAction": 2}

    await store.update("o1", 11.0)
    assert await store.get("o2") == 20.0
    assert shop.RUNS == {"ListOrdersAction": 1, "GetOrderAction": 2}

    assert await store.list() == [("o1", 11.0), ("o2", 20.0)]
    # The list wrote o1 again under the shared key, so the get of o1 hits without running.
    assert await store.get("o1") == 11.0
    assert shop.RUNS == {"ListOrdersAction": 2, "GetOrderAction": 2}


async def test_a_new_order_drops_the_list_through_its_tag() -> None:
    """12.4: before, the cached list stayed ['o1', 'o2']; now CreateOrderAction drops it and o3 appears."""
    shop.reset()
    store = _Shop()
    assert [order_id for order_id, _total in await store.list()] == ["o1", "o2"]
    await store.create("o3", 30.0)
    assert [order_id for order_id, _total in await store.list()] == ["o1", "o2", "o3"]
    assert shop.RUNS == {"ListOrdersAction": 2}


async def test_a_list_whose_entity_entry_is_gone_runs_whole() -> None:
    """The adversarial case of the issue: one entity entry removed gives a miss, never a shorter list."""
    shop.reset()
    store = _Shop()
    await store.list()
    await store.store.invalidate(CachedEntity, "a:order:o2:row")
    assert await store.list() == [("o1", 10.0), ("o2", 20.0)]
    assert shop.RUNS == {"ListOrdersAction": 2}
