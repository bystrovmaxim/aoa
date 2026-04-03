"""
Тесты MetadataBuilder — базовые сценарии сборки ClassMetadata.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет, что MetadataBuilder корректно собирает ClassMetadata из классов
в базовых сценариях: пустой класс, класс с ролью, с зависимостями,
с соединениями. Также проверяет отклонение невалидных аргументов.

MetadataBuilder.build(cls) — единственная точка входа. Принимает класс,
обходит атрибуты и методы, вызывает коллекторы и валидаторы, возвращает
frozen ClassMetadata.

═══════════════════════════════════════════════════════════════════════════════
СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

TestBuildEmptyClass
    - Пустой класс возвращает ClassMetadata без ошибок.
    - role = None.
    - Все коллекции пустые.

TestBuildWithRole
    - Класс с @check_roles("admin") → role.spec == "admin".
    - Класс с @check_roles(ROLE_NONE) → role.spec == ROLE_NONE.
    - role без других метаданных.

TestBuildWithDependencies
    - Класс с @depends(ServiceA) → dependencies содержит ServiceA.
    - Классы зависимостей сохраняются.

TestBuildWithConnections
    - Класс с @connection(Manager, "db") → connections содержит ключ "db".
    - Ключ соединения сохраняется.

TestBuildErrors
    - Не класс (экземпляр) → TypeError.
    - Не класс (функция) → TypeError.

TestBuildIdempotency
    - Повторный вызов build для одного класса возвращает идентичный результат.
"""

import pytest

from action_machine.auth.check_roles import check_roles
from action_machine.auth.constants import ROLE_ANY, ROLE_NONE
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.dependencies.depends import depends
from action_machine.metadata.builder import MetadataBuilder
from action_machine.resource_managers.base_resource_manager import BaseResourceManager
from action_machine.resource_managers.connection import connection

# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные классы
# ═════════════════════════════════════════════════════════════════════════════


class _EmptyClass:
    """Пустой класс без декораторов — минимальный ввод для Builder."""
    pass


class _SimpleParams(BaseParams):
    """Параметры для тестовых действий."""
    pass


class _SimpleResult(BaseResult):
    """Результат для тестовых действий."""
    pass


class _ServiceA:
    """Тестовая зависимость A."""
    pass


class _ServiceB:
    """Тестовая зависимость B."""
    pass


class _MockManager(BaseResourceManager):
    """Мок менеджера ресурсов для соединений."""
    pass


class _CacheManager(BaseResourceManager):
    """Мок менеджера кеша для соединений."""
    pass


@check_roles("admin")
class _AdminAction(BaseAction["_SimpleParams", "_SimpleResult"]):
    """Действие с ролью admin."""
    pass


@check_roles(ROLE_NONE)
class _PublicAction(BaseAction["_SimpleParams", "_SimpleResult"]):
    """Действие без ролевых ограничений."""
    pass


@check_roles(ROLE_ANY)
class _AnyRoleAction(BaseAction["_SimpleParams", "_SimpleResult"]):
    """Действие, требующее любую роль."""
    pass


@check_roles(["admin", "manager"])
class _MultiRoleAction(BaseAction["_SimpleParams", "_SimpleResult"]):
    """Действие с несколькими допустимыми ролями."""
    pass


@check_roles(ROLE_NONE)
@depends(_ServiceA)
class _ActionWithOneDepAction(BaseAction["_SimpleParams", "_SimpleResult"]):
    """Действие с одной зависимостью."""
    pass


@check_roles(ROLE_NONE)
@depends(_ServiceA)
@depends(_ServiceB)
class _ActionWithTwoDepsAction(BaseAction["_SimpleParams", "_SimpleResult"]):
    """Действие с двумя зависимостями."""
    pass


@check_roles(ROLE_NONE)
@connection(_MockManager, key="db", description="Основная БД")
class _ActionWithOneConnAction(BaseAction["_SimpleParams", "_SimpleResult"]):
    """Действие с одним соединением."""
    pass


@check_roles(ROLE_NONE)
@connection(_MockManager, key="db", description="Основная БД")
@connection(_CacheManager, key="cache", description="Кеш")
class _ActionWithTwoConnsAction(BaseAction["_SimpleParams", "_SimpleResult"]):
    """Действие с двумя соединениями."""
    pass


# ═════════════════════════════════════════════════════════════════════════════
# Пустой класс
# ═════════════════════════════════════════════════════════════════════════════


class TestBuildEmptyClass:
    """Проверяет сборку метаданных из пустого класса."""

    def test_returns_class_metadata(self):
        """build возвращает экземпляр ClassMetadata."""
        # Arrange
        builder = MetadataBuilder()

        # Act
        result = builder.build(_EmptyClass)

        # Assert
        assert result is not None
        assert result.class_ref is _EmptyClass

    def test_role_is_none(self):
        """Пустой класс не имеет роли."""
        # Arrange & Act
        result = MetadataBuilder().build(_EmptyClass)

        # Assert
        assert result.role is None
        assert result.has_role() is False

    def test_collections_are_empty(self):
        """Все коллекции пустого класса пустые."""
        # Arrange & Act
        result = MetadataBuilder().build(_EmptyClass)

        # Assert
        assert result.dependencies == ()
        assert result.connections == ()
        assert result.aspects == ()
        assert result.checkers == ()
        assert result.subscriptions == ()
        assert result.sensitive_fields == ()


# ═════════════════════════════════════════════════════════════════════════════
# Роль
# ═════════════════════════════════════════════════════════════════════════════


