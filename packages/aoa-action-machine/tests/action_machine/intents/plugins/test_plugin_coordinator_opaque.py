# tests/action_machine/intents/plugins/test_plugin_coordinator_opaque.py
"""Unit tests for PluginCoordinator.emit_after_regular_aspect opaque_fields propagation."""

from __future__ import annotations

from typing import Any

import pytest

from aoa.action_machine.context.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.plugin.core.events import AfterRegularAspectEvent
from aoa.action_machine.plugin.core.plugin_coordinator import PluginCoordinator

from ....support.domain_model import PingAction


class _RecordingPluginCtx:
    def __init__(self) -> None:
        self.emitted: list[tuple[object, dict[str, Any]]] = []

    async def emit_event(self, event: object, **kwargs: Any) -> None:
        self.emitted.append((event, kwargs))


def _make_coordinator() -> tuple[PluginCoordinator, _RecordingPluginCtx, PingAction]:
    log = LogCoordinator(loggers=[])
    coordinator = PluginCoordinator([], log)
    plugin_ctx = _RecordingPluginCtx()
    action = PingAction()
    return coordinator, plugin_ctx, action


@pytest.mark.asyncio
async def test_emit_after_regular_default_opaque_fields() -> None:
    """Without opaque_fields arg the event carries frozenset()."""
    coordinator, plugin_ctx, action = _make_coordinator()
    ctx = Context(user=UserInfo(user_id="u1", roles=()))

    await coordinator.emit_after_regular_aspect(
        plugin_ctx,
        action=action,
        context=ctx,
        params=PingAction.Params(),
        nest_level=1,
        aspect_name="step",
        state_snapshot={},
        aspect_result={"x": 1},
        duration_ms=10.0,
    )

    assert len(plugin_ctx.emitted) == 1
    event, _ = plugin_ctx.emitted[0]
    assert isinstance(event, AfterRegularAspectEvent)
    assert event.opaque_fields == frozenset()


@pytest.mark.asyncio
async def test_emit_after_regular_custom_opaque_fields_propagated() -> None:
    """opaque_fields passed to coordinator is forwarded verbatim to the event."""
    coordinator, plugin_ctx, action = _make_coordinator()
    ctx = Context(user=UserInfo(user_id="u1", roles=()))
    opaque = frozenset({"rich_obj", "db_conn"})

    await coordinator.emit_after_regular_aspect(
        plugin_ctx,
        action=action,
        context=ctx,
        params=PingAction.Params(),
        nest_level=1,
        aspect_name="step",
        state_snapshot={},
        aspect_result={"rich_obj": object(), "order_id": "ORD-1"},
        duration_ms=5.0,
        opaque_fields=opaque,
    )

    assert len(plugin_ctx.emitted) == 1
    event, _ = plugin_ctx.emitted[0]
    assert isinstance(event, AfterRegularAspectEvent)
    assert event.opaque_fields == frozenset({"rich_obj", "db_conn"})


@pytest.mark.asyncio
async def test_after_regular_event_opaque_fields_is_frozenset() -> None:
    """opaque_fields attribute is always a frozenset regardless of value."""
    coordinator, plugin_ctx, action = _make_coordinator()
    ctx = Context(user=UserInfo(user_id="u1", roles=()))

    await coordinator.emit_after_regular_aspect(
        plugin_ctx,
        action=action,
        context=ctx,
        params=PingAction.Params(),
        nest_level=1,
        aspect_name="step",
        state_snapshot={},
        aspect_result={},
        duration_ms=1.0,
        opaque_fields=frozenset({"field_a"}),
    )

    event, _ = plugin_ctx.emitted[0]
    assert isinstance(event.opaque_fields, frozenset)
