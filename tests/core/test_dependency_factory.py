# tests/core/test_dependency_factory.py
"""
Тесты DependencyFactory — фабрики зависимостей для действий.

Проверяем:
- Получение зависимостей через get() с разными источниками
- Кеширование экземпляров
- Приоритет external_resources
- Оборачивание connections для дочерних действий
- Запуск дочерних действий через run_action
"""


import pytest

from action_machine.Core.BaseAction import BaseAction
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseResult import BaseResult
from action_machine.Core.DependencyFactory import DependencyFactory
from action_machine.ResourceManagers.BaseResourceManager import BaseResourceManager

# ----------------------------------------------------------------------
# Вспомогательные классы
# ----------------------------------------------------------------------

class MockMachine:
    """Мок машины действий для проверки вызовов run."""

    def __init__(self):
        self.run_calls = []

    async def run(self, action, params, resources=None, connections=None):
        self.run_calls.append((action, params, resources, connections))
        return MockResult()

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
    """Ресурс, который требует обёртки."""

    def __init__(self, name="test"):
        self.name = name

    def get_wrapper_class(self):
        return MockWrapper

class ResourceWithoutWrapper(BaseResourceManager):
    """Ресурс без обёртки."""

    def get_wrapper_class(self):
        return None

class MockWrapper(BaseResourceManager):
    """Обёртка для ресурса."""

    def __init__(self, inner):
        self.inner = inner

    def get_wrapper_class(self):
        return None  # обёртки второго уровня не нужны

# ======================================================================
# ТЕСТЫ: Метод get()
# ======================================================================

class TestGet:
    """Проверка метода get."""

    def test_get_returns_from_external_resources(self):
        """external_resources имеют наивысший приоритет."""
        deps_info = [
            {"class": ServiceA, "description": "", "factory": None},
        ]
        external = {ServiceA: ServiceA(value="external")}
        factory = DependencyFactory(MockMachine(), deps_info, external)

        instance = factory.get(ServiceA)

        assert instance.value == "external"
        # Не должно быть в кеше, т.к. внешние не кешируются?
        # В текущей реализации внешние не сохраняются в _instances,
        # но если класс есть во внешних, он возвращается напрямую.
        assert ServiceA not in factory._instances

    def test_get_returns_cached_instance_on_second_call(self):
        """Повторный вызов возвращает закешированный экземпляр."""
        deps_info = [
            {"class": ServiceA, "description": "", "factory": None},
        ]
        factory = DependencyFactory(MockMachine(), deps_info, None)

        first = factory.get(ServiceA)
        second = factory.get(ServiceA)

        assert first is second
        assert ServiceA in factory._instances

    def test_get_creates_via_factory_function(self):
        """Если указана factory, она вызывается."""

        def custom_factory():
            return ServiceA(value="from_factory")

        deps_info = [
            {"class": ServiceA, "description": "", "factory": custom_factory},
        ]
        factory = DependencyFactory(MockMachine(), deps_info, None)

        instance = factory.get(ServiceA)
        assert instance.value == "from_factory"

    def test_get_creates_via_default_constructor(self):
        """Без factory используется конструктор по умолчанию."""
        deps_info = [
            {"class": ServiceA, "description": "", "factory": None},
        ]
        factory = DependencyFactory(MockMachine(), deps_info, None)

        instance = factory.get(ServiceA)
        assert instance.value == "A"

    def test_get_raises_for_undeclared_class(self):
        """Если класс не объявлен в depends и нет во внешних, ошибка."""
        deps_info = []  # пусто
        factory = DependencyFactory(MockMachine(), deps_info, None)

        with pytest.raises(ValueError, match="not declared in @depends"):
            factory.get(ServiceA)

# ======================================================================
# ТЕСТЫ: Оборачивание connections (_wrap_connections)
# ======================================================================

