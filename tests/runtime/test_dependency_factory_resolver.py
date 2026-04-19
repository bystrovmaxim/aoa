# tests/runtime/test_dependency_factory_resolver.py
"""Tests for ``DependencyFactoryResolver`` wiring and ``ToolsBoxFactory.create``."""

from unittest.mock import AsyncMock, MagicMock

from action_machine.dependencies.dependency_factory import DependencyFactory
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.runtime.components.tools_box_factory import ToolsBoxFactory
from action_machine.runtime.machines.action_product_machine import ActionProductMachine
from tests.scenarios.domain_model import PingAction


def test_machine_dependency_factory_for_returns_factory(coordinator) -> None:
    """ActionProductMachine.dependency_factory_for matches _dependency_factory_for."""
    machine = ActionProductMachine(mode="test", coordinator=coordinator)
    pub = machine.dependency_factory_for(PingAction)
    internal = machine._dependency_factory_for(PingAction)
    assert isinstance(pub, DependencyFactory)
    assert pub._deps == internal._deps


def test_tools_box_factory_create_uses_resolver() -> None:
    """ToolsBoxFactory.create pulls DependencyFactory via resolver only."""
    log = LogCoordinator(loggers=[])
    factory = ToolsBoxFactory(log)
    mock_dep = DependencyFactory(())
    resolver = MagicMock()
    resolver.dependency_factory_for.return_value = mock_dep
    run_child = AsyncMock()

    box = factory.create(
        factory_resolver=resolver,
        nest_level=1,
        context=MagicMock(),
        action_cls=PingAction,
        params=MagicMock(),
        resources=None,
        rollup=False,
        run_child=run_child,
        mode="test",
        machine_class_name="ActionProductMachine",
    )

    resolver.dependency_factory_for.assert_called_once_with(PingAction)
    assert box.factory is mock_dep
    assert box.nested_level == 1
