# tests/core/test_aspect_method.py
"""
Тесты декораторов аспектов: @aspect, @summary_aspect, @depends, @connection.
Проверяем:
- Установку атрибутов _is_aspect, _aspect_description, _aspect_type
- Ошибку TypeError для не-async функций
- Добавление зависимостей через @depends
- Добавление соединений через @connection
- Копирование списков при наследовании (не мутировать родительские)
"""

import pytest

from action_machine.Core.AspectMethod import aspect, connection, depends, summary_aspect
from action_machine.Core.BaseAction import BaseAction
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseResult import BaseResult
from action_machine.ResourceManagers.BaseResourceManager import BaseResourceManager


# ----------------------------------------------------------------------
# Вспомогательные классы
# ----------------------------------------------------------------------
class MockParams(BaseParams):
    pass

class MockResult(BaseResult):
    pass

class MockAction(BaseAction[MockParams, MockResult]):
    pass

class MockResourceManager(BaseResourceManager):
    def get_wrapper_class(self):
        return None

# ======================================================================
# ТЕСТЫ: @aspect
# ======================================================================
class TestAspectDecorator:
    """Проверка декоратора @aspect."""

    def test_aspect_sets_correct_attributes(self):
        """@aspect должен установить _is_aspect, _aspect_description, _aspect_type='regular'."""
        class TestAction(MockAction):
            @aspect("Описание аспекта")
            async def my_aspect(self, params, state, deps, connections):
                return {}

        assert hasattr(TestAction.my_aspect, "_is_aspect")
        assert TestAction.my_aspect._is_aspect is True
        assert TestAction.my_aspect._aspect_description == "Описание аспекта"
        assert TestAction.my_aspect._aspect_type == "regular"

    def test_aspect_on_sync_function_raises_type_error(self):
        """@aspect должен кидать TypeError, если функция не async."""
        with pytest.raises(TypeError, match="должен быть async def"):
            class TestAction(MockAction):
                @aspect("Синхронный")
                def my_aspect(self, params, state, deps, connections):
                    return {}

    def test_aspect_preserves_method_metadata(self):
        """@aspect не должен затирать имя и другие атрибуты метода."""
        class TestAction(MockAction):
            @aspect("Тест")
            async def my_aspect(self, params, state, deps, connections):
                """docstring"""
                return {}

        assert TestAction.my_aspect.__name__ == "my_aspect"
        assert TestAction.my_aspect.__doc__ == "docstring"


# ======================================================================
# ТЕСТЫ: @summary_aspect
# ======================================================================
class TestSummaryAspectDecorator:
    """Проверка декоратора @summary_aspect."""

    def test_summary_aspect_sets_correct_attributes(self):
        """@summary_aspect должен установить _aspect_type='summary'."""
        class TestAction(MockAction):
            @summary_aspect("Главный аспект")
            async def my_summary(self, params, state, deps, connections):
                return MockResult()

        assert hasattr(TestAction.my_summary, "_is_aspect")
        assert TestAction.my_summary._is_aspect is True
        assert TestAction.my_summary._aspect_description == "Главный аспект"
        assert TestAction.my_summary._aspect_type == "summary"

    def test_summary_aspect_on_sync_function_raises_type_error(self):
        """@summary_aspect должен кидать TypeError, если функция не async."""
        with pytest.raises(TypeError, match="должен быть async def"):
            class TestAction(MockAction):
                @summary_aspect("Синхронный")
                def my_summary(self, params, state, deps, connections):
                    return MockResult()


# ======================================================================
# ТЕСТЫ: @depends
# ======================================================================
class TestDependsDecorator:
    """Проверка декоратора @depends."""

    def test_depends_adds_dependency(self):
        """@depends добавляет запись в _dependencies класса."""
        @depends(str, description="Строковый сервис")
        class TestAction(MockAction):
            @summary_aspect("test")
            async def summary(self, params, state, deps, connections):
                return MockResult()

        assert hasattr(TestAction, "_dependencies")
        assert len(TestAction._dependencies) == 1
        dep = TestAction._dependencies[0]
        assert dep["class"] is str
        assert dep["description"] == "Строковый сервис"
        assert dep["factory"] is None

    def test_depends_with_factory(self):
        """@depends может принимать фабрику."""
        def factory():
            return "created"

        @depends(int, description="Число", factory=factory)
        class TestAction(MockAction):
            @summary_aspect("test")
            async def summary(self, params, state, deps, connections):
                return MockResult()

        dep = TestAction._dependencies[0]
        assert dep["class"] is int
        assert dep["factory"] is factory

    def test_depends_multiple_decorators(self):
        """Несколько @depends добавляются в список."""
        # Декораторы применяются снизу вверх:
        # сначала @depends(float), затем @depends(int), затем @depends(str)
        # Каждый последующий prepend'ит или append'ит — проверяем set, не порядок
        @depends(str)
        @depends(int)
        @depends(float)
        class TestAction(MockAction):
            @summary_aspect("test")
            async def summary(self, params, state, deps, connections):
                return MockResult()

        assert len(TestAction._dependencies) == 3
        classes = {d["class"] for d in TestAction._dependencies}
        assert classes == {str, int, float}

    def test_depends_does_not_mutate_parent_class(self):
        """Список зависимостей копируется, родительский класс не изменяется."""
        class Parent(MockAction):
            pass

        @depends(str)
        class Child(Parent):
            @summary_aspect("test")
            async def summary(self, params, state, deps, connections):
                return MockResult()

        # Parent не должен получить _dependencies от декоратора Child
        assert "_dependencies" not in Parent.__dict__
        assert hasattr(Child, "_dependencies")
        assert len(Child._dependencies) == 1


# ======================================================================
# ТЕСТЫ: @connection
# ======================================================================
class TestConnectionDecorator:
    """Проверка декоратора @connection."""

    def test_connection_adds_connection_info(self):
        """@connection добавляет запись в _connections класса."""
        @connection("db", MockResourceManager, description="База данных")
        class TestAction(MockAction):
            @summary_aspect("test")
            async def summary(self, params, state, deps, connections):
                return MockResult()

        assert hasattr(TestAction, "_connections")
        assert len(TestAction._connections) == 1
        conn = TestAction._connections[0]
        assert conn["key"] == "db"
        assert conn["class"] == MockResourceManager
        assert conn["description"] == "База данных"

    def test_connection_multiple_decorators(self):
        """Несколько @connection добавляются в список."""
        # Декораторы применяются снизу вверх:
        # сначала @connection("cache", ...), затем @connection("db", ...)
        # Проверяем set ключей, не порядок
        @connection("db", MockResourceManager)
        @connection("cache", MockResourceManager)
        class TestAction(MockAction):
            @summary_aspect("test")
            async def summary(self, params, state, deps, connections):
                return MockResult()

        assert len(TestAction._connections) == 2
        keys = {c["key"] for c in TestAction._connections}
        assert keys == {"db", "cache"}

    def test_connection_does_not_mutate_parent_class(self):
        """Список соединений копируется, родительский класс не изменяется."""
        class Parent(MockAction):
            pass

        @connection("db", MockResourceManager)
        class Child(Parent):
            @summary_aspect("test")
            async def summary(self, params, state, deps, connections):
                return MockResult()

        # Parent не должен получить _connections от декоратора Child
        assert "_connections" not in Parent.__dict__
        assert hasattr(Child, "_connections")
        assert len(Child._connections) == 1