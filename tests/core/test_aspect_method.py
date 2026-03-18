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
from typing import Any

from action_machine.Core.AspectMethod import aspect, summary_aspect, depends, connection
from action_machine.Core.BaseAction import BaseAction
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseResult import BaseResult
from action_machine.Core.BaseState import BaseState
from action_machine.Core.DependencyFactory import DependencyFactory
from action_machine.ResourceManagers.BaseResourceManager import BaseResourceManager


# ----------------------------------------------------------------------
# Вспомогательные классы
# ----------------------------------------------------------------------
class MockParams(BaseParams):
    """Тестовые параметры."""
    pass


class MockResult(BaseResult):
    """Тестовый результат."""
    pass


class MockAction(BaseAction[MockParams, MockResult]):
    """Базовое тестовое действие."""
    pass


class MockResourceManager(BaseResourceManager):
    """Тестовый ресурсный менеджер."""

    def get_wrapper_class(self) -> type[BaseResourceManager] | None:
        return None


# ======================================================================
# ТЕСТЫ: @aspect
# ======================================================================
class TestAspectDecorator:
    """Проверка декоратора @aspect."""

    def test_aspect_sets_correct_attributes(self) -> None:
        """@aspect должен установить _is_aspect, _aspect_description, _aspect_type='regular'."""

        class TestAction(MockAction):
            @aspect("Описание аспекта")
            async def my_aspect(
                self,
                params: MockParams,
                state: BaseState,
                deps: DependencyFactory,
                connections: dict[str, BaseResourceManager],
            ) -> dict[str, object]:
                return {}

        assert hasattr(TestAction.my_aspect, "_is_aspect")
        assert TestAction.my_aspect._is_aspect is True
        assert TestAction.my_aspect._aspect_description == "Описание аспекта"
        assert TestAction.my_aspect._aspect_type == "regular"

    def test_aspect_on_sync_function_raises_type_error(self) -> None:
        """@aspect должен кидать TypeError, если функция не async."""

        with pytest.raises(TypeError, match="должен быть async def"):

            class TestAction(MockAction):
                @aspect("Синхронный")
                def my_aspect(  # type: ignore[misc]
                    self,
                    params: MockParams,
                    state: BaseState,
                    deps: DependencyFactory,
                    connections: dict[str, BaseResourceManager],
                ) -> dict[str, object]:
                    return {}

    def test_aspect_preserves_method_metadata(self) -> None:
        """@aspect не должен затирать имя и другие атрибуты метода."""

        class TestAction(MockAction):
            @aspect("Тест")
            async def my_aspect(
                self,
                params: MockParams,
                state: BaseState,
                deps: DependencyFactory,
                connections: dict[str, BaseResourceManager],
            ) -> dict[str, object]:
                """docstring"""
                return {}

        assert TestAction.my_aspect.__name__ == "my_aspect"
        assert TestAction.my_aspect.__doc__ == "docstring"


# ======================================================================
# ТЕСТЫ: @summary_aspect
# ======================================================================
class TestSummaryAspectDecorator:
    """Проверка декоратора @summary_aspect."""

    def test_summary_aspect_sets_correct_attributes(self) -> None:
        """@summary_aspect должен установить _aspect_type='summary'."""

        class TestAction(MockAction):
            @summary_aspect("Главный аспект")
            async def my_summary(
                self,
                params: MockParams,
                state: BaseState,
                deps: DependencyFactory,
                connections: dict[str, BaseResourceManager],
            ) -> MockResult:
                return MockResult()

        assert hasattr(TestAction.my_summary, "_is_aspect")
        assert TestAction.my_summary._is_aspect is True
        assert TestAction.my_summary._aspect_description == "Главный аспект"
        assert TestAction.my_summary._aspect_type == "summary"

    def test_summary_aspect_on_sync_function_raises_type_error(self) -> None:
        """@summary_aspect должен кидать TypeError, если функция не async."""

        with pytest.raises(TypeError, match="должен быть async def"):

            class TestAction(MockAction):
                @summary_aspect("Синхронный")
                def my_summary(  # type: ignore[misc]
                    self,
                    params: MockParams,
                    state: BaseState,
                    deps: DependencyFactory,
                    connections: dict[str, BaseResourceManager],
                ) -> MockResult:
                    return MockResult()


