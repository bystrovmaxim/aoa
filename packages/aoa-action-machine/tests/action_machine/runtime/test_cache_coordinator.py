# tests/action_machine/runtime/test_cache_coordinator.py
"""Unit tests for :class:`~aoa.action_machine.runtime.cache_coordinator.CacheCoordinator`."""

from __future__ import annotations

import asyncio

import pytest

from aoa.action_machine.runtime.cache_coordinator import CacheCoordinator
from aoa.action_machine.runtime.cache_tag import CacheTag


class _OrderAction:
    pass


class _PaymentAction:
    pass


class _Order:
    pass


class _Payment:
    pass


@pytest.mark.asyncio
async def test_put_then_get_entry_returns_entry() -> None:
    coord = CacheCoordinator()
    await coord.put(_OrderAction, "user:1:order:99", {"total": 100}, 200.0)
    entry = await coord.get_entry(_OrderAction, "user:1:order:99")
    assert entry is not None
    assert entry.result == {"total": 100}
    assert entry.pipeline_duration_ms == 200.0


@pytest.mark.asyncio
async def test_get_entry_missing_returns_none() -> None:
    coord = CacheCoordinator()
    assert await coord.get_entry(_OrderAction, "nonexistent") is None


@pytest.mark.asyncio
async def test_put_overwrites_existing_key() -> None:
    coord = CacheCoordinator()
    await coord.put(_OrderAction, "key", "first", 100.0)
    await coord.put(_OrderAction, "key", "second", 150.0)
    entry = await coord.get_entry(_OrderAction, "key")
    assert entry is not None
    assert entry.result == "second"
    assert entry.pipeline_duration_ms == 150.0


@pytest.mark.asyncio
async def test_same_user_key_different_action_classes_isolated() -> None:
    coord = CacheCoordinator()
    await coord.put(_OrderAction, "user:1:order:99", "order_result", 200.0)
    assert await coord.get_entry(_PaymentAction, "user:1:order:99") is None


@pytest.mark.asyncio
async def test_internal_key_uses_module_and_qualname() -> None:
    coord = CacheCoordinator()
    await coord.put(_OrderAction, "user:42", "result", 100.0)
    expected_prefix = f"{_OrderAction.__module__}.{_OrderAction.__qualname__}:"
    internal = f"{expected_prefix}user:42"
    assert internal in coord._store
    entry = await coord.get_entry(_OrderAction, "user:42")
    assert entry is not None
    assert entry.result == "result"


@pytest.mark.asyncio
async def test_get_entry_increments_access_count() -> None:
    coord = CacheCoordinator()
    await coord.put(_OrderAction, "key", "result", 100.0)
    await coord.get_entry(_OrderAction, "key")
    await coord.get_entry(_OrderAction, "key")
    internal = CacheCoordinator._make_key(_OrderAction, "key")
    assert coord._store[internal].access_count == 2


@pytest.mark.asyncio
async def test_miss_does_not_increment_access_count() -> None:
    coord = CacheCoordinator()
    await coord.put(_OrderAction, "key", "result", 100.0)
    assert await coord.get_entry(_OrderAction, "nonexistent") is None
    internal = CacheCoordinator._make_key(_OrderAction, "key")
    assert coord._store[internal].access_count == 0


@pytest.mark.asyncio
async def test_eviction_removes_cheapest_when_full() -> None:
    coord = CacheCoordinator(max_size=2)
    await coord.put(_OrderAction, "expensive", "r_e", 500.0)
    await coord.put(_OrderAction, "cheap", "r_c", 50.0)
    await coord.put(_OrderAction, "medium", "r_m", 200.0)
    assert coord.size == 2
    assert await coord.get_entry(_OrderAction, "cheap") is None
    entry_e = await coord.get_entry(_OrderAction, "expensive")
    entry_m = await coord.get_entry(_OrderAction, "medium")
    assert entry_e is not None and entry_e.result == "r_e"
    assert entry_m is not None and entry_m.result == "r_m"


@pytest.mark.asyncio
async def test_no_eviction_without_max_size() -> None:
    coord = CacheCoordinator()
    for i in range(100):
        await coord.put(_OrderAction, f"key:{i}", i, float(i))
    assert coord.size == 100


@pytest.mark.asyncio
async def test_invalidate_existing_returns_true() -> None:
    coord = CacheCoordinator()
    await coord.put(_OrderAction, "key", "result", 100.0)
    assert await coord.invalidate(_OrderAction, "key") is True
    assert await coord.get_entry(_OrderAction, "key") is None


@pytest.mark.asyncio
async def test_invalidate_missing_returns_false() -> None:
    coord = CacheCoordinator()
    assert await coord.invalidate(_OrderAction, "nonexistent") is False


