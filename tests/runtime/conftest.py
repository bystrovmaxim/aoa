# tests/runtime/conftest.py
"""Runtime test fixtures shared across sibling modules under ``tests/runtime/``."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from action_machine.intents.context.context import Context
from action_machine.intents.context.user_info import UserInfo
from action_machine.intents.logging.log_coordinator import LogCoordinator
from action_machine.intents.plugins.plugin_coordinator import PluginCoordinator
from action_machine.intents.plugins.plugin_run_context import PluginRunContext
from action_machine.runtime.machines.action_product_machine import ActionProductMachine
from tests.scenarios.domain_model.roles import AdminRole, ManagerRole


@pytest.fixture()
def machine(log_coordinator: LogCoordinator) -> ActionProductMachine:
    """ActionProductMachine with quiet logging (nested run and similar tests)."""
    return ActionProductMachine(
        mode="test",
        log_coordinator=log_coordinator,
    )


@pytest.fixture()
def log_coordinator() -> LogCoordinator:
    """Quiet LogCoordinator (no stdout loggers)."""
    return LogCoordinator(loggers=[])


@pytest.fixture()
def mock_plugin_ctx() -> AsyncMock:
    """Mock PluginRunContext recording ``emit_event`` calls."""
    return AsyncMock(spec=PluginRunContext)


@pytest.fixture()
def machine_with_mock_plugins(log_coordinator: LogCoordinator, mock_plugin_ctx: AsyncMock) -> ActionProductMachine:
    """ActionProductMachine with PluginCoordinator returning ``mock_plugin_ctx``."""
    mock_coordinator = AsyncMock(spec=PluginCoordinator)
    mock_coordinator.create_run_context = AsyncMock(return_value=mock_plugin_ctx)

    machine = ActionProductMachine(
        mode="test",
        log_coordinator=log_coordinator,
    )
    machine._plugin_coordinator = mock_coordinator
    return machine


@pytest.fixture()
def context() -> Context:
    """Context with roles that pass runtime role checks."""
    return Context(user=UserInfo(user_id="tester", roles=(ManagerRole, AdminRole)))
