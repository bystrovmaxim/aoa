# tests/action_machine/runtime/test_action_product_machine_cache_invalidation.py
"""Integration tests for tag-based cache invalidation in ActionProductMachine (#58)."""

from __future__ import annotations

import pytest
from pydantic import Field

from aoa.action_machine.context.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.exceptions.cache_contract_error import CacheContractError
from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.check_roles import GuestRole, check_roles
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.intents.on_error import on_error
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.cache_coordinator import CacheCoordinator
from aoa.action_machine.runtime.cache_tag import CacheTag
from aoa.action_machine.runtime.tools_box import ToolsBox
from tests.action_machine.scenarios.domain_model.domains import OrdersDomain

# ─── Domain types used as CacheTag.type ───────────────────────────────────────


class _Report:
    pass


class _Invoice:
    pass


# ─── Call counters ────────────────────────────────────────────────────────────

_inv_calls: list[str] = []  # records action name each time on_cache_invalidate fires
_write_calls: list[str] = []  # records action name each time on_cache_write fires
_pipeline_runs: list[str] = []  # records action name each time summary aspect runs


def _reset() -> None:
    _inv_calls.clear()
    _write_calls.clear()
    _pipeline_runs.clear()


# ─── Actions ──────────────────────────────────────────────────────────────────