# ======================================================================
# ТЕСТЫ: @depends
# ======================================================================
class TestDependsDecorator:
    """Проверка декоратора @depends."""

    def test_depends_adds_dependency(self) -> None:
        """@depends добавляет запись в _dependencies класса."""

        @depends(str, description="Строковый сервис")
        class TestAction(MockAction):
            @summary_aspect("test")
            async def summary(
                self,
                params: MockParams,
                state: BaseState,
                deps: DependencyFactory,
                connections: dict[str, BaseResourceManager],
            ) -> MockResult:
                return MockResult()

        assert hasattr(TestAction, "_dependencies")
        assert len(TestAction._dependencies) == 1
        dep = TestAction._dependencies[0]
        assert dep["class"] == str
        assert dep["description"] == "Строковый сервис"
        assert dep["factory"] is None

    def test_depends_with_factory(self) -> None:
        """@depends может принимать фабрику."""

        def factory() -> str:
            return "created"

        @depends(int, description="Число", factory=factory)
        class TestAction(MockAction):
            @summary_aspect("test")
            async def summary(
                self,
                params: MockParams,
                state: BaseState,
                deps: DependencyFactory,
                connections: dict[str, BaseResourceManager],
            ) -> MockResult:
                return MockResult()

        dep = TestAction._dependencies[0]
        assert dep["class"] == int
        assert dep["factory"] is factory

    def test_depends_multiple_decorators(self) -> None:
        """Несколько @depends добавляются в список."""
        # Декораторы применяются снизу вверх:
        # сначала @depends(float), затем @depends(int), затем @depends(str)
        # Каждый последующий добавляет в конец, но порядок не гарантирован.
        @depends(str)
        @depends(int)
        @depends(float)
        class TestAction(MockAction):
            @summary_aspect("test")
            async def summary(
                self,
                params: MockParams,
                state: BaseState,
                deps: DependencyFactory,
                connections: dict[str, BaseResourceManager],
            ) -> MockResult:
                return MockResult()

        assert len(TestAction._dependencies) == 3
        classes = {d["class"] for d in TestAction._dependencies}
        assert classes == {str, int, float}

    def test_depends_does_not_mutate_parent_class(self) -> None:
        """Список зависимостей копируется, родительский класс не изменяется."""

        class Parent(MockAction):
            pass

        @depends(str)
        class Child(Parent):
            @summary_aspect("test")
            async def summary(
                self,
                params: MockParams,
                state: BaseState,
                deps: DependencyFactory,
                connections: dict[str, BaseResourceManager],
            ) -> MockResult:
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

    def test_connection_adds_connection_info(self) -> None:
        """@connection добавляет запись в _connections класса."""

        @connection("db", MockResourceManager, description="База данных")
        class TestAction(MockAction):
            @summary_aspect("test")
            async def summary(
                self,
                params: MockParams,
                state: BaseState,
                deps: DependencyFactory,
                connections: dict[str, BaseResourceManager],
            ) -> MockResult:
                return MockResult()

        assert hasattr(TestAction, "_connections")
        assert len(TestAction._connections) == 1
        conn = TestAction._connections[0]
        assert conn["key"] == "db"
        assert conn["class"] == MockResourceManager
        assert conn["description"] == "База данных"

    def test_connection_multiple_decorators(self) -> None:
        """Несколько @connection добавляются в список."""
        # Декораторы применяются снизу вверх:
        # сначала @connection("cache", ...), затем @connection("db", ...)
        @connection("db", MockResourceManager)
        @connection("cache", MockResourceManager)
        class TestAction(MockAction):
            @summary_aspect("test")
            async def summary(
                self,
                params: MockParams,
                state: BaseState,
                deps: DependencyFactory,
                connections: dict[str, BaseResourceManager],
            ) -> MockResult:
                return MockResult()

        assert len(TestAction._connections) == 2
        keys = {c["key"] for c in TestAction._connections}
        assert keys == {"db", "cache"}

    def test_connection_does_not_mutate_parent_class(self) -> None:
        """Список соединений копируется, родительский класс не изменяется."""

        class Parent(MockAction):
            pass

        @connection("db", MockResourceManager)
        class Child(Parent):
            @summary_aspect("test")
            async def summary(
                self,
                params: MockParams,
                state: BaseState,
                deps: DependencyFactory,
                connections: dict[str, BaseResourceManager],
            ) -> MockResult:
                return MockResult()

        # Parent не должен получить _connections от декоратора Child
        assert "_connections" not in Parent.__dict__
        assert hasattr(Child, "_connections")
        assert len(Child._connections) == 1