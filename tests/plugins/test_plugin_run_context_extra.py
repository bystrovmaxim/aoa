"""Extra branch tests for PluginRunContext internals."""

from __future__ import annotations

import pytest

from action_machine.intents.plugins.events import GlobalStartEvent
from action_machine.intents.plugins.plugin import Plugin
from action_machine.intents.plugins.plugin_run_context import PluginRunContext
from action_machine.intents.plugins.subscription_info import SubscriptionInfo


class _P(Plugin):
    async def get_initial_state(self) -> dict:
        return {"n": 0}

    def get_handlers(self, event):
        return []


class _CoordOk:
    def get(self, cls):
        return object()

    def get_snapshot(self, cls, facet_key: str):
        if facet_key != "meta":
            return None

        class _Snap:
            domain = str

        return _Snap()


class _CoordFail:
    def get(self, cls):
        raise RuntimeError("boom")

    def get_snapshot(self, cls, facet_key: str):
        raise RuntimeError("boom")


@pytest.mark.anyio
async def test_plugin_run_context_filter_and_run_branches() -> None:
    p = _P()
    ctx = PluginRunContext([p], {id(p): {"n": 0}})
    ev = GlobalStartEvent(
        action_class=123,  # type: ignore[arg-type]
        action_name="XAction",
        nest_level=0,
        context=None,  # type: ignore[arg-type]
        params=None,  # type: ignore[arg-type]
    )
    sub = SubscriptionInfo(
        event_class=GlobalStartEvent,
        method_name="on_x",
        action_class=(type,),
        action_name_pattern="Action",
        nest_level=(0,),
        domain=str,
        predicate=lambda e: True,
    )
    # action_class not type -> False
    assert not PluginRunContext._matches_all_filters(ev, sub, _CoordOk())

    ev2 = GlobalStartEvent(
        action_class=type,
        action_name="XAction",
        nest_level=0,
        context=None,  # type: ignore[arg-type]
        params=None,  # type: ignore[arg-type]
    )
    assert not PluginRunContext._matches_all_filters(ev2, sub, _CoordFail())
    assert PluginRunContext._matches_all_filters(ev2, sub, _CoordOk())

    # parallel branch with empty tasks
    await ctx._run_parallel([], ev2, None, "M", "test")  # pylint: disable=protected-access


@pytest.mark.anyio
async def test_plugin_run_context_sequential_error_paths() -> None:
    p = _P()
    ctx = PluginRunContext([p], {id(p): {"n": 0}})
    ev = GlobalStartEvent(
        action_class=type,
        action_name="XAction",
        nest_level=0,
        context=None,  # type: ignore[arg-type]
        params=None,  # type: ignore[arg-type]
    )

    async def _bad(plugin, state, event, log):
        raise ValueError("x")

    sub_ignore = SubscriptionInfo(event_class=GlobalStartEvent, method_name="on_x", ignore_exceptions=True)
    await ctx._run_sequential([(p, _bad, sub_ignore)], ev, None, "M", "test")  # pylint: disable=protected-access

    sub_critical = SubscriptionInfo(event_class=GlobalStartEvent, method_name="on_x", ignore_exceptions=False)
    with pytest.raises(ValueError):
        await ctx._run_sequential([(p, _bad, sub_critical)], ev, None, "M", "test")  # pylint: disable=protected-access
