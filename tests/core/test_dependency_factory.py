# tests/core/test_dependency_factory.py
"""
Тесты для DependencyFactory — stateless-фабрики зависимостей действий.

Проверяется:
- Получение зависимостей через resolve() из разных источников.
- Каждый вызов resolve() создаёт новый экземпляр (фабрика stateless).
- Поддержка *args и **kwargs в resolve().
- Запуск дочерних действий через ToolsBox.

DependencyFactory не хранит кеш экземпляров (_instances удалён).
Каждый вызов resolve() создаёт свежий экземпляр через фабрику или
конструктор по умолчанию. Если нужен синглтон, пользователь реализует
это через lambda-замыкание в параметре factory декоратора @depends.
"""

import pytest

from action_machine.context.context import Context
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.tools_box import ToolsBox
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
    """Тесты для метода resolve."""

    def test_resolve_creates_new_instance_each_call(self):
        """Каждый вызов resolve() создаёт новый экземпляр (фабрика stateless)."""
        deps_info = [
            {"class": ServiceA, "description": "", "factory": None},
        ]
        factory = DependencyFactory(deps_info)

        first = factory.resolve(ServiceA)
        second = factory.resolve(ServiceA)

        assert isinstance(first, ServiceA)
        assert isinstance(second, ServiceA)
        assert first is not second  # разные экземпляры, кеша нет

    def test_resolve_creates_via_factory_function(self):
        """Если задана фабрика, она вызывается при каждом resolve()."""

        def custom_factory():
            return ServiceA(value="from_factory")

        deps_info = [
            {"class": ServiceA, "description": "", "factory": custom_factory},
        ]
        factory = DependencyFactory(deps_info)

        instance = factory.resolve(ServiceA)
        assert instance.value == "from_factory"

    def test_resolve_creates_via_default_constructor(self):
        """Без фабрики используется конструктор по умолчанию."""
        deps_info = [
            {"class": ServiceA, "description": "", "factory": None},
        ]
        factory = DependencyFactory(deps_info)

        instance = factory.resolve(ServiceA)
        assert instance.value == "A"

    def test_resolve_raises_for_undeclared_class(self):
        """Если класс не объявлен в @depends, выбрасывается ошибка."""
        deps_info = []  # empty
        factory = DependencyFactory(deps_info)

        with pytest.raises(ValueError, match="not declared in @depends"):
            factory.resolve(ServiceA)

    def test_resolve_with_args_passes_to_constructor(self):
        """Аргументы *args пробрасываются в конструктор."""
        deps_info = [
            {"class": ServiceA, "description": "", "factory": None},
        ]
        factory = DependencyFactory(deps_info)

        instance = factory.resolve(ServiceA, "custom_value")
        assert instance.value == "custom_value"

    def test_resolve_with_kwargs_passes_to_constructor(self):
        """Аргументы **kwargs пробрасываются в конструктор."""
        deps_info = [
            {"class": ServiceA, "description": "", "factory": None},
        ]
        factory = DependencyFactory(deps_info)

        instance = factory.resolve(ServiceA, value="from_kwargs")
        assert instance.value == "from_kwargs"

    def test_resolve_with_args_passes_to_factory(self):
        """Аргументы *args и **kwargs пробрасываются в фабрику."""
        def custom_factory(value="default"):
            return ServiceA(value=f"factory_{value}")

        deps_info = [
            {"class": ServiceA, "description": "", "factory": custom_factory},
        ]
        factory = DependencyFactory(deps_info)

        instance = factory.resolve(ServiceA, value="custom")
        assert instance.value == "factory_custom"

    def test_resolve_lambda_singleton_pattern(self):
        """
        Lambda-синглтон: пользователь создаёт экземпляр вне класса
        и передаёт lambda, возвращающую этот экземпляр.
        Оба вызова resolve() возвращают один и тот же объект.
        """
        shared_instance = ServiceA(value="singleton")

        deps_info = [
            {"class": ServiceA, "description": "", "factory": lambda: shared_instance},
        ]
        factory = DependencyFactory(deps_info)

        first = factory.resolve(ServiceA)
        second = factory.resolve(ServiceA)

        assert first is second  # один и тот же объект
        assert first is shared_instance
        assert first.value == "singleton"


# ======================================================================
# TESTS: ToolsBox functionality (formerly part of DependencyFactory)
# ======================================================================

class TestToolsBoxIntegration:
    """Тесты для ToolsBox, который управляет ресурсами и дочерними действиями."""

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
        """ToolsBox.resolve ищет сначала в resources, затем в factory."""
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
        """Если в resources нет, ToolsBox.resolve обращается к factory."""
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
    async def test_tools_box_resolve_with_kwargs(self, run_child, mock_log):
        """ToolsBox.resolve пробрасывает *args и **kwargs в factory."""
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

        instance = box.resolve(ServiceA, value="custom")
        assert instance.value == "custom"

    @pytest.mark.anyio
    async def test_tools_box_wrap_connections(self, run_child, mock_log):
        """ToolsBox._wrap_connections оборачивает ресурсы в обёртки."""
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
        """ToolsBox.run вызывает run_child с обёрнутыми connections."""
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
