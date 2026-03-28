# tests/core/test_dependency_factory.py
"""
Тесты для DependencyFactory — stateless-фабрики зависимостей действий.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

DependencyFactory принимает tuple[DependencyInfo, ...] из
ClassMetadata.dependencies и предоставляет resolve() для создания
экземпляров зависимостей.

═══════════════════════════════════════════════════════════════════════════════
КЛЮЧЕВЫЕ СВОЙСТВА
═══════════════════════════════════════════════════════════════════════════════

- Каждый вызов resolve() создаёт новый экземпляр (кеш отсутствует).
- Синглтоны реализуются через lambda-замыкание в @depends(factory=...).
- Поддержка *args и **kwargs в resolve() для параметризованных фабрик.
- Обратная совместимость с list[dict] форматом для старых тестов.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

1. resolve() создаёт новый экземпляр при каждом вызове.
2. resolve() использует factory-функцию если задана.
3. resolve() использует конструктор по умолчанию если factory=None.
4. resolve() выбрасывает ValueError для необъявленного класса.
5. resolve() пробрасывает *args и **kwargs в конструктор.
6. resolve() пробрасывает *args и **kwargs в factory.
7. Lambda-синглтон: factory=lambda: shared_instance.
8. ToolsBox.resolve ищет сначала в resources, затем в factory.
9. ToolsBox._wrap_connections оборачивает ресурсы в обёртки.
10. ToolsBox.run вызывает run_child с обёрнутыми connections.
"""

import pytest

from action_machine.context.context import Context
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.tools_box import ToolsBox
from action_machine.dependencies.dependency_factory import DependencyFactory, DependencyInfo
from action_machine.resource_managers.base_resource_manager import BaseResourceManager

# ----------------------------------------------------------------------
# Вспомогательные классы
# ----------------------------------------------------------------------

class MockParams(BaseParams):
    """Пустые параметры для тестов."""
    pass


class MockResult(BaseResult):
    """Пустой результат для тестов."""
    pass


class MockAction(BaseAction[MockParams, MockResult]):
    """Тестовое действие."""
    pass


class ServiceA:
    """Тестовый сервис с опциональным параметром."""
    def __init__(self, value=None):
        self.value = value or "A"


class ServiceB:
    """Второй тестовый сервис."""
    def __init__(self, value=None):
        self.value = value or "B"


class ResourceWithWrapper(BaseResourceManager):
    """Ресурс, требующий обёртку при передаче в дочерние действия."""
    def __init__(self, name="test"):
        self.name = name

    def get_wrapper_class(self):
        return MockWrapper


class ResourceWithoutWrapper(BaseResourceManager):
    """Ресурс без обёртки — передаётся как есть."""
    def get_wrapper_class(self):
        return None


class MockWrapper(BaseResourceManager):
    """Обёртка ресурса — запрещает управление транзакциями."""
    def __init__(self, inner):
        self.inner = inner

    def get_wrapper_class(self):
        return None


# ======================================================================
# ТЕСТЫ: resolve() — создание экземпляров
# ======================================================================

