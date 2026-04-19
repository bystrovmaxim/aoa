# tests/runtime/test_machine_plugins_events_data.py
"""Kwargs and payloads passed through ``PluginRunContext.emit_event``."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from action_machine.context.context import Context
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.plugin.events import (
    AfterRegularAspectEvent,
    BeforeRegularAspectEvent,
    GlobalFinishEvent,
)
from action_machine.runtime.action_product_machine import ActionProductMachine
from tests.runtime._machine_plugins_helpers import extract_event, extract_event_types
from tests.scenarios.domain_model import PingAction, SimpleAction


class TestEventData:
    """Data passed into each ``emit_event`` call."""

    @pytest.mark.asyncio
    async def test_log_coordinator_passed(
        self,
        machine_with_mock_plugins: ActionProductMachine,
        mock_plugin_ctx: AsyncMock,
        context: Context,
        log_coordinator: LogCoordinator,
    ) -> None:
        action = PingAction()
        params = PingAction.Params()
        await machine_with_mock_plugins.run(context, action, params)
        for call in mock_plugin_ctx.emit_event.call_args_list:
            assert "log_coordinator" in call.kwargs
            assert call.kwargs["log_coordinator"] is log_coordinator

    @pytest.mark.asyncio
    async def test_machine_name_and_mode_passed(
        self,
        machine_with_mock_plugins: ActionProductMachine,
        mock_plugin_ctx: AsyncMock,
        context: Context,
    ) -> None:
        action = PingAction()
        params = PingAction.Params()
        await machine_with_mock_plugins.run(context, action, params)
        for call in mock_plugin_ctx.emit_event.call_args_list:
            assert call.kwargs["machine_name"] == "ActionProductMachine"
            assert call.kwargs["mode"] == "test"

    @pytest.mark.asyncio
    async def test_coordinator_not_passed(
        self,
        machine_with_mock_plugins: ActionProductMachine,
        mock_plugin_ctx: AsyncMock,
        context: Context,
    ) -> None:
        action = PingAction()
        params = PingAction.Params()
        await machine_with_mock_plugins.run(context, action, params)
        for call in mock_plugin_ctx.emit_event.call_args_list:
            assert "coordinator" not in call.kwargs

    @pytest.mark.asyncio
    async def test_event_contains_action_class_and_name(
        self,
        machine_with_mock_plugins: ActionProductMachine,
        mock_plugin_ctx: AsyncMock,
        context: Context,
    ) -> None:
        action = SimpleAction()
        params = SimpleAction.Params(name="Charlie")
        await machine_with_mock_plugins.run(context, action, params)
        event = extract_event(mock_plugin_ctx, 0)
        assert event.action_class is SimpleAction
        assert "SimpleAction" in event.action_name
        assert event.params is params

    @pytest.mark.asyncio
    async def test_nest_level_in_event(
        self,
        machine_with_mock_plugins: ActionProductMachine,
        mock_plugin_ctx: AsyncMock,
        context: Context,
    ) -> None:
        action = PingAction()
        params = PingAction.Params()
        await machine_with_mock_plugins.run(context, action, params)
        event = extract_event(mock_plugin_ctx, 0)
        assert event.nest_level == 1

    @pytest.mark.asyncio
    async def test_global_finish_contains_result_and_duration(
        self,
        machine_with_mock_plugins: ActionProductMachine,
        mock_plugin_ctx: AsyncMock,
        context: Context,
    ) -> None:
        action = PingAction()
        params = PingAction.Params()
        await machine_with_mock_plugins.run(context, action, params)
        event = extract_event(mock_plugin_ctx, -1)
        assert isinstance(event, GlobalFinishEvent)
        assert event.result is not None
        assert event.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_regular_aspect_event_contains_aspect_name(
        self,
        machine_with_mock_plugins: ActionProductMachine,
        mock_plugin_ctx: AsyncMock,
        context: Context,
    ) -> None:
        action = SimpleAction()
        params = SimpleAction.Params(name="Test")
        await machine_with_mock_plugins.run(context, action, params)
        event_types = extract_event_types(mock_plugin_ctx)
        before_idx = event_types.index("BeforeRegularAspectEvent")
        before_event = extract_event(mock_plugin_ctx, before_idx)
        assert isinstance(before_event, BeforeRegularAspectEvent)
        assert isinstance(before_event.aspect_name, str)
        assert len(before_event.aspect_name) > 0

    @pytest.mark.asyncio
    async def test_after_regular_aspect_contains_result_and_duration(
        self,
        machine_with_mock_plugins: ActionProductMachine,
        mock_plugin_ctx: AsyncMock,
        context: Context,
    ) -> None:
        action = SimpleAction()
        params = SimpleAction.Params(name="Test")
        await machine_with_mock_plugins.run(context, action, params)
        event_types = extract_event_types(mock_plugin_ctx)
        after_idx = event_types.index("AfterRegularAspectEvent")
        after_event = extract_event(mock_plugin_ctx, after_idx)
        assert isinstance(after_event, AfterRegularAspectEvent)
        assert isinstance(after_event.aspect_result, dict)
        assert after_event.duration_ms >= 0
