# tests/intents/plugins/test_plugin_coordinator_emit.py
"""Unit tests for ``PluginCoordinator`` event payload helpers."""

from __future__ import annotations

from typing import Any

import pytest

from action_machine.context.context import Context
from action_machine.context.user_info import UserInfo
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.plugin.events import (
    AfterRegularAspectEvent,
    AfterSummaryAspectEvent,
    BeforeRegularAspectEvent,
    BeforeSummaryAspectEvent,
    GlobalFinishEvent,
    GlobalStartEvent,
)
from action_machine.plugin.plugin_coordinator import PluginCoordinator
from tests.scenarios.domain_model import PingAction


class _RecordingPluginCtx:
    """Minimal stand-in for ``PluginRunContext`` — only ``emit_event`` is used."""

    def __init__(self) -> None:
        self.emitted: list[tuple[object, dict[str, Any]]] = []

    async def emit_event(self, event: object, **kwargs: Any) -> None:
        self.emitted.append((event, kwargs))


def test_base_fields_shape() -> None:
    """base_fields returns action_class, action_name, nest_level, context, params."""
    log = LogCoordinator(loggers=[])
    emit = PluginCoordinator([], log)
    action = PingAction()
    ctx = Context(user=UserInfo(user_id="u1", roles=()))
    params = PingAction.Params()

    fields = emit.base_fields(action, ctx, params, nest_level=2)

    assert fields["action_class"] is type(action)
    assert fields["action_name"] == action.get_full_class_name()
    assert fields["nest_level"] == 2
    assert fields["context"] is ctx
    assert fields["params"] is params


def test_emit_extra_kwargs_shape() -> None:
    """emit_extra_kwargs returns log_coordinator."""
    log = LogCoordinator(loggers=[])
    emit = PluginCoordinator([], log)

    extra = emit.emit_extra_kwargs(99)

    assert extra["log_coordinator"] is log


def test_properties_expose_config() -> None:
    """log_coordinator matches constructor."""
    log = LogCoordinator(loggers=[])
    emit = PluginCoordinator([], log)
    assert emit.log_coordinator is log


@pytest.mark.asyncio
async def test_emit_regular_aspect_helpers() -> None:
    """Before/after regular aspect events use base_fields and emit_extra_kwargs."""
    log = LogCoordinator(loggers=[])
    emit = PluginCoordinator([], log)
    action = PingAction()
    ctx = Context(user=UserInfo(user_id="u1", roles=()))
    params = PingAction.Params()
    plugin_ctx = _RecordingPluginCtx()

    await emit.emit_before_regular_aspect(
        plugin_ctx,
        action=action,
        context=ctx,
        params=params,
        nest_level=1,
        aspect_name="alpha_aspect",
        state_snapshot={"k": 1},
    )
    await emit.emit_after_regular_aspect(
        plugin_ctx,
        action=action,
        context=ctx,
        params=params,
        nest_level=1,
        aspect_name="alpha_aspect",
        state_snapshot={"k": 2},
        aspect_result={"out": True},
        duration_ms=42.0,
    )

    assert len(plugin_ctx.emitted) == 2
    ev0, kw0 = plugin_ctx.emitted[0]
    ev1, kw1 = plugin_ctx.emitted[1]
    assert isinstance(ev0, BeforeRegularAspectEvent)
    assert isinstance(ev1, AfterRegularAspectEvent)
    assert ev0.aspect_name == "alpha_aspect"
    assert ev1.aspect_name == "alpha_aspect"
    assert ev0.state_snapshot == {"k": 1}
    assert ev1.state_snapshot == {"k": 2}
    assert ev1.aspect_result == {"out": True}
    assert ev1.duration_ms == 42.0
    for kw in (kw0, kw1):
        assert kw["log_coordinator"] is log


@pytest.mark.asyncio
async def test_emit_summary_aspect_helpers() -> None:
    """Before/after summary aspect events carry state snapshot and result."""
    log = LogCoordinator(loggers=[])
    emit = PluginCoordinator([], log)
    action = PingAction()
    ctx = Context(user=UserInfo(user_id="u2", roles=()))
    params = PingAction.Params()
    plugin_ctx = _RecordingPluginCtx()
    result = PingAction.Result(message="pong")

    await emit.emit_before_summary_aspect(
        plugin_ctx,
        action=action,
        context=ctx,
        params=params,
        nest_level=0,
        aspect_name="pong_summary",
        state_snapshot={},
    )
    await emit.emit_after_summary_aspect(
        plugin_ctx,
        action=action,
        context=ctx,
        params=params,
        nest_level=0,
        aspect_name="pong_summary",
        state_snapshot={},
        result=result,
        duration_ms=7.5,
    )

    assert len(plugin_ctx.emitted) == 2
    ev0, _ = plugin_ctx.emitted[0]
    ev1, _ = plugin_ctx.emitted[1]
    assert isinstance(ev0, BeforeSummaryAspectEvent)
    assert isinstance(ev1, AfterSummaryAspectEvent)
    assert ev1.result is result
    assert ev1.duration_ms == 7.5


@pytest.mark.asyncio
async def test_emit_global_lifecycle_helpers() -> None:
    """Global start/finish events use base_fields and emit_extra_kwargs."""
    log = LogCoordinator(loggers=[])
    emit = PluginCoordinator([], log)
    action = PingAction()
    ctx = Context(user=UserInfo(user_id="g1", roles=()))
    params = PingAction.Params()
    plugin_ctx = _RecordingPluginCtx()
    result = PingAction.Result(message="pong")

    await emit.emit_global_start(
        plugin_ctx,
        action=action,
        context=ctx,
        params=params,
        nest_level=3,
    )
    await emit.emit_global_finish(
        plugin_ctx,
        action=action,
        context=ctx,
        params=params,
        nest_level=3,
        result=result,
        duration_ms=100.0,
    )

    assert len(plugin_ctx.emitted) == 2
    ev0, kw0 = plugin_ctx.emitted[0]
    ev1, kw1 = plugin_ctx.emitted[1]
    assert isinstance(ev0, GlobalStartEvent)
    assert isinstance(ev1, GlobalFinishEvent)
    assert ev0.nest_level == 3
    assert ev1.nest_level == 3
    assert ev1.result is result
    assert ev1.duration_ms == 100.0
    for kw in (kw0, kw1):
        assert kw["log_coordinator"] is log
