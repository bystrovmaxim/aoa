# packages/aoa-action-machine/tests/action_machine/runtime/test_cache_entity_by_entity.py
"""
A collection cached entity by entity: what a write stores, what a hit assembles.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Cases 12.1–12.3 and 12.5 of issue #413, on the shop of ``tests/support/shop_cache_model``.
"""

from __future__ import annotations

import json

from aoa.action_machine.context.context import Context
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.cache_coordinator import CacheCoordinator
from aoa.action_machine.runtime.cache_entity import CachedEntity
from aoa.action_machine.runtime.cache_tag import CacheTag

from ...support import shop_cache_model as shop


def _machine(cache: CacheCoordinator) -> ActionProductMachine:
    return ActionProductMachine(log_coordinator=LogCoordinator(loggers=[]), cache_coordinator=cache)


async def _stored(cache: CacheCoordinator, owner: type, key: str) -> object:
    entry = await cache.get_entry(owner, key)
    return None if entry is None else json.loads(entry.payload)


async def test_a_write_stores_each_entity_once_and_the_list_as_keys() -> None:
    """12.1, 12.2: the list keeps keys and its other fields; o1 is one entry, read by both actions."""
    shop.reset()
    cache = CacheCoordinator()
    machine = _machine(cache)
    await machine.run(Context(), shop.ListOrdersAction(), shop.CustomerIdParams(customer_id="c1"))
    await machine.run(Context(), shop.GetOrderAction(), shop.OrderIdParams(order_id="o1"))
    assert await _stored(cache, shop.ListOrdersAction, "a:customer:c1") == {
        "fields": {"total_count": 2},
        "entities": {"orders": ["a:order:o1:row", "a:order:o2:row"]},
    }
    assert await _stored(cache, shop.GetOrderAction, "a:get:o1") == {"fields": {}, "entities": {"order": "a:order:o1:row"}}
    assert await _stored(cache, CachedEntity, "a:order:o1:row") == {"id": "o1", "total": 10.0}
    assert await _stored(cache, CachedEntity, "a:order:o2:row") == {"id": "o2", "total": 20.0}
    assert cache.size == 4


async def test_an_entity_entry_is_tagged_with_its_type_and_id() -> None:
    """12.7.3: dropping (order, o1) removes the entity entry of o1 alone."""
    shop.reset()
    cache = CacheCoordinator()
    await _machine(cache).run(Context(), shop.ListOrdersAction(), shop.CustomerIdParams(customer_id="c1"))
    assert await cache.evict_by_tags(frozenset({CacheTag(type=shop.ShopOrderCoreEntity, key="o1")})) == 1
    assert await _stored(cache, CachedEntity, "a:order:o1:row") is None
    assert await _stored(cache, CachedEntity, "a:order:o2:row") == {"id": "o2", "total": 20.0}


async def test_a_hit_assembles_the_result_from_the_entries_without_running() -> None:
    """12.2: the second list is read from its entries; the pipeline does not run; @cache_read gets it whole."""
    shop.reset()
    machine = _machine(CacheCoordinator())
    first = await machine.run(Context(), shop.ListOrdersAction(), shop.CustomerIdParams(customer_id="c1"))
    second = await machine.run(Context(), shop.ListOrdersAction(), shop.CustomerIdParams(customer_id="c1"))
    assert shop.RUNS == {"ListOrdersAction": 1}
    assert second is not first and second.model_dump() == first.model_dump()
    assert [result.model_dump() for result in shop.READS] == [first.model_dump()]  # type: ignore[attr-defined]


async def test_a_missing_entity_makes_a_miss_never_a_shorter_list() -> None:
    """12.3: o1 dropped, the list misses, runs whole and writes o1 again; @cache_read is not called."""
    shop.reset()
    cache = CacheCoordinator()
    machine = _machine(cache)
    await machine.run(Context(), shop.ListOrdersAction(), shop.CustomerIdParams(customer_id="c1"))
    await cache.evict_by_tags(frozenset({CacheTag(type=shop.ShopOrderCoreEntity, key="o1")}))
    again = await machine.run(Context(), shop.ListOrdersAction(), shop.CustomerIdParams(customer_id="c1"))
    assert [one.id for one in again.orders] == ["o1", "o2"]
    assert shop.RUNS == {"ListOrdersAction": 2} and shop.READS == []
    assert await _stored(cache, CachedEntity, "a:order:o1:row") == {"id": "o1", "total": 10.0}


async def test_an_entity_entry_of_a_form_the_reader_refuses_makes_a_miss() -> None:
    """12.5: a partial order under the shared key cannot fill a field that takes a full one."""
    shop.reset()
    cache = CacheCoordinator()
    machine = _machine(cache)
    await machine.run(Context(), shop.GetOrderAction(), shop.OrderIdParams(order_id="o1"))
    await cache.put(CachedEntity, "a:order:o1:row", b'{"id":"o1"}', 1.0)
    again = await machine.run(Context(), shop.GetOrderAction(), shop.OrderIdParams(order_id="o1"))
    assert again.order.total == 10.0
    assert shop.RUNS == {"GetOrderAction": 2}
