# tests/action_machine/runtime/conftest.py
"""Runtime test fixtures shared across sibling modules under ``tests/action_machine/runtime/``."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from aoa.action_machine.context.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.plugin.plugin_coordinator import PluginCoordinator
from aoa.action_machine.plugin.plugin_run_context import PluginRunContext
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from tests.action_machine.scenarios.domain_model.roles import AdminRole, ManagerRole


@pytest.fixture()
def machine(log_coordinator: LogCoordinator) -> ActionProductMachine:
    """ActionProductMachine with quiet logging (nested run and similar tests)."""
    return ActionProductMachine(
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
        log_coordinator=log_coordinator,
    )
    machine._plugin_coordinator = mock_coordinator
    return machine


@pytest.fixture()
def context() -> Context:
    """Context with roles that pass runtime role checks."""
    return Context(user=UserInfo(user_id="tester", roles=(ManagerRole, AdminRole)))