class TestResolve:
    """Тесты для метода resolve."""

    def test_resolve_creates_new_instance_each_call(self):
        """Каждый вызов resolve() создаёт новый экземпляр (кеш отсутствует)."""
        factory = DependencyFactory((
            DependencyInfo(cls=ServiceA, description="A"),
        ))

        first = factory.resolve(ServiceA)
        second = factory.resolve(ServiceA)

        assert isinstance(first, ServiceA)
        assert isinstance(second, ServiceA)
        assert first is not second

    def test_resolve_creates_via_factory_function(self):
        """Если задана factory-функция, она вызывается при каждом resolve()."""
        factory = DependencyFactory((
            DependencyInfo(cls=ServiceA, factory=lambda: ServiceA(value="from_factory")),
        ))

        instance = factory.resolve(ServiceA)
        assert instance.value == "from_factory"

    def test_resolve_creates_via_default_constructor(self):
        """Без factory используется конструктор по умолчанию."""
        factory = DependencyFactory((
            DependencyInfo(cls=ServiceA),
        ))

        instance = factory.resolve(ServiceA)
        assert instance.value == "A"

    def test_resolve_raises_for_undeclared_class(self):
        """Если класс не объявлен в @depends — ValueError."""
        factory = DependencyFactory(())

        with pytest.raises(ValueError, match="not declared in @depends"):
            factory.resolve(ServiceA)

    def test_resolve_with_args_passes_to_constructor(self):
        """Позиционные аргументы пробрасываются в конструктор."""
        factory = DependencyFactory((
            DependencyInfo(cls=ServiceA),
        ))

        instance = factory.resolve(ServiceA, "custom_value")
        assert instance.value == "custom_value"

    def test_resolve_with_kwargs_passes_to_constructor(self):
        """Именованные аргументы пробрасываются в конструктор."""
        factory = DependencyFactory((
            DependencyInfo(cls=ServiceA),
        ))

        instance = factory.resolve(ServiceA, value="from_kwargs")
        assert instance.value == "from_kwargs"

    def test_resolve_with_args_passes_to_factory(self):
        """Аргументы пробрасываются в factory-функцию."""
        factory = DependencyFactory((
            DependencyInfo(
                cls=ServiceA,
                factory=lambda value="default": ServiceA(value=f"factory_{value}"),
            ),
        ))

        instance = factory.resolve(ServiceA, value="custom")
        assert instance.value == "factory_custom"

    def test_resolve_lambda_singleton_pattern(self):
        """
        Lambda-синглтон: factory возвращает один и тот же экземпляр.
        Оба вызова resolve() возвращают один объект.
        """
        shared_instance = ServiceA(value="singleton")

        factory = DependencyFactory((
            DependencyInfo(cls=ServiceA, factory=lambda: shared_instance),
        ))

        first = factory.resolve(ServiceA)
        second = factory.resolve(ServiceA)

        assert first is second
        assert first is shared_instance
        assert first.value == "singleton"


# ======================================================================
# ТЕСТЫ: обратная совместимость с list[dict]
# ======================================================================

class TestResolveBackwardCompat:
    """Тесты обратной совместимости с форматом list[dict]."""

    def test_resolve_from_dict_format(self):
        """DependencyFactory принимает list[dict] для старых тестов."""
        factory = DependencyFactory([
            {"class": ServiceA, "factory": None, "description": "A"},
        ])

        instance = factory.resolve(ServiceA)
        assert isinstance(instance, ServiceA)
        assert instance.value == "A"

    def test_resolve_from_dict_with_factory(self):
        """list[dict] с factory-функцией."""
        factory = DependencyFactory([
            {"class": ServiceA, "factory": lambda: ServiceA(value="dict_factory"), "description": ""},
        ])

        instance = factory.resolve(ServiceA)
        assert instance.value == "dict_factory"


# ======================================================================
# ТЕСТЫ: вспомогательные методы
# ======================================================================

class TestFactoryHelpers:
    """Тесты вспомогательных методов фабрики."""

    def test_get_all_classes(self):
        """get_all_classes() возвращает список зарегистрированных классов."""
        factory = DependencyFactory((
            DependencyInfo(cls=ServiceA),
            DependencyInfo(cls=ServiceB),
        ))

        classes = factory.get_all_classes()
        assert ServiceA in classes
        assert ServiceB in classes
        assert len(classes) == 2

    def test_has_returns_true_for_registered(self):
        """has() возвращает True для зарегистрированного класса."""
        factory = DependencyFactory((DependencyInfo(cls=ServiceA),))
        assert factory.has(ServiceA) is True

    def test_has_returns_false_for_unregistered(self):
        """has() возвращает False для незарегистрированного класса."""
        factory = DependencyFactory(())
        assert factory.has(ServiceA) is False


# ======================================================================
# ТЕСТЫ: ToolsBox интеграция с DependencyFactory
# ======================================================================