@pytest.mark.asyncio
async def test_clear_one_class_does_not_affect_other() -> None:
    coord = CacheCoordinator()
    await coord.put(_OrderAction, "key", "order", 100.0)
    await coord.put(_PaymentAction, "key", "payment", 200.0)
    removed = await coord.clear(_OrderAction)
    assert removed == 1
    assert await coord.get_entry(_OrderAction, "key") is None
    entry = await coord.get_entry(_PaymentAction, "key")
    assert entry is not None
    assert entry.result == "payment"


@pytest.mark.asyncio
async def test_clear_all_removes_everything() -> None:
    coord = CacheCoordinator()
    await coord.put(_OrderAction, "k1", "r1", 100.0)
    await coord.put(_PaymentAction, "k2", "r2", 200.0)
    assert await coord.clear() == 2
    assert coord.size == 0


@pytest.mark.asyncio
async def test_clear_all_returns_removed_count() -> None:
    coord = CacheCoordinator()
    await coord.put(_OrderAction, "a", 1, 10.0)
    await coord.put(_OrderAction, "b", 2, 20.0)
    assert await coord.clear() == 2


@pytest.mark.asyncio
async def test_clear_action_class_returns_removed_count() -> None:
    coord = CacheCoordinator()
    await coord.put(_OrderAction, "x", "ox", 10.0)
    await coord.put(_PaymentAction, "y", "py", 20.0)
    assert await coord.clear(_OrderAction) == 1
    assert coord.size == 1


@pytest.mark.asyncio
async def test_parallel_puts_different_keys_no_corruption() -> None:
    coord = CacheCoordinator()

    async def write(i: int) -> None:
        await coord.put(_OrderAction, f"key:{i}", i * 10, float(i))

    await asyncio.gather(*[write(i) for i in range(50)])
    for i in range(50):
        entry = await coord.get_entry(_OrderAction, f"key:{i}")
        assert entry is not None
        assert entry.result == i * 10


@pytest.mark.asyncio
async def test_put_overwrite_at_capacity_does_not_evict_other_entry() -> None:
    """Updating an existing key when full must not evict unrelated keys."""
    coord = CacheCoordinator(max_size=2)
    await coord.put(_OrderAction, "a", "va", 100.0)
    await coord.put(_OrderAction, "b", "vb", 200.0)
    await coord.put(_OrderAction, "a", "va2", 300.0)
    assert coord.size == 2
    assert (await coord.get_entry(_OrderAction, "b")) is not None
    assert (await coord.get_entry(_OrderAction, "a")) is not None
    assert (await coord.get_entry(_OrderAction, "a")).result == "va2"


# ─── Tag index tests ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_put_with_tags_populates_index() -> None:
    coord = CacheCoordinator()
    tag = CacheTag(type=_Order, key=1)
    await coord.put(_OrderAction, "1", "result", 100.0, tags=[tag])
    internal = CacheCoordinator._make_key(_OrderAction, "1")
    assert tag in coord._tag_to_keys
    assert internal in coord._tag_to_keys[tag]
    assert internal in coord._key_to_tags
    assert tag in coord._key_to_tags[internal]


@pytest.mark.asyncio
async def test_put_without_tags_does_not_populate_index() -> None:
    coord = CacheCoordinator()
    await coord.put(_OrderAction, "1", "result", 100.0, tags=None)
    assert len(coord._tag_to_keys) == 0
    assert len(coord._key_to_tags) == 0


@pytest.mark.asyncio
async def test_evict_by_exact_tag_removes_entry() -> None:
    coord = CacheCoordinator()
    tag = CacheTag(type=_Order, key=1)
    await coord.put(_OrderAction, "1", "result", 100.0, tags=[tag])
    evicted = await coord.evict_by_tags(frozenset({tag}))
    assert evicted == 1
    assert await coord.get_entry(_OrderAction, "1") is None


@pytest.mark.asyncio
async def test_evict_by_exact_tag_cleans_both_index_directions() -> None:
    coord = CacheCoordinator()
    tag = CacheTag(type=_Order, key=1)
    await coord.put(_OrderAction, "1", "result", 100.0, tags=[tag])
    await coord.evict_by_tags(frozenset({tag}))
    assert tag not in coord._tag_to_keys
    internal = CacheCoordinator._make_key(_OrderAction, "1")
    assert internal not in coord._key_to_tags


@pytest.mark.asyncio
async def test_evict_by_type_wildcard_removes_all_of_type() -> None:
    coord = CacheCoordinator()
    await coord.put(_OrderAction, "1", "r1", 100.0, tags=[CacheTag(type=_Order, key=1)])
    await coord.put(_OrderAction, "2", "r2", 100.0, tags=[CacheTag(type=_Order, key=2)])
    await coord.put(_PaymentAction, "p", "rp", 100.0, tags=[CacheTag(type=_Payment, key=1)])
    evicted = await coord.evict_by_tags(frozenset({CacheTag(type=_Order)}))
    assert evicted == 2
    assert await coord.get_entry(_OrderAction, "1") is None
    assert await coord.get_entry(_OrderAction, "2") is None
    assert await coord.get_entry(_PaymentAction, "p") is not None