class TestBuildWithRole:
    """Проверяет сборку метаданных с различными ролевыми спецификациями."""

    def test_single_role_collected(self):
        """@check_roles('admin') → role.spec == 'admin'."""
        # Arrange & Act
        result = MetadataBuilder().build(_AdminAction)

        # Assert
        assert result.has_role() is True
        assert result.role.spec == "admin"

    def test_role_none_collected(self):
        """@check_roles(ROLE_NONE) → role.spec == ROLE_NONE."""
        # Arrange & Act
        result = MetadataBuilder().build(_PublicAction)

        # Assert
        assert result.has_role() is True
        assert result.role.spec == ROLE_NONE

    def test_role_any_collected(self):
        """@check_roles(ROLE_ANY) → role.spec == ROLE_ANY."""
        # Arrange & Act
        result = MetadataBuilder().build(_AnyRoleAction)

        # Assert
        assert result.has_role() is True
        assert result.role.spec == ROLE_ANY

    def test_role_list_collected(self):
        """@check_roles(['admin', 'manager']) → role.spec == ['admin', 'manager']."""
        # Arrange & Act
        result = MetadataBuilder().build(_MultiRoleAction)

        # Assert
        assert result.has_role() is True
        assert result.role.spec == ["admin", "manager"]

    def test_role_without_other_metadata(self):
        """Класс с ролью, но без зависимостей и аспектов."""
        # Arrange & Act
        result = MetadataBuilder().build(_AdminAction)

        # Assert
        assert result.has_dependencies() is False
        assert result.has_connections() is False
        assert result.has_aspects() is False


# ═════════════════════════════════════════════════════════════════════════════
# Зависимости
# ═════════════════════════════════════════════════════════════════════════════


class TestBuildWithDependencies:
    """Проверяет сборку метаданных с зависимостями."""

    def test_single_dependency_collected(self):
        """Одна зависимость корректно собирается."""
        # Arrange & Act
        result = MetadataBuilder().build(_ActionWithOneDepAction)

        # Assert
        assert result.has_dependencies() is True
        assert len(result.dependencies) == 1

    def test_dependency_class_preserved(self):
        """Класс зависимости сохраняется в DependencyInfo."""
        # Arrange & Act
        result = MetadataBuilder().build(_ActionWithOneDepAction)

        # Assert
        assert result.dependencies[0].cls is _ServiceA

    def test_two_dependencies_collected(self):
        """Две зависимости корректно собираются."""
        # Arrange & Act
        result = MetadataBuilder().build(_ActionWithTwoDepsAction)

        # Assert
        assert len(result.dependencies) == 2

    def test_dependency_classes_preserved(self):
        """Классы обеих зависимостей сохраняются."""
        # Arrange & Act
        result = MetadataBuilder().build(_ActionWithTwoDepsAction)

        # Assert
        classes = result.get_dependency_classes()
        assert _ServiceA in classes
        assert _ServiceB in classes


# ═════════════════════════════════════════════════════════════════════════════
# Соединения
# ═════════════════════════════════════════════════════════════════════════════


class TestBuildWithConnections:
    """Проверяет сборку метаданных с соединениями."""

    def test_single_connection_collected(self):
        """Одно соединение корректно собирается."""
        # Arrange & Act
        result = MetadataBuilder().build(_ActionWithOneConnAction)

        # Assert
        assert result.has_connections() is True
        assert len(result.connections) == 1

    def test_connection_key_preserved(self):
        """Ключ соединения сохраняется в ConnectionInfo."""
        # Arrange & Act
        result = MetadataBuilder().build(_ActionWithOneConnAction)

        # Assert
        assert result.connections[0].key == "db"

    def test_two_connections_collected(self):
        """Два соединения корректно собираются."""
        # Arrange & Act
        result = MetadataBuilder().build(_ActionWithTwoConnsAction)

        # Assert
        assert len(result.connections) == 2

    def test_connection_keys_preserved(self):
        """Ключи обоих соединений сохраняются."""
        # Arrange & Act
        result = MetadataBuilder().build(_ActionWithTwoConnsAction)

        # Assert
        keys = result.get_connection_keys()
        assert "db" in keys
        assert "cache" in keys


# ═════════════════════════════════════════════════════════════════════════════
# Ошибки
# ═════════════════════════════════════════════════════════════════════════════


class TestBuildErrors:
    """Проверяет, что build отклоняет невалидные аргументы."""

    def test_not_a_class_raises_error(self):
        """Передача экземпляра вместо класса вызывает ошибку."""
        # Arrange
        instance = _EmptyClass()

        # Act & Assert
        with pytest.raises((TypeError, ValueError)):
            MetadataBuilder().build(instance)

    def test_function_raises_error(self):
        """Передача функции вместо класса вызывает ошибку."""
        # Arrange
        def some_func():
            pass

        # Act & Assert
        with pytest.raises((TypeError, ValueError)):
            MetadataBuilder().build(some_func)


# ═════════════════════════════════════════════════════════════════════════════
# Идемпотентность
# ═════════════════════════════════════════════════════════════════════════════


class TestBuildIdempotency:
    """Проверяет, что повторная сборка даёт идентичный результат."""

    def test_repeated_build_same_result(self):
        """Два вызова build для одного класса возвращают одинаковый результат."""
        # Arrange
        builder = MetadataBuilder()

        # Act
        result1 = builder.build(_AdminAction)
        result2 = builder.build(_AdminAction)

        # Assert
        assert result1.class_ref is result2.class_ref
        assert result1.class_name == result2.class_name
        assert result1.role.spec == result2.role.spec
        assert len(result1.dependencies) == len(result2.dependencies)