class TestToolsBoxIntegration:
    """Тесты ToolsBox, который использует DependencyFactory для резолва."""

    @pytest.fixture
    def mock_log(self):
        """Мок логгера."""
        class MockLog:
            async def info(self, msg, **kwargs): pass
            async def warning(self, msg, **kwargs): pass
            async def error(self, msg, **kwargs): pass
            async def debug(self, msg, **kwargs): pass
        return MockLog()

    @pytest.fixture
    def mock_machine(self):
        """Мок машины с методом _run_internal."""
        class MockMachineWithRun:
            def __init__(self):
                self.called = False
                self.last_action = None
                self.last_params = None
                self.last_connections = None
                self.last_nested_level = None

            async def _run_internal(self, context, action, params, resources, connections, nested_level):
                self.called = True
                self.last_action = action
                self.last_params = params
                self.last_connections = connections
                self.last_nested_level = nested_level
                return MockResult()
        return MockMachineWithRun()

    @pytest.fixture
    def run_child(self, mock_machine):
        """Замыкание run_child, вызывающее mock_machine._run_internal."""
        async def _run_child(action, params, connections):
            return await mock_machine._run_internal(
                context=None, action=action, params=params,
                resources=None, connections=connections, nested_level=0,
            )
        return _run_child

    @pytest.mark.anyio
    async def test_resolve_uses_resources_first(self, run_child, mock_log):
        """ToolsBox.resolve ищет сначала в resources, затем в factory."""
        factory = DependencyFactory((DependencyInfo(cls=ServiceA),))
        resources = {ServiceA: ServiceA(value="from_resources")}

        box = ToolsBox(
            run_child=run_child, factory=factory, resources=resources,
            context=Context(), log=mock_log, nested_level=0,
        )

        instance = box.resolve(ServiceA)
        assert instance.value == "from_resources"

    @pytest.mark.anyio
    async def test_resolve_falls_back_to_factory(self, run_child, mock_log):
        """Если в resources нет — обращается к factory."""
        factory = DependencyFactory((DependencyInfo(cls=ServiceA),))

        box = ToolsBox(
            run_child=run_child, factory=factory, resources=None,
            context=Context(), log=mock_log, nested_level=0,
        )

        instance = box.resolve(ServiceA)
        assert instance.value == "A"

    @pytest.mark.anyio
    async def test_resolve_with_kwargs(self, run_child, mock_log):
        """ToolsBox.resolve пробрасывает kwargs в factory."""
        factory = DependencyFactory((DependencyInfo(cls=ServiceA),))

        box = ToolsBox(
            run_child=run_child, factory=factory, resources=None,
            context=Context(), log=mock_log, nested_level=0,
        )

        instance = box.resolve(ServiceA, value="custom")
        assert instance.value == "custom"

    @pytest.mark.anyio
    async def test_wrap_connections(self, run_child, mock_log):
        """ToolsBox._wrap_connections оборачивает ресурсы в обёртки."""
        factory = DependencyFactory(())

        box = ToolsBox(
            run_child=run_child, factory=factory, resources=None,
            context=Context(), log=mock_log, nested_level=0,
        )

        inner = ResourceWithWrapper(name="inner")
        connections = {"db": inner}

        wrapped = box._wrap_connections(connections)

        assert "db" in wrapped
        assert isinstance(wrapped["db"], MockWrapper)
        assert wrapped["db"].inner is inner

    @pytest.mark.anyio
    async def test_run_calls_run_child(self, mock_machine, run_child, mock_log):
        """ToolsBox.run вызывает run_child с обёрнутыми connections."""
        factory = DependencyFactory((DependencyInfo(cls=MockAction),))

        box = ToolsBox(
            run_child=run_child, factory=factory, resources={"test": "resource"},
            context=Context(), log=mock_log, nested_level=2,
        )

        params = MockParams()
        connections = {"db": ResourceWithWrapper(name="inner")}

        result = await box.run(MockAction, params, connections=connections)

        assert mock_machine.called is True
        assert isinstance(mock_machine.last_action, MockAction)
        assert mock_machine.last_params is params
        assert "db" in mock_machine.last_connections
        assert isinstance(mock_machine.last_connections["db"], MockWrapper)
        assert isinstance(result, MockResult)
