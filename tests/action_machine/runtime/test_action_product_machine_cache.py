# tests/action_machine/runtime/test_action_product_machine_cache.py
"""Integration tests for ``ActionProductMachine`` optional action cache (PR-3)."""

from __future__ import annotations

from typing import Any, ClassVar

import pytest
from pydantic import Field

from aoa.action_machine.context.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.exceptions.authorization_error import AuthorizationError
from aoa.action_machine.exceptions.cache_contract_error import CacheContractError
from aoa.action_machine.intents.aspects.regular_aspect_decorator import regular_aspect
from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.check_roles import NoneRole, check_roles
from aoa.action_machine.intents.checkers import result_string
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.intents.on import on
from aoa.action_machine.intents.on_error import on_error
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.plugin.events import AspectEvent, GlobalLifecycleEvent
from aoa.action_machine.plugin.plugin import Plugin
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.cache_coordinator import CacheCoordinator
from aoa.action_machine.runtime.cache_entry import CacheEntry
from aoa.action_machine.runtime.tools_box import ToolsBox
from tests.action_machine.scenarios.domain_model.domains import OrdersDomain
from tests.action_machine.scenarios.domain_model.error_actions import ErrorTestParams, ErrorTestResult
from tests.action_machine.scenarios.domain_model.roles import ManagerRole

_summary_counter: dict[str, int] = {"n": 0}


def _reset_summary_counter() -> None:
    _summary_counter["n"] = 0


_error_aspect_calls = {"n": 0}


def _reset_error_aspect_calls() -> None:
    _error_aspect_calls["n"] = 0


# ─── Plugin: record event type names ─────────────────────────────────────────


class _EventNameRecorder(Plugin):
    def __init__(self, names: list[str]) -> None:
        self._names = names

    async def get_initial_state(self) -> dict[str, Any]:
        return {}

    @on(GlobalLifecycleEvent)
    async def on_global_lifecycle(
        self,
        state: dict[str, Any],
        event: GlobalLifecycleEvent,
        log: Any,
    ) -> dict[str, Any]:
        self._names.append(type(event).__name__)
        return state

    @on(AspectEvent)
    async def on_aspect_event(
        self,
        state: dict[str, Any],
        event: AspectEvent,
        log: Any,
    ) -> dict[str, Any]:
        self._names.append(type(event).__name__)
        return state


# ─── Actions under test (module-level → graph inspector registration) ──────