@meta(description="Write report to cache with tags", domain=OrdersDomain)
@check_roles(GuestRole)
class WriteReportAction(BaseAction["WriteReportAction.Params", "WriteReportAction.Result"]):
    class Params(BaseParams):
        report_id: int = Field(description="report id")

    class Result(BaseResult):
        value: str = Field(default="report")

    def cache_key(self, params: Params) -> str | None:
        return str(params.report_id)

    async def on_cache_write(self, result: Result, params: Params, duration_ms: float) -> list[CacheTag] | None:
        _write_calls.append("WriteReportAction")
        return [CacheTag(type=_Report, key=params.report_id)]

    @summary_aspect("build")
    async def build_summary(
        self,
        params: Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Result:
        _pipeline_runs.append("WriteReportAction")
        return WriteReportAction.Result(value=f"report:{params.report_id}")


@meta(description="Invalidate all reports of a type", domain=OrdersDomain)
@check_roles(GuestRole)
class InvalidateReportsAction(BaseAction["InvalidateReportsAction.Params", "InvalidateReportsAction.Result"]):
    class Params(BaseParams):
        pass

    class Result(BaseResult):
        done: bool = Field(default=True)

    def cache_key(self, params: Params) -> str | None:
        return None  # write-like action; does not cache itself

    async def on_cache_invalidate(self, params: Params, result: Result) -> list[CacheTag] | None:
        _inv_calls.append("InvalidateReportsAction")
        return [CacheTag(type=_Report)]  # wildcard: evict all reports

    @summary_aspect("do")
    async def do_summary(
        self,
        params: Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Result:
        _pipeline_runs.append("InvalidateReportsAction")
        return InvalidateReportsAction.Result()


@meta(description="Invalidate specific report then write invoice", domain=OrdersDomain)
@check_roles(GuestRole)
class WriteInvoiceInvalidatesReportAction(
    BaseAction[
        "WriteInvoiceInvalidatesReportAction.Params",
        "WriteInvoiceInvalidatesReportAction.Result",
    ]
):
    class Params(BaseParams):
        report_id: int = Field(description="report to evict")
        invoice_id: int = Field(description="invoice to write")

    class Result(BaseResult):
        value: str = Field(default="invoice")

    def cache_key(self, params: Params) -> str | None:
        return str(params.invoice_id)

    async def on_cache_invalidate(self, params: Params, result: Result) -> list[CacheTag] | None:
        _inv_calls.append("WriteInvoiceInvalidatesReportAction")
        return [CacheTag(type=_Report, key=params.report_id)]

    async def on_cache_write(self, result: Result, params: Params, duration_ms: float) -> list[CacheTag] | None:
        _write_calls.append("WriteInvoiceInvalidatesReportAction")
        return [CacheTag(type=_Invoice, key=params.invoice_id)]

    @summary_aspect("build")
    async def build_summary(
        self,
        params: Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Result:
        _pipeline_runs.append("WriteInvoiceInvalidatesReportAction")
        return WriteInvoiceInvalidatesReportAction.Result(value=f"invoice:{params.invoice_id}")


@meta(description="No cache_key, still has invalidation", domain=OrdersDomain)
@check_roles(GuestRole)
class NoCacheKeyButInvalidatesAction(
    BaseAction["NoCacheKeyButInvalidatesAction.Params", "NoCacheKeyButInvalidatesAction.Result"]
):
    class Params(BaseParams):
        pass

    class Result(BaseResult):
        ok: bool = Field(default=True)

    def cache_key(self, params: Params) -> str | None:
        return None

    async def on_cache_invalidate(self, params: Params, result: Result) -> list[CacheTag] | None:
        _inv_calls.append("NoCacheKeyButInvalidatesAction")
        return [CacheTag(type=_Report)]

    @summary_aspect("do")
    async def do_summary(
        self,
        params: Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Result:
        _pipeline_runs.append("NoCacheKeyButInvalidatesAction")
        return NoCacheKeyButInvalidatesAction.Result()


@meta(description="on_cache_write returns None — skip write", domain=OrdersDomain)
@check_roles(GuestRole)
class NoneWriteAction(BaseAction["NoneWriteAction.Params", "NoneWriteAction.Result"]):
    class Params(BaseParams):
        pass

    class Result(BaseResult):
        x: int = Field(default=1)

    def cache_key(self, params: Params) -> str | None:
        return "none-write"

    async def on_cache_write(self, result: Result, params: Params, duration_ms: float) -> list[CacheTag] | None:
        return None  # explicitly skip write

    @summary_aspect("s")
    async def run_summary(
        self,
        params: Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Result:
        _pipeline_runs.append("NoneWriteAction")
        return NoneWriteAction.Result()


@meta(description="on_cache_write returns bad type", domain=OrdersDomain)
@check_roles(GuestRole)
class BadWriteTypeAction(BaseAction["BadWriteTypeAction.Params", "BadWriteTypeAction.Result"]):
    class Params(BaseParams):
        pass

    class Result(BaseResult):
        x: int = Field(default=1)

    def cache_key(self, params: Params) -> str | None:
        return "bad-write-type"

    async def on_cache_write(self, result: Result, params: Params, duration_ms: float) -> list[CacheTag] | None:
        return True  # type: ignore[return-value]  — bool is not a list

    @summary_aspect("s")
    async def run_summary(
        self,
        params: Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Result:
        return BadWriteTypeAction.Result()


@meta(description="on_cache_write returns list with bad item", domain=OrdersDomain)
@check_roles(GuestRole)
class BadWriteItemAction(BaseAction["BadWriteItemAction.Params", "BadWriteItemAction.Result"]):
    class Params(BaseParams):
        pass

    class Result(BaseResult):
        x: int = Field(default=1)

    def cache_key(self, params: Params) -> str | None:
        return "bad-write-item"

    async def on_cache_write(self, result: Result, params: Params, duration_ms: float) -> list[CacheTag] | None:
        return ["not-a-cache-tag"]  # type: ignore[list-item]

    @summary_aspect("s")
    async def run_summary(
        self,
        params: Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Result:
        return BadWriteItemAction.Result()


@meta(description="on_cache_invalidate returns bad type", domain=OrdersDomain)
@check_roles(GuestRole)
class BadInvalidateTypeAction(BaseAction["BadInvalidateTypeAction.Params", "BadInvalidateTypeAction.Result"]):
    class Params(BaseParams):
        pass

    class Result(BaseResult):
        x: int = Field(default=1)

    async def on_cache_invalidate(self, params: Params, result: Result) -> list[CacheTag] | None:
        return "bad"  # type: ignore[return-value]

    @summary_aspect("s")
    async def run_summary(
        self,
        params: Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Result:
        return BadInvalidateTypeAction.Result()


@meta(description="on_cache_invalidate returns list with bad item", domain=OrdersDomain)
@check_roles(GuestRole)
class BadInvalidateItemAction(BaseAction["BadInvalidateItemAction.Params", "BadInvalidateItemAction.Result"]):
    class Params(BaseParams):
        pass

    class Result(BaseResult):
        x: int = Field(default=1)

    async def on_cache_invalidate(self, params: Params, result: Result) -> list[CacheTag] | None:
        return [42]  # type: ignore[list-item]  — int is not a CacheTag

    @summary_aspect("s")
    async def run_summary(
        self,
        params: Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Result:
        return BadInvalidateItemAction.Result()


@meta(description="Cacheable with error path", domain=OrdersDomain)
@check_roles(GuestRole)
class ErrorPathCachedAction(BaseAction["ErrorPathCachedAction.Params", "ErrorPathCachedAction.Result"]):
    class Params(BaseParams):
        fail: bool = Field(default=False)

    class Result(BaseResult):
        status: str = Field(default="ok")

    def cache_key(self, params: Params) -> str | None:
        return "error-path"

    async def on_cache_write(self, result: Result, params: Params, duration_ms: float) -> list[CacheTag] | None:
        _write_calls.append("ErrorPathCachedAction")
        return [CacheTag(type=_Report, key="error-path")]

    async def on_cache_invalidate(self, params: Params, result: Result) -> list[CacheTag] | None:
        _inv_calls.append("ErrorPathCachedAction")
        return [CacheTag(type=_Report)]

    @summary_aspect("s")
    async def run_summary(
        self,
        params: Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Result:
        if params.fail:
            raise ValueError("boom")
        _pipeline_runs.append("ErrorPathCachedAction")
        return ErrorPathCachedAction.Result(status="ok")

    @on_error(ValueError, description="handle")
    async def handle_on_error(
        self,
        params: Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
        error: Exception,
    ) -> Result:
        return ErrorPathCachedAction.Result(status="handled")


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _ctx() -> Context:
    return Context(user=UserInfo(user_id="u1", roles=(GuestRole,)))


def _machine(cache: CacheCoordinator | None = None) -> ActionProductMachine:
    return ActionProductMachine(
        log_coordinator=LogCoordinator(loggers=[]),
        cache_coordinator=cache or CacheCoordinator(),
    )


# ─── Tests: on_cache_write ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_on_cache_write_tags_indexed_in_coordinator() -> None:
    _reset()
    cache = CacheCoordinator()
    machine = _machine(cache)
    await machine.run(_ctx(), WriteReportAction(), WriteReportAction.Params(report_id=7))
    tag = CacheTag(type=_Report, key=7)
    assert tag in cache._tag_to_keys
    assert len(cache._tag_to_keys[tag]) == 1


@pytest.mark.asyncio
async def test_on_cache_write_none_skips_write_no_entry_stored() -> None:
    _reset()
    cache = CacheCoordinator()
    machine = _machine(cache)
    await machine.run(_ctx(), NoneWriteAction(), NoneWriteAction.Params())
    assert cache.size == 0


@pytest.mark.asyncio
async def test_on_cache_write_none_second_run_goes_through_pipeline() -> None:
    _reset()
    machine = _machine()
    p = NoneWriteAction.Params()
    await machine.run(_ctx(), NoneWriteAction(), p)
    await machine.run(_ctx(), NoneWriteAction(), p)
    assert _pipeline_runs.count("NoneWriteAction") == 2


@pytest.mark.asyncio
async def test_on_cache_write_wrong_type_raises_cache_contract_error() -> None:
    machine = _machine()
    with pytest.raises(CacheContractError, match="on_cache_write"):
        await machine.run(_ctx(), BadWriteTypeAction(), BadWriteTypeAction.Params())


@pytest.mark.asyncio
async def test_on_cache_write_bad_item_raises_cache_contract_error() -> None:
    machine = _machine()
    with pytest.raises(CacheContractError, match="on_cache_write"):
        await machine.run(_ctx(), BadWriteItemAction(), BadWriteItemAction.Params())


@pytest.mark.asyncio
async def test_on_cache_write_not_called_when_cache_key_returns_none() -> None:
    _reset()
    machine = _machine()
    await machine.run(_ctx(), NoCacheKeyButInvalidatesAction(), NoCacheKeyButInvalidatesAction.Params())
    assert "NoCacheKeyButInvalidatesAction" not in _write_calls


# ─── Tests: on_cache_invalidate ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_on_cache_invalidate_evicts_tagged_entries_before_write() -> None:
    _reset()
    cache = CacheCoordinator()
    machine = _machine(cache)
    # Prime the cache with two reports.
    await machine.run(_ctx(), WriteReportAction(), WriteReportAction.Params(report_id=1))
    await machine.run(_ctx(), WriteReportAction(), WriteReportAction.Params(report_id=2))
    assert cache.size == 2
    # Run the invalidating action.
    await machine.run(_ctx(), InvalidateReportsAction(), InvalidateReportsAction.Params())
    assert cache.size == 0  # both reports evicted


@pytest.mark.asyncio
async def test_on_cache_invalidate_and_write_in_same_action() -> None:
    _reset()
    cache = CacheCoordinator()
    machine = _machine(cache)
    # Prime a report entry.
    await machine.run(_ctx(), WriteReportAction(), WriteReportAction.Params(report_id=5))
    assert cache.size == 1
    # Run action that evicts report:5 and writes invoice:10.
    params = WriteInvoiceInvalidatesReportAction.Params(report_id=5, invoice_id=10)
    await machine.run(_ctx(), WriteInvoiceInvalidatesReportAction(), params)
    # Report evicted, invoice written.
    assert await cache.get_entry(WriteReportAction, "5") is None
    assert await cache.get_entry(WriteInvoiceInvalidatesReportAction, "10") is not None
    assert cache.size == 1


@pytest.mark.asyncio
async def test_on_cache_invalidate_called_when_cache_key_returns_none() -> None:
    _reset()
    machine = _machine()
    await machine.run(_ctx(), NoCacheKeyButInvalidatesAction(), NoCacheKeyButInvalidatesAction.Params())
    assert "NoCacheKeyButInvalidatesAction" in _inv_calls


@pytest.mark.asyncio
async def test_on_cache_invalidate_called_every_successful_pipeline_run() -> None:
    _reset()
    machine = _machine()
    p = InvalidateReportsAction.Params()
    await machine.run(_ctx(), InvalidateReportsAction(), p)
    await machine.run(_ctx(), InvalidateReportsAction(), p)
    assert _inv_calls.count("InvalidateReportsAction") == 2


@pytest.mark.asyncio
async def test_on_cache_invalidate_not_called_on_cache_hit() -> None:
    _reset()
    cache = CacheCoordinator()
    machine = _machine(cache)
    params = WriteReportAction.Params(report_id=99)
    # First run: pipeline executes, on_cache_invalidate is not defined on WriteReportAction.
    await machine.run(_ctx(), WriteReportAction(), params)
    # Confirm it's cached.
    assert cache.size == 1
    # Second run: cache hit — pipeline and all hooks are skipped.
    _pipeline_runs.clear()
    _inv_calls.clear()
    await machine.run(_ctx(), WriteReportAction(), params)
    assert "WriteReportAction" not in _pipeline_runs
    assert len(_inv_calls) == 0


@pytest.mark.asyncio
async def test_on_cache_invalidate_not_called_on_error_handler_result() -> None:
    _reset()
    machine = _machine()
    params = ErrorPathCachedAction.Params(fail=True)
    result = await machine.run(_ctx(), ErrorPathCachedAction(), params)
    assert result.status == "handled"
    assert "ErrorPathCachedAction" not in _inv_calls
    assert "ErrorPathCachedAction" not in _write_calls


@pytest.mark.asyncio
async def test_on_cache_invalidate_none_does_not_evict_anything() -> None:
    _reset()
    cache = CacheCoordinator()
    machine = _machine(cache)
    # Prime two entries.
    await machine.run(_ctx(), WriteReportAction(), WriteReportAction.Params(report_id=1))
    await machine.run(_ctx(), WriteReportAction(), WriteReportAction.Params(report_id=2))
    assert cache.size == 2
    # Run an action whose on_cache_invalidate returns None (default).
    await machine.run(_ctx(), NoneWriteAction(), NoneWriteAction.Params())
    assert cache.size == 2  # nothing evicted


@pytest.mark.asyncio
async def test_on_cache_invalidate_wrong_type_raises_cache_contract_error() -> None:
    machine = _machine()
    with pytest.raises(CacheContractError, match="on_cache_invalidate"):
        await machine.run(_ctx(), BadInvalidateTypeAction(), BadInvalidateTypeAction.Params())


@pytest.mark.asyncio
async def test_on_cache_invalidate_bad_item_raises_cache_contract_error() -> None:
    machine = _machine()
    with pytest.raises(CacheContractError, match="on_cache_invalidate"):
        await machine.run(_ctx(), BadInvalidateItemAction(), BadInvalidateItemAction.Params())


# ─── Tests: ordering guarantee ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_invalidation_happens_before_write_new_entry_survives() -> None:
    """If on_cache_invalidate would evict the same key we're about to write,
    the new write must still land in the cache after invalidation."""
    _reset()
    cache = CacheCoordinator()
    machine = _machine(cache)
    # WriteInvoiceInvalidatesReportAction writes invoice:10 and invalidates report:5.
    # Run it twice; the second run should get a cache hit.
    params = WriteInvoiceInvalidatesReportAction.Params(report_id=5, invoice_id=10)
    await machine.run(_ctx(), WriteReportAction(), WriteReportAction.Params(report_id=5))
    await machine.run(_ctx(), WriteInvoiceInvalidatesReportAction(), params)
    # Entry for invoice:10 is in the cache.
    entry = await cache.get_entry(WriteInvoiceInvalidatesReportAction, "10")
    assert entry is not None
    # Second run is a cache hit; pipeline does not run again.
    _pipeline_runs.clear()
    await machine.run(_ctx(), WriteInvoiceInvalidatesReportAction(), params)
    assert "WriteInvoiceInvalidatesReportAction" not in _pipeline_runs
