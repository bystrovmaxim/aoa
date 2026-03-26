# tests/core/test_dependency_factory.py
"""
Tests for DependencyFactory — the dependency factory for actions.

Checks:
- Getting dependencies via resolve() from different sources
- Instance caching
- Launching child actions via ToolsBox (moved from DependencyFactory)

Изменения (этап 0–1):
- Все вызовы factory.get(...) заменены на factory.resolve(...).
- Убран параметр machine из конструктора DependencyFactory.
- Убран параметр external_resources из конструктора DependencyFactory.
- Убраны тесты, связанные с external_resources и run_action (эти функции перемещены в ToolsBox).
- Тесты на запуск дочерних действий переписаны с использованием ToolsBox.
- Обновлены комментарии.

Изменения (этап 2):
- В тестах ToolsBox теперь создаётся с аргументом run_child вместо machine.
- Добавлена фикстура run_child для упрощения создания ToolsBox.
"""

import pytest

from action_machine.context.context import Context
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.tools_box import ToolsBox

# Импорт DependencyFactory исправлен: из action_machine.dependencies.dependency_factory
from action_machine.dependencies.dependency_factory import DependencyFactory
from action_machine.resource_managers.base_resource_manager import BaseResourceManager

# ----------------------------------------------------------------------
# Helper classes
# ----------------------------------------------------------------------

class MockMachine:
    """Mock action machine for verifying run calls."""
    pass


class MockParams(BaseParams):
    pass


class MockResult(BaseResult):
    pass


class MockAction(BaseAction[MockParams, MockResult]):
    pass


class ServiceA:
    def __init__(self, value=None):
        self.value = value or "A"


class ServiceB:
    def __init__(self, value=None):
        self.value = value or "B"


class ResourceWithWrapper(BaseResourceManager):
    """Resource that requires a wrapper."""

    def __init__(self, name="test"):
        self.name = name

    def get_wrapper_class(self):
        return MockWrapper


class ResourceWithoutWrapper(BaseResourceManager):
    """Resource without a wrapper."""

    def get_wrapper_class(self):
        return None


class MockWrapper(BaseResourceManager):
    """Wrapper for a resource."""

    def __init__(self, inner):
        self.inner = inner

    def get_wrapper_class(self):
        return None  # no second‑level wrappers needed


# ======================================================================
# TESTS: resolve() method
# ======================================================================

class TestResolve:
    """Tests for the resolve method."""

    def test_resolve_returns_cached_instance_on_second_call(self):
        """Second call returns the cached instance."""
        deps_info = [
            {"class": ServiceA, "description": "", "factory": None},
        ]
        factory = DependencyFactory(deps_info)

        first = factory.resolve(ServiceA)
        second = factory.resolve(ServiceA)

        assert first is second
        assert ServiceA in factory._instances

    def test_resolve_creates_via_factory_function(self):
        """If a factory is provided, it is called."""

        def custom_factory():
            return ServiceA(value="from_factory")

        deps_info = [
            {"class": ServiceA, "description": "", "factory": custom_factory},
        ]
        factory = DependencyFactory(deps_info)

        instance = factory.resolve(ServiceA)
        assert instance.value == "from_factory"

    def test_resolve_creates_via_default_constructor(self):
        """Without a factory, the default constructor is used."""
        deps_info = [
            {"class": ServiceA, "description": "", "factory": None},
        ]
        factory = DependencyFactory(deps_info)

        instance = factory.resolve(ServiceA)
        assert instance.value == "A"

    def test_resolve_raises_for_undeclared_class(self):
        """If the class is not declared in @depends, an error is raised."""
        deps_info = []  # empty
        factory = DependencyFactory(deps_info)

        with pytest.raises(ValueError, match="not declared in @depends"):
            factory.resolve(ServiceA)


# ======================================================================
# TESTS: ToolsBox functionality (formerly part of DependencyFactory)
# ======================================================================

