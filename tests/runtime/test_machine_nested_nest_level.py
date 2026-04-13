# tests/runtime/test_machine_nested_nest_level.py
"""nest_level propagation for nested runs and plugin events."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from action_machine.intents.plugins.plugin_coordinator import PluginCoordinator
from action_machine.intents.plugins.plugin_run_context import PluginRunContext
from tests.runtime._machine_nested_actions import (
    ChildNestedParams,
    NestLevelParentAction,
    NestLevelTestAction,
    ParentNestedParams,
)
from tests.scenarios.domain_model import PingAction


class TestNestLevel:
    """nest_level increases at each nesting depth."""

    @pytest.mark.asyncio
    async def test_root_action_has_nest_level_one(self, machine, context) -> None:
        action = NestLevelTestAction()
        params = ChildNestedParams()
        result = await machine.run(context, action, params)
        assert result.nest == 1

    @pytest.mark.asyncio
    async def test_child_has_incremented_nest_level(self, machine, context) -> None:
        action = NestLevelParentAction()
        params = ParentNestedParams()
        result = await machine.run(context, action, params)
        assert result.combined == "parent=1,child=2"

    @pytest.mark.asyncio
    async def test_plugin_receives_correct_nest_level(self, machine, context) -> None:
        mock_plugin_ctx = AsyncMock(spec=PluginRunContext)
        mock_coordinator = AsyncMock(spec=PluginCoordinator)
        mock_coordinator.create_run_context = AsyncMock(return_value=mock_plugin_ctx)
        machine._plugin_coordinator = mock_coordinator

        action = PingAction()
        params = PingAction.Params()
        await machine.run(context, action, params)

        first_call = mock_plugin_ctx.emit_event.call_args_list[0]
        event = first_call.args[0]
        assert event.nest_level == 1