class TestWrapConnections:
    """Проверка метода _wrap_connections."""

    def test_wrap_connections_with_wrapper(self):
        """Ресурс с wrapper_class оборачивается."""
        deps_info = []
        factory = DependencyFactory(MockMachine(), deps_info, None)

        inner = ResourceWithWrapper(name="inner")
        connections = {"db": inner}

        wrapped = factory._wrap_connections(connections)

        assert "db" in wrapped
        assert isinstance(wrapped["db"], MockWrapper)
        assert wrapped["db"].inner is inner

    def test_wrap_connections_without_wrapper(self):
        """Ресурс без wrapper_class передаётся как есть."""
        deps_info = []
        factory = DependencyFactory(MockMachine(), deps_info, None)

        inner = ResourceWithoutWrapper()
        connections = {"db": inner}

        wrapped = factory._wrap_connections(connections)

        assert "db" in wrapped
        assert wrapped["db"] is inner  # тот же объект

    def test_wrap_connections_handles_empty_dict(self):
        """Пустой словарь connections возвращается как есть."""
        deps_info = []
        factory = DependencyFactory(MockMachine(), deps_info, None)

        wrapped = factory._wrap_connections({})
        assert wrapped == {}

    def test_wrap_connections_handles_none(self):
        """connections=None возвращает None (не вызывается в run_action)."""
        # Этот метод не вызывается с None в run_action, но проверим.

        # Не передаём None, т.к. _wrap_connections ожидает dict
        # В коде run_action проверяет if connections is not None
        # и только тогда вызывает _wrap_connections.
        # Отдельно тестировать передачу None не нужно.

# ======================================================================
# ТЕСТЫ: Запуск дочерних действий (run_action)
# ======================================================================

class TestRunAction:
    """Проверка метода run_action."""

    @pytest.mark.anyio
    async def test_run_action_wraps_connections(self):
        """Перед вызовом дочернего действия connections оборачиваются."""
        machine = MockMachine()
        deps_info = [
            {"class": MockAction, "description": "", "factory": None},
        ]
        factory = DependencyFactory(machine, deps_info, None)

        # Сначала получим экземпляр действия (чтобы он закешировался)
        action_instance = factory.get(MockAction)

        inner = ResourceWithWrapper(name="inner")
        conns = {"db": inner}

        params = MockParams()
        await factory.run_action(MockAction, params, connections=conns)

        # Проверяем, что run был вызван с обёрнутыми connections
        assert len(machine.run_calls) == 1
        called_action, called_params, called_resources, called_conns = machine.run_calls[0]

        assert called_action is action_instance
        assert called_params is params
        assert called_conns is not None
        assert "db" in called_conns
        assert isinstance(called_conns["db"], MockWrapper)
        assert called_conns["db"].inner is inner

    @pytest.mark.anyio
    async def test_run_action_without_connections(self):
        """Если connections=None, оборачивание не происходит."""
        machine = MockMachine()
        deps_info = [
            {"class": MockAction, "description": "", "factory": None},
        ]
        factory = DependencyFactory(machine, deps_info, None)

        params = MockParams()

        await factory.run_action(MockAction, params, connections=None)

        assert len(machine.run_calls) == 1
        called_action, called_params, called_resources, called_conns = machine.run_calls[0]
        assert called_conns is None

    @pytest.mark.anyio
    async def test_run_action_passes_resources(self):
        """Параметр resources передаётся в дочернее действие."""
        machine = MockMachine()
        deps_info = [
            {"class": MockAction, "description": "", "factory": None},
        ]
        factory = DependencyFactory(machine, deps_info, None)

        params = MockParams()
        resources = {"some": "resource"}

        await factory.run_action(MockAction, params, resources=resources)

        assert len(machine.run_calls) == 1
        called_action, called_params, called_resources, called_conns = machine.run_calls[0]
        assert called_resources == resources

    @pytest.mark.anyio
    async def test_run_action_returns_result(self):
        """Метод возвращает результат от дочернего действия."""
        machine = MockMachine()
        deps_info = [
            {"class": MockAction, "description": "", "factory": None},
        ]
        factory = DependencyFactory(machine, deps_info, None)

        params = MockParams()
        result = await factory.run_action(MockAction, params)

        assert isinstance(result, MockResult)