class TestToolsBoxIntegration:
    """Tests for ToolsBox which now handles resources and child actions."""

    @pytest.fixture
    def mock_machine(self):
        """Mock machine with a _run_internal method."""
        class MockMachineWithRun:
            async def _run_internal(self, context, action, params, resources, connections, nested_level):
                self.called = True
                self.last_context = context
                self.last_action = action
                self.last_params = params
                self.last_resources = resources
                self.last_connections = connections
                self.last_nested_level = nested_level
                return MockResult()
        return MockMachineWithRun()

    @pytest.fixture
    def mock_log(self):
        """Mock logger."""
        class MockLog:
            async def info(self, msg, **kwargs):
                pass
            async def warning(self, msg, **kwargs):
                pass
            async def error(self, msg, **kwargs):
                pass
            async def debug(self, msg, **kwargs):
                pass
        return MockLog()

    @pytest.fixture
    def run_child(self, mock_machine):
        """Create a run_child closure that calls mock_machine._run_internal."""
        async def run_child(action, params, connections):
            return await mock_machine._run_internal(
                context=None,
                action=action,
                params=params,
                resources=None,
                connections=connections,
                nested_level=0,
            )
        return run_child

    @pytest.mark.anyio
    async def test_tools_box_resolve_uses_resources_first(self, run_child, mock_log):
        """ToolsBox.resolve should check resources before factory."""
        deps_info = [
            {"class": ServiceA, "description": "", "factory": None},
        ]
        factory = DependencyFactory(deps_info)
        resources = {ServiceA: ServiceA(value="from_resources")}
        box = ToolsBox(
            run_child=run_child,
            factory=factory,
            resources=resources,
            context=Context(),
            log=mock_log,
            nested_level=0,
        )

        instance = box.resolve(ServiceA)
        assert instance.value == "from_resources"

    @pytest.mark.anyio
    async def test_tools_box_resolve_falls_back_to_factory(self, run_child, mock_log):
        """If not in resources, ToolsBox.resolve should use factory."""
        deps_info = [
            {"class": ServiceA, "description": "", "factory": None},
        ]
        factory = DependencyFactory(deps_info)
        box = ToolsBox(
            run_child=run_child,
            factory=factory,
            resources=None,
            context=Context(),
            log=mock_log,
            nested_level=0,
        )

        instance = box.resolve(ServiceA)
        assert instance.value == "A"

    @pytest.mark.anyio
    async def test_tools_box_wrap_connections(self, run_child, mock_log):
        """ToolsBox._wrap_connections should wrap resources with wrappers."""
        factory = DependencyFactory([])
        box = ToolsBox(
            run_child=run_child,
            factory=factory,
            resources=None,
            context=Context(),
            log=mock_log,
            nested_level=0,
        )

        inner = ResourceWithWrapper(name="inner")
        connections = {"db": inner}

        wrapped = box._wrap_connections(connections)

        assert "db" in wrapped
        assert isinstance(wrapped["db"], MockWrapper)
        assert wrapped["db"].inner is inner

    @pytest.mark.anyio
    async def test_tools_box_run(self, mock_machine, run_child, mock_log):
        """ToolsBox.run should call the run_child function with wrapped connections."""
        deps_info = [
            {"class": MockAction, "description": "", "factory": None},
        ]
        factory = DependencyFactory(deps_info)
        resources = {"test": "resource"}
        context = Context()
        box = ToolsBox(
            run_child=run_child,
            factory=factory,
            resources=resources,
            context=context,
            log=mock_log,
            nested_level=2,
        )

        params = MockParams()
        connections = {"db": ResourceWithWrapper(name="inner")}

        result = await box.run(MockAction, params, connections=connections)

        # Verify that run_child was called with the correct parameters
        assert mock_machine.called is True
        assert mock_machine.last_context is None  # run_child doesn't pass context
        assert isinstance(mock_machine.last_action, MockAction)
        assert mock_machine.last_params is params
        # Connections should be wrapped
        assert mock_machine.last_connections is not None
        assert "db" in mock_machine.last_connections
        assert isinstance(mock_machine.last_connections["db"], MockWrapper)
        assert mock_machine.last_nested_level == 0  # run_child uses default nested_level=0
        assert isinstance(result, MockResult)