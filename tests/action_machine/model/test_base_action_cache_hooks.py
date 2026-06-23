# tests/action_machine/model/test_base_action_cache_hooks.py
"""Unit tests for optional cache hooks on ``BaseAction`` (PR-2)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.params_stub import ParamsStub
from aoa.action_machine.model.result_stub import ResultStub
from aoa.action_machine.runtime.cache_tag import CacheTag


@exclude_graph_model
class DefaultHooksAction(BaseAction[ParamsStub, ResultStub]):
    """Concrete action using default cache hook implementations."""

    pass


@exclude_graph_model
class KeyedCacheAction(BaseAction[ParamsStub, ResultStub]):
    def cache_key(self, params: ParamsStub) -> str | None:
        return "order:42"


@exclude_graph_model
class RejectStaleReadAction(BaseAction[ParamsStub, ResultStub]):
    async def read_cache(self, params: ParamsStub, entry: object) -> ResultStub | None:
        return None


@exclude_graph_model
class AllowWriteAction(BaseAction[ParamsStub, ResultStub]):
    async def on_cache_write(
        self,
        result: ResultStub,
        params: ParamsStub,
        duration_ms: float,
    ) -> list[CacheTag] | None:
        return [CacheTag(key="result")]


class TestDefaultCacheHooks:
    def test_default_cache_key_returns_none(self) -> None:
        assert DefaultHooksAction().cache_key(ParamsStub()) is None

    @pytest.mark.asyncio
    async def test_default_read_cache_returns_entry_result(self) -> None:
        params = ParamsStub()
        result = ResultStub()
        entry = SimpleNamespace(result=result, pipeline_duration_ms=12.5)
        got = await DefaultHooksAction().read_cache(params, entry)
        assert got is result

    @pytest.mark.asyncio
    async def test_default_on_cache_write_returns_none(self) -> None:
        params = ParamsStub()
        result = ResultStub()
        assert await DefaultHooksAction().on_cache_write(result, params, 3.0) is None


class TestSubclassCacheHooks:
    def test_subclass_can_override_cache_key(self) -> None:
        assert KeyedCacheAction().cache_key(ParamsStub()) == "order:42"

    @pytest.mark.asyncio
    async def test_subclass_can_reject_stale_via_read_cache_none(self) -> None:
        entry = SimpleNamespace(result=ResultStub(), pipeline_duration_ms=1.0)
        assert await RejectStaleReadAction().read_cache(ParamsStub(), entry) is None

    @pytest.mark.asyncio
    async def test_subclass_can_allow_write_via_on_cache_write_tags(self) -> None:
        params = ParamsStub()
        result = ResultStub()
        tags = await AllowWriteAction().on_cache_write(result, params, 7.0)
        assert isinstance(tags, list) and len(tags) == 1
        assert isinstance(tags[0], CacheTag)