@meta(description="Cacheable counting summary", domain=OrdersDomain)
@check_roles(NoneRole)
class CacheableCountingAction(BaseAction["CacheableCountingAction.Params", "CacheableCountingAction.Result"]):
    class Params(BaseParams):
        pass

    class Result(BaseResult):
        n: int = Field(description="run ordinal")

    def cache_key(self, params: Params) -> str | None:
        return "fixed-key"

    async def on_cache_write(
        self,
        result: Result,
        params: Params,
        duration_ms: float,
    ) -> bool:
        return True

    @summary_aspect("count")
    async def summary(
        self,
        params: Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Result:
        _summary_counter["n"] += 1
        return CacheableCountingAction.Result(n=_summary_counter["n"])


@meta(description="Per-user cache key", domain=OrdersDomain)
@check_roles(NoneRole)
class PerUserOrderCacheAction(BaseAction["PerUserOrderCacheAction.Params", "PerUserOrderCacheAction.Result"]):
    class Params(BaseParams):
        user_id: str = Field(description="user")
        order_id: str = Field(description="order")

    class Result(BaseResult):
        n: int = Field(description="run ordinal")

    def cache_key(self, params: Params) -> str | None:
        return f"{params.user_id}:{params.order_id}"

    async def on_cache_write(
        self,
        result: Result,
        params: Params,
        duration_ms: float,
    ) -> bool:
        return True

    @summary_aspect("sum")
    async def summary(
        self,
        params: Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Result:
        _summary_counter["n"] += 1
        return PerUserOrderCacheAction.Result(n=_summary_counter["n"])


_reject_next_read: ClassVar[bool] = False


@meta(description="Stale read once", domain=OrdersDomain)
@check_roles(NoneRole)
class StaleReadCacheAction(BaseAction["StaleReadCacheAction.Params", "StaleReadCacheAction.Result"]):
    class Params(BaseParams):
        pass

    class Result(BaseResult):
        tag: str = Field(default="v1")

    def cache_key(self, params: Params) -> str | None:
        return "stale-key"

    async def read_cache(self, params: Params, entry: CacheEntry) -> Result | None:
        if StaleReadCacheAction._reject_next_read:
            return None
        return await super().read_cache(params, entry)

    async def on_cache_write(
        self,
        result: Result,
        params: Params,
        duration_ms: float,
    ) -> bool:
        return True

    @summary_aspect("s")
    async def summary(
        self,
        params: Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Result:
        return StaleReadCacheAction.Result(tag="fresh")


@meta(description="Bad read_cache dict", domain=OrdersDomain)
@check_roles(NoneRole)
class BadDictReadCacheAction(BaseAction["BadDictReadCacheAction.Params", "BadDictReadCacheAction.Result"]):
    class Params(BaseParams):
        pass

    class Result(BaseResult):
        x: int = Field(default=1)

    def cache_key(self, params: Params) -> str | None:
        return "dict-bad"

    async def read_cache(self, params: Params, entry: CacheEntry) -> Result | None:
        return {}  # type: ignore[return-value]

    async def on_cache_write(
        self,
        result: Result,
        params: Params,
        duration_ms: float,
    ) -> bool:
        return True

    @summary_aspect("s")
    async def summary(
        self,
        params: Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Result:
        return BadDictReadCacheAction.Result(x=1)


@meta(description="Empty cache key", domain=OrdersDomain)
@check_roles(NoneRole)
class EmptyKeyCacheAction(BaseAction["EmptyKeyCacheAction.Params", "EmptyKeyCacheAction.Result"]):
    class Params(BaseParams):
        pass

    class Result(BaseResult):
        x: int = Field(default=0)

    def cache_key(self, params: Params) -> str | None:
        return ""

    @summary_aspect("s")
    async def summary(
        self,
        params: Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Result:
        return EmptyKeyCacheAction.Result(x=1)


@meta(description="Invalid on_cache_write type", domain=OrdersDomain)
@check_roles(NoneRole)
class BadWriteDecisionAction(BaseAction["BadWriteDecisionAction.Params", "BadWriteDecisionAction.Result"]):
    class Params(BaseParams):
        pass

    class Result(BaseResult):
        x: int = Field(default=0)

    def cache_key(self, params: Params) -> str | None:
        return "bad-write"

    async def on_cache_write(
        self,
        result: Result,
        params: Params,
        duration_ms: float,
    ) -> bool:
        return 1  # type: ignore[return-value]

    @summary_aspect("s")
    async def summary(
        self,
        params: Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Result:
        return BadWriteDecisionAction.Result(x=1)


@meta(description="on_cache_write boom", domain=OrdersDomain)
@check_roles(NoneRole)
class BoomWriteCacheAction(BaseAction["BoomWriteCacheAction.Params", "BoomWriteCacheAction.Result"]):
    class Params(BaseParams):
        pass

    class Result(BaseResult):
        x: int = Field(default=0)

    def cache_key(self, params: Params) -> str | None:
        return "boom-write"

    async def on_cache_write(
        self,
        result: Result,
        params: Params,
        duration_ms: float,
    ) -> bool:
        raise RuntimeError("write boom")

    @summary_aspect("s")
    async def summary(
        self,
        params: Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Result:
        return BoomWriteCacheAction.Result(x=1)


@meta(description="read_cache boom on hit", domain=OrdersDomain)
@check_roles(NoneRole)
class BoomReadCacheAction(BaseAction["BoomReadCacheAction.Params", "BoomReadCacheAction.Result"]):
    class Params(BaseParams):
        pass

    class Result(BaseResult):
        x: int = Field(default=0)

    def cache_key(self, params: Params) -> str | None:
        return "boom-read"

    async def read_cache(self, params: Params, entry: CacheEntry) -> Result | None:
        raise RuntimeError("read boom")

    async def on_cache_write(
        self,
        result: Result,
        params: Params,
        duration_ms: float,
    ) -> bool:
        return True

    @summary_aspect("s")
    async def summary(
        self,
        params: Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Result:
        return BoomReadCacheAction.Result(x=1)


@meta(description="Manager-only cache", domain=OrdersDomain)
@check_roles(ManagerRole)
class ManagerOnlyCacheAction(BaseAction["ManagerOnlyCacheAction.Params", "ManagerOnlyCacheAction.Result"]):
    class Params(BaseParams):
        pass

    class Result(BaseResult):
        ok: bool = Field(default=True)

    def cache_key(self, params: Params) -> str | None:
        return "mgr-secret"

    async def on_cache_write(
        self,
        result: Result,
        params: Params,
        duration_ms: float,
    ) -> bool:
        return True

    @summary_aspect("s")
    async def summary(
        self,
        params: Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Result:
        return ManagerOnlyCacheAction.Result(ok=True)


@meta(description="Error path + cache write True", domain=OrdersDomain)
@check_roles(NoneRole)
class CacheableErrorHandledAction(BaseAction[ErrorTestParams, ErrorTestResult]):
    """Like ``ErrorHandledAction`` with stable ``cache_key`` and ``on_cache_write`` True."""

    def cache_key(self, params: ErrorTestParams) -> str | None:
        return f"err:{params.value}:{params.should_fail}"

    async def on_cache_write(
        self,
        result: ErrorTestResult,
        params: ErrorTestParams,
        duration_ms: float,
    ) -> bool:
        return True

    @regular_aspect("Process value")
    @result_string("processed", required=True)
    async def process_aspect(
        self,
        params: ErrorTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> dict[str, Any]:
        _error_aspect_calls["n"] += 1
        if params.should_fail:
            raise ValueError(f"Processing error: {params.value}")
        return {"processed": params.value}

    @summary_aspect("Build result")
    async def build_result_summary(
        self,
        params: ErrorTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> ErrorTestResult:
        return ErrorTestResult(status="ok", detail=state["processed"])

    @on_error(ValueError, description="Handle validation error")
    async def handle_validation_on_error(
        self,
        params: ErrorTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
        error: Exception,
    ) -> ErrorTestResult:
        return ErrorTestResult(status="handled", detail=str(error))


# ─── Helpers ───────────────────────────────────────────────────────────────


def _ctx_manager() -> Context:
    return Context(user=UserInfo(user_id="mgr", roles=(ManagerRole,)))


def _ctx_anon() -> Context:
    return Context(user=UserInfo(user_id="anon", roles=()))


def _machine(
    names: list[str] | None = None,
    *,
    no_cache: bool = False,
    cache: CacheCoordinator | None = None,
) -> ActionProductMachine:
    plugins: list[Plugin] = []
    if names is not None:
        plugins.append(_EventNameRecorder(names))
    if no_cache:
        cc: CacheCoordinator | None = None
    elif cache is not None:
        cc = cache
    else:
        cc = CacheCoordinator()
    return ActionProductMachine(
        log_coordinator=LogCoordinator(loggers=[]),
        plugins=plugins,
        cache_coordinator=cc,
    )


# ─── Tests ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_no_cache_coordinator_runs_pipeline_each_time() -> None:
    _reset_summary_counter()
    machine = _machine(no_cache=True)
    ctx = _ctx_manager()
    p = CacheableCountingAction.Params()
    r1 = await machine.run(ctx, CacheableCountingAction(), p)
    r2 = await machine.run(ctx, CacheableCountingAction(), p)
    assert r1.n == 1 and r2.n == 2


@pytest.mark.asyncio
async def test_cache_hit_skips_second_summary() -> None:
    _reset_summary_counter()
    machine = _machine()
    ctx = _ctx_manager()
    p = CacheableCountingAction.Params()
    r1 = await machine.run(ctx, CacheableCountingAction(), p)
    r2 = await machine.run(ctx, CacheableCountingAction(), p)
    assert r1.n == 1 and r2.n == 1
    assert _summary_counter["n"] == 1


@pytest.mark.asyncio
async def test_unauthorized_after_cache_does_not_return_cached() -> None:
    cache = CacheCoordinator()
    machine = _machine(cache=cache)
    ctx_ok = _ctx_manager()
    await machine.run(ctx_ok, ManagerOnlyCacheAction(), ManagerOnlyCacheAction.Params())
    with pytest.raises(AuthorizationError):
        await machine.run(_ctx_anon(), ManagerOnlyCacheAction(), ManagerOnlyCacheAction.Params())


@pytest.mark.asyncio
async def test_cache_hit_emits_global_lifecycle_but_not_aspect_events() -> None:
    names: list[str] = []
    machine = _machine(names=names)
    ctx = _ctx_manager()
    p = CacheableCountingAction.Params()
    await machine.run(ctx, CacheableCountingAction(), p)
    names.clear()
    await machine.run(ctx, CacheableCountingAction(), p)
    assert "GlobalStartEvent" in names
    assert "GlobalFinishEvent" in names
    assert not any(n.startswith("Before") or n.startswith("After") for n in names if "Aspect" in n)


@pytest.mark.asyncio
async def test_different_users_do_not_share_cache_entry() -> None:
    _reset_summary_counter()
    machine = _machine()
    ctx = _ctx_manager()
    oid = "order-99"
    await machine.run(
        ctx,
        PerUserOrderCacheAction(),
        PerUserOrderCacheAction.Params(user_id="u1", order_id=oid),
    )
    await machine.run(
        ctx,
        PerUserOrderCacheAction(),
        PerUserOrderCacheAction.Params(user_id="u2", order_id=oid),
    )
    r3 = await machine.run(
        ctx,
        PerUserOrderCacheAction(),
        PerUserOrderCacheAction.Params(user_id="u1", order_id=oid),
    )
    assert _summary_counter["n"] == 2
    assert r3.n == 1


@pytest.mark.asyncio
async def test_stale_read_invalidates_and_reruns_pipeline() -> None:
    StaleReadCacheAction._reject_next_read = False
    machine = _machine()
    ctx = _ctx_manager()
    p = StaleReadCacheAction.Params()
    r1 = await machine.run(ctx, StaleReadCacheAction(), p)
    assert r1.tag == "fresh"
    StaleReadCacheAction._reject_next_read = True
    r2 = await machine.run(ctx, StaleReadCacheAction(), p)
    assert r2.tag == "fresh"
    StaleReadCacheAction._reject_next_read = False
    r3 = await machine.run(ctx, StaleReadCacheAction(), p)
    assert r3.tag == "fresh"


@pytest.mark.asyncio
async def test_read_cache_wrong_type_raises_cache_contract_error() -> None:
    machine = _machine()
    ctx = _ctx_manager()
    # Prime cache with valid pipeline (default read_cache not used on write path)
    await machine.run(ctx, BadDictReadCacheAction(), BadDictReadCacheAction.Params())
    with pytest.raises(CacheContractError, match="read_cache"):
        await machine.run(ctx, BadDictReadCacheAction(), BadDictReadCacheAction.Params())


@pytest.mark.asyncio
async def test_empty_cache_key_raises_cache_contract_error() -> None:
    machine = _machine()
    ctx = _ctx_manager()
    with pytest.raises(CacheContractError, match="cache_key"):
        await machine.run(ctx, EmptyKeyCacheAction(), EmptyKeyCacheAction.Params())


@pytest.mark.asyncio
async def test_on_cache_write_non_bool_raises_cache_contract_error() -> None:
    machine = _machine()
    ctx = _ctx_manager()
    with pytest.raises(CacheContractError, match="on_cache_write"):
        await machine.run(ctx, BadWriteDecisionAction(), BadWriteDecisionAction.Params())


@pytest.mark.asyncio
async def test_on_cache_write_exception_no_global_finish() -> None:
    names: list[str] = []
    machine = _machine(names=names)
    ctx = _ctx_manager()
    with pytest.raises(RuntimeError, match="write boom"):
        await machine.run(ctx, BoomWriteCacheAction(), BoomWriteCacheAction.Params())
    assert "GlobalStartEvent" in names
    assert "GlobalFinishEvent" not in names


@pytest.mark.asyncio
async def test_read_cache_exception_after_prime_no_global_finish() -> None:
    names: list[str] = []
    machine = _machine(names=names)
    ctx = _ctx_manager()
    p = BoomReadCacheAction.Params()
    await machine.run(ctx, BoomReadCacheAction(), p)
    names.clear()
    with pytest.raises(RuntimeError, match="read boom"):
        await machine.run(ctx, BoomReadCacheAction(), p)
    assert names == ["GlobalStartEvent"]


@pytest.mark.asyncio
async def test_handled_on_error_result_not_cached_second_run_runs_pipeline() -> None:
    _reset_error_aspect_calls()
    machine = _machine()
    ctx = _ctx_manager()
    params = ErrorTestParams(value="x", should_fail=True)
    r1 = await machine.run(ctx, CacheableErrorHandledAction(), params)
    assert r1.status == "handled"
    r2 = await machine.run(ctx, CacheableErrorHandledAction(), params)
    assert r2.status == "handled"
    assert _error_aspect_calls["n"] == 2