@pytest.mark.asyncio
async def test_evict_by_key_wildcard_removes_all_with_key() -> None:
    coord = CacheCoordinator()
    await coord.put(_OrderAction, "o42", "ro", 100.0, tags=[CacheTag(type=_Order, key=42)])
    await coord.put(_PaymentAction, "p42", "rp", 100.0, tags=[CacheTag(type=_Payment, key=42)])
    await coord.put(_OrderAction, "o99", "r99", 100.0, tags=[CacheTag(type=_Order, key=99)])
    evicted = await coord.evict_by_tags(frozenset({CacheTag(key=42)}))
    assert evicted == 2
    assert await coord.get_entry(_OrderAction, "o42") is None
    assert await coord.get_entry(_PaymentAction, "p42") is None
    assert await coord.get_entry(_OrderAction, "o99") is not None


@pytest.mark.asyncio
async def test_evict_by_empty_frozenset_evicts_nothing() -> None:
    coord = CacheCoordinator()
    await coord.put(_OrderAction, "1", "result", 100.0, tags=[CacheTag(type=_Order, key=1)])
    evicted = await coord.evict_by_tags(frozenset())
    assert evicted == 0
    assert coord.size == 1


@pytest.mark.asyncio
async def test_evict_does_not_affect_untagged_entries() -> None:
    coord = CacheCoordinator()
    await coord.put(_OrderAction, "untagged", "result", 100.0, tags=None)
    evicted = await coord.evict_by_tags(frozenset({CacheTag(type=_Order)}))
    assert evicted == 0
    assert await coord.get_entry(_OrderAction, "untagged") is not None


@pytest.mark.asyncio
async def test_evict_returns_count_of_removed_entries() -> None:
    coord = CacheCoordinator()
    for i in range(5):
        await coord.put(_OrderAction, str(i), f"r{i}", 100.0, tags=[CacheTag(type=_Order, key=i)])
    evicted = await coord.evict_by_tags(frozenset({CacheTag(type=_Order)}))
    assert evicted == 5
    assert coord.size == 0


@pytest.mark.asyncio
async def test_put_overwrite_updates_tag_index() -> None:
    coord = CacheCoordinator()
    old_tag = CacheTag(type=_Order, key=1)
    new_tag = CacheTag(type=_Payment, key=99)
    await coord.put(_OrderAction, "x", "v1", 100.0, tags=[old_tag])
    await coord.put(_OrderAction, "x", "v2", 100.0, tags=[new_tag])
    internal = CacheCoordinator._make_key(_OrderAction, "x")
    assert old_tag not in coord._tag_to_keys
    assert new_tag in coord._tag_to_keys
    assert internal in coord._tag_to_keys[new_tag]


@pytest.mark.asyncio
async def test_invalidate_removes_entry_from_tag_index() -> None:
    coord = CacheCoordinator()
    tag = CacheTag(type=_Order, key=5)
    await coord.put(_OrderAction, "5", "result", 100.0, tags=[tag])
    await coord.invalidate(_OrderAction, "5")
    assert tag not in coord._tag_to_keys
    internal = CacheCoordinator._make_key(_OrderAction, "5")
    assert internal not in coord._key_to_tags


@pytest.mark.asyncio
async def test_clear_removes_all_tag_indexes() -> None:
    coord = CacheCoordinator()
    await coord.put(_OrderAction, "1", "r1", 100.0, tags=[CacheTag(type=_Order, key=1)])
    await coord.put(_PaymentAction, "2", "r2", 100.0, tags=[CacheTag(type=_Payment, key=2)])
    await coord.clear()
    assert len(coord._tag_to_keys) == 0
    assert len(coord._key_to_tags) == 0


@pytest.mark.asyncio
async def test_evict_multiple_directives_combined() -> None:
    coord = CacheCoordinator()
    await coord.put(_OrderAction, "o1", "r1", 100.0, tags=[CacheTag(type=_Order, key=1)])
    await coord.put(_PaymentAction, "p2", "r2", 100.0, tags=[CacheTag(type=_Payment, key=2)])
    await coord.put(_OrderAction, "o3", "r3", 100.0, tags=[CacheTag(type=_Order, key=3)])
    evicted = await coord.evict_by_tags(
        frozenset(
            {
                CacheTag(type=_Order, key=1),
                CacheTag(type=_Payment, key=2),
            }
        )
    )
    assert evicted == 2
    assert await coord.get_entry(_OrderAction, "o1") is None
    assert await coord.get_entry(_PaymentAction, "p2") is None
    assert await coord.get_entry(_OrderAction, "o3") is not None
