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

import pytest
from pydantic import Field, field_serializer

from aoa.action_machine.context.context import Context
from aoa.action_machine.exceptions.cache_contract_error import CacheContractError
from aoa.action_machine.exceptions.cache_serialization_error import CacheSerializationError
from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.cache import cache_key, cache_read, cache_write
from aoa.action_machine.intents.check_roles import GuestRole, check_roles
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.model.stub_params import StubParams
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
class CachedListAction(BaseAction[StubParams, ItemsResult]):
    """Caches one list under one key and records what its read receives."""

    @cache_key("One key")
    async def list_cache_key(self, params: StubParams, box: ToolsBox, connections: Connections) -> str | None:
        return "list"

    @cache_read("Record the entry and keep it")
    async def list_cache_read(
        self, params: StubParams, box: ToolsBox, connections: Connections, entry: CacheEntry
    ) -> ItemsResult | None:
        _read.append(entry)
        return entry.result  # type: ignore[no-any-return]

    @cache_write("Keep the list", tags=(CachedItemCoreEntity,))
    async def list_cache_write(
        self, params: StubParams, box: ToolsBox, connections: Connections, result: ItemsResult, duration_ms: float
    ) -> list[CacheTag] | None:
        return [CacheTag(type=CachedItemCoreEntity, key="list")]

    @summary_aspect("Load the list")
    async def load_summary(
        self, params: StubParams, state: BaseState, box: ToolsBox, connections: Connections
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
    first = await machine.run(Context(), CachedListAction(), StubParams())
    first.names.append("leak")
    second = await machine.run(Context(), CachedListAction(), StubParams())
    assert (second.names, first is second) == (["a"], False)


async def test_the_store_receives_the_results_json_bytes() -> None:
    """The store never sees a Result: ``put`` gets ``model_dump_json()`` in UTF-8."""
    cache = RecordingCoordinator()
    await _machine(cache).run(Context(), CachedListAction(), StubParams())
    assert cache.puts == [b'{"names":["a"]}']


async def test_the_read_receives_a_new_result_with_the_stored_metadata() -> None:
    """``@cache_read`` gets a CacheEntry: a Result read from the bytes, and the stored entry's metadata."""
    _read.clear()
    cache = CacheCoordinator()
    machine = _machine(cache)
    first = await machine.run(Context(), CachedListAction(), StubParams())
    await machine.run(Context(), CachedListAction(), StubParams())
    stored = await cache.get_entry(CachedListAction, "list")
    assert stored is not None
    (entry,) = _read
    assert isinstance(entry.result, ItemsResult) and entry.result is not first
    assert entry.result.names == ["a"]
    assert (entry.pipeline_duration_ms, entry.created_at) == (stored.pipeline_duration_ms, stored.created_at)
    assert entry.access_count == 1


# ─── 9.2: a Result that does not read back is refused at the write ─────────────


class Frame:
    """A plain Python class, like a DataFrame."""


@meta(description="ReportAction for the read-back tests", domain=OrdersDomain)
@check_roles(GuestRole)
class ReportAction(BaseAction[StubParams, "ReportAction.Result"]):
    """Its Result has a JSON Schema and holds a value that has no JSON form."""

    class Result(BaseResult):
        summary: str = Field(description="Summary")
        data: Any = Field(description="Raw data")

    @cache_key("One key")
    async def picked_cache_key(self, params: StubParams, box: ToolsBox, connections: Connections) -> str | None:
        return "ReportAction"

    @cache_write("Keep it", tags=(CachedItemCoreEntity,))
    async def picked_cache_write(
        self, params: StubParams, box: ToolsBox, connections: Connections, result: ReportAction.Result, duration_ms: float
    ) -> list[CacheTag] | None:
        return []

    @summary_aspect("Answer")
    async def picked_summary(
        self, params: StubParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> ReportAction.Result:
        return ReportAction.Result(summary="ok", data=Frame())


@meta(description="CountAction for the read-back tests", domain=OrdersDomain)
@check_roles(GuestRole)
class CountAction(BaseAction[StubParams, "CountAction.Result"]):
    """Its Result writes its count as text its own field does not accept."""

    class Result(BaseResult):
        count: int = Field(description="Count")

        @field_serializer("count")
        def _count_text(self, value: int) -> str:
            return f"{value} items"

    @cache_key("One key")
    async def picked_cache_key(self, params: StubParams, box: ToolsBox, connections: Connections) -> str | None:
        return "CountAction"

    @cache_write("Keep it", tags=(CachedItemCoreEntity,))
    async def picked_cache_write(
        self, params: StubParams, box: ToolsBox, connections: Connections, result: CountAction.Result, duration_ms: float
    ) -> list[CacheTag] | None:
        return []

    @summary_aspect("Answer")
    async def picked_summary(
        self, params: StubParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> CountAction.Result:
        return CountAction.Result(count=2)


@meta(description="FloorAction for the read-back tests", domain=OrdersDomain)
@check_roles(GuestRole)
class FloorAction(BaseAction[StubParams, "FloorAction.Result"]):
    """Its Result writes its count as another valid count."""

    class Result(BaseResult):
        count: int = Field(description="Count")

        @field_serializer("count")
        def _floor(self, value: int) -> int:
            return value // 10 * 10

    @cache_key("One key")
    async def picked_cache_key(self, params: StubParams, box: ToolsBox, connections: Connections) -> str | None:
        return "FloorAction"

    @cache_write("Keep it", tags=(CachedItemCoreEntity,))
    async def picked_cache_write(
        self, params: StubParams, box: ToolsBox, connections: Connections, result: FloorAction.Result, duration_ms: float
    ) -> list[CacheTag] | None:
        return []

    @summary_aspect("Answer")
    async def picked_summary(
        self, params: StubParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> FloorAction.Result:
        return FloorAction.Result(count=29)


REFUSED = {
    "report": (
        ReportAction,
        "ReportAction.Result cannot be cached: field 'data' has no JSON form (Unable to serialize unknown type: <class 'tests.action_machine.runtime.test_cache_stores_json.Frame'>).",
    ),
    "count": (
        CountAction,
        "CountAction.Result cannot be cached: field 'count' does not read back from its own JSON ('2 items': int_parsing).",
    ),
    "floor": (FloorAction, "FloorAction.Result cannot be cached: field 'count' reads back as 20, but was 29."),
}


@pytest.mark.parametrize("picked", sorted(REFUSED))
async def test_a_result_that_does_not_read_back_is_refused_and_not_stored(picked: str) -> None:
    """Case 9.2: the three kinds the build check cannot see; nothing is stored."""
    action_cls, message = REFUSED[picked]
    cache = RecordingCoordinator()
    with pytest.raises(CacheSerializationError) as refused:
        await _machine(cache).run(Context(), action_cls(), StubParams())
    assert str(refused.value) == message
    assert isinstance(refused.value, CacheContractError)
    assert cache.puts == [] and cache.size == 0


async def test_an_action_that_does_not_cache_never_serializes() -> None:
    """Only a write serializes: a machine without a cache returns the same Result as it is."""
    action_cls, _ = REFUSED["report"]
    machine = ActionProductMachine(log_coordinator=LogCoordinator(loggers=[]), cache_coordinator=None)
    result = await machine.run(Context(), action_cls(), StubParams())
    assert isinstance(result.data, Frame)


# ─── 9.3: a stored entry that no longer reads ─────────────────────────────────


_runs: list[str] = []


@meta(description="A list whose stored JSON an old version wrote", domain=OrdersDomain)
@check_roles(GuestRole)
class RenamedListAction(BaseAction[StubParams, ItemsResult]):
    """Counts its runs and its reads."""

    @cache_key("One key")
    async def renamed_cache_key(self, params: StubParams, box: ToolsBox, connections: Connections) -> str | None:
        return "list"

    @cache_read("Count the reads")
    async def renamed_cache_read(
        self, params: StubParams, box: ToolsBox, connections: Connections, entry: CacheEntry
    ) -> ItemsResult | None:
        _runs.append("read")
        return entry.result  # type: ignore[no-any-return]

    @cache_write("Keep it", tags=(CachedItemCoreEntity,))
    async def renamed_cache_write(
        self, params: StubParams, box: ToolsBox, connections: Connections, result: ItemsResult, duration_ms: float
    ) -> list[CacheTag] | None:
        return []

    @summary_aspect("Load")
    async def load_summary(
        self, params: StubParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> ItemsResult:
        _runs.append("run")
        return ItemsResult(names=["a"])


async def test_an_entry_that_no_longer_reads_is_dropped_and_the_pipeline_runs() -> None:
    """Case 9.3: bytes an earlier Result wrote are stale; the next entry is fresh and read."""
    _runs.clear()
    cache = CacheCoordinator()
    await cache.put(RenamedListAction, "list", b'{"items":["old"]}', 5.0)
    machine = _machine(cache)
    first = await machine.run(Context(), RenamedListAction(), StubParams())
    second = await machine.run(Context(), RenamedListAction(), StubParams())
    assert (first.names, second.names) == (["a"], ["a"])
    assert _runs == ["run", "read"]
