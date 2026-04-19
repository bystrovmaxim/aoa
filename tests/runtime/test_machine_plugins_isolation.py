# tests/runtime/test_machine_plugins_isolation.py
"""Plugin run context isolation across separate ``run()`` calls."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from action_machine.context.context import Context
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.plugin.plugin_coordinator import PluginCoordinator
from action_machine.plugin.plugin_run_context import PluginRunContext
from action_machine.runtime.machines.action_product_machine import ActionProductMachine
from tests.scenarios.domain_model import PingAction


class TestPluginIsolation:
    """Each ``run()`` gets a fresh ``PluginRunContext``."""

    @pytest.mark.asyncio
    async def test_separate_contexts_per_run(
        self, log_coordinator: LogCoordinator, context: Context,
    ) -> None:
        ctx1 = AsyncMock(spec=PluginRunContext)
        ctx2 = AsyncMock(spec=PluginRunContext)
        mock_coordinator = AsyncMock(spec=PluginCoordinator)
        mock_coordinator.create_run_context = AsyncMock(side_effect=[ctx1, ctx2])

        machine = ActionProductMachine(
            mode="test",
            log_coordinator=log_coordinator,
        )
        machine._plugin_coordinator = mock_coordinator

        action = PingAction()
        params = PingAction.Params()

        await machine.run(context, action, params)
        await machine.run(context, PingAction(), PingAction.Params())

        assert mock_coordinator.create_run_context.await_count == 2
        assert ctx1.emit_event.await_count == 4
        assert ctx2.emit_event.await_count == 4
