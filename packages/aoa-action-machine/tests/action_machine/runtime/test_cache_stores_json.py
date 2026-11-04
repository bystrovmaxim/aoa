# packages/aoa-action-machine/tests/action_machine/runtime/test_cache_stores_json.py
"""
The cache stores JSON: the store keeps bytes, and every hit reads a new Result.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Case 9.1 of issue #410. The machine writes ``result.model_dump_json()`` as UTF-8 to
the store and reads a hit with the action's Result type, so a caller that changes the
Result it received changes nothing another caller gets; ``@cache_read`` receives the
new Result with the stored metadata.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from aoa.action_machine.context.context import Context
from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.cache import cache_key, cache_read, cache_write
from aoa.action_machine.intents.check_roles import GuestRole, check_roles
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.model.params_stub import ParamsStub
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.cache_coordinator import CacheCoordinator
from aoa.action_machine.runtime.cache_entry import CacheEntry
from aoa.action_machine.runtime.cache_tag import CacheTag
from aoa.action_machine.runtime.tools_box import ToolsBox

from ...support.cache_model import CachedItemCoreEntity
from ...support.domain_model.domains import OrdersDomain

_read: list[CacheEntry] = []


class ItemsResult(BaseResult):
    """A Result with a list a caller could change."""

    names: list[str] = Field(description="Names")


@meta(description="A cached list", domain=OrdersDomain)
@check_roles(GuestRole)
class CachedListAction(BaseAction[ParamsStub, ItemsResult]):
    """Caches one list under one key and records what its read receives."""

    @cache_key("One key")
    async def list_cache_key(self, params: ParamsStub, box: ToolsBox, connections: Connections) -> str | None:
        return "list"

    @cache_read("Record the entry and keep it")
    async def list_cache_read(
        self, params: ParamsStub, box: ToolsBox, connections: Connections, entry: CacheEntry
    ) -> ItemsResult | None:
        _read.append(entry)
        return entry.result  # type: ignore[no-any-return]

    @cache_write("Keep the list", tags=(CachedItemCoreEntity,))
    async def list_cache_write(
        self, params: ParamsStub, box: ToolsBox, connections: Connections, result: ItemsResult, duration_ms: float
    ) -> list[CacheTag] | None:
        return [CacheTag(type=CachedItemCoreEntity, key="list")]

    @summary_aspect("Load the list")
    async def load_summary(
        self, params: ParamsStub, state: BaseState, box: ToolsBox, connections: Connections
    ) -> ItemsResult:
        return ItemsResult(names=["a"])


class RecordingCoordinator(CacheCoordinator):
    """The shipped store, recording what ``put`` receives."""

    def __init__(self) -> None:
        super().__init__()
        self.puts: list[Any] = []

    async def put(self, action_cls: type, user_key: str, payload: bytes, pipeline_duration_ms: float, tags: list[CacheTag] | None = None) -> None:
        self.puts.append(payload)
        await super().put(action_cls, user_key, payload, pipeline_duration_ms, tags)


def _machine(cache: CacheCoordinator) -> ActionProductMachine:
    return ActionProductMachine(log_coordinator=LogCoordinator(loggers=[]), cache_coordinator=cache)


async def test_a_hit_returns_a_new_result_a_caller_cannot_change() -> None:
    """Case 9.1: before, ``(['a', 'leak'], True)``; now the hit is another object with what was written."""
    machine = _machine(CacheCoordinator())
    first = await machine.run(Context(), CachedListAction(), ParamsStub())
    first.names.append("leak")
    second = await machine.run(Context(), CachedListAction(), ParamsStub())
    assert (second.names, first is second) == (["a"], False)


async def test_the_store_receives_the_results_json_bytes() -> None:
    """The store never sees a Result: ``put`` gets ``model_dump_json()`` in UTF-8."""
    cache = RecordingCoordinator()
    await _machine(cache).run(Context(), CachedListAction(), ParamsStub())
    assert cache.puts == [b'{"names":["a"]}']


async def test_the_read_receives_a_new_result_with_the_stored_metadata() -> None:
    """``@cache_read`` gets a CacheEntry: a Result read from the bytes, and the stored entry's metadata."""
    _read.clear()
    cache = CacheCoordinator()
    machine = _machine(cache)
    first = await machine.run(Context(), CachedListAction(), ParamsStub())
    await machine.run(Context(), CachedListAction(), ParamsStub())
    stored = await cache.get_entry(CachedListAction, "list")
    assert stored is not None
    (entry,) = _read
    assert isinstance(entry.result, ItemsResult) and entry.result is not first
    assert entry.result.names == ["a"]
    assert (entry.pipeline_duration_ms, entry.created_at) == (stored.pipeline_duration_ms, stored.created_at)
    assert entry.access_count == 1
