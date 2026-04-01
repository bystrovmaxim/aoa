# tests2/decorators/test_connection_decorator.py
"""
Тесты декоратора @connection — объявление подключения к внешнему ресурсу.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Декоратор @connection объявляет, что действие использует внешний ресурс
(база данных, кеш, очередь сообщений), управляемый через ResourceManager.
Каждое соединение идентифицируется строковым ключом (key), по которому
аспект обращается к нему: connections["db"], connections["cache"].

Декоратор при применении:
1. Проверяет, что klass — подкласс BaseResourceManager.
2. Проверяет, что целевой класс наследует ConnectionGateHost.
3. Проверяет, что key — непустая строка.
4. Проверяет отсутствие дубликатов ключей.
5. Записывает ConnectionInfo в cls._connection_info.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Валидные аргументы:
    - Один @connection с key и description.
    - Несколько @connection с разными ключами.
    - @connection без description (пустая строка по умолчанию).

Запись _connection_info:
    - ConnectionInfo(cls, key, description) записывается в список.

Наследование:
    - Дочерний класс наследует connections родителя.
    - Дочерний добавляет свои без мутации родителя.

Невалидные аргументы:
    - klass не подкласс BaseResourceManager → TypeError.
    - key не строка → TypeError.
    - key пустая строка → ValueError.
    - description не строка → TypeError.
    - Дублирование ключа → ValueError.

Невалидные цели:
    - Применён к функции → TypeError.
    - Класс не наследует ConnectionGateHost → TypeError.

Интеграция:
    - MetadataBuilder собирает connections из _connection_info.
    - metadata.get_connection_keys() возвращает кортеж ключей.
"""

import pytest

from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth import ROLE_NONE, check_roles
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.gate_coordinator import GateCoordinator
from action_machine.core.meta_decorator import meta
from action_machine.resource_managers.base_resource_manager import BaseResourceManager
from action_machine.resource_managers.connection import ConnectionInfo, connection
from action_machine.resource_managers.connection_gate_host import ConnectionGateHost
from tests2.domain import FullAction

# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные классы
# ═════════════════════════════════════════════════════════════════════════════


@meta(description="Мок-менеджер для тестов @connection")
class _MockManager(BaseResourceManager):
    """Минимальная реализация BaseResourceManager для тестов."""

    def get_wrapper_class(self):
        return None


@meta(description="Второй мок-менеджер")
class _CacheManager(BaseResourceManager):
    """Второй менеджер для тестов множественных connections."""

    def get_wrapper_class(self):
        return None


# ═════════════════════════════════════════════════════════════════════════════
# Валидные аргументы
# ═════════════════════════════════════════════════════════════════════════════


class TestValidArgs:
    """Декоратор принимает валидные аргументы и записывает _connection_info."""

    def test_single_connection(self) -> None:
        """
        @connection(Manager, key="db") — одно подключение.

        ConnectionInfo(cls=Manager, key="db", description="")
        записывается в cls._connection_info.
        """
        # Arrange & Act
        @meta(description="Тест")
        @check_roles(ROLE_NONE)
        @connection(_MockManager, key="db", description="Основная БД")
        class _Action(BaseAction[BaseParams, BaseResult]):
            @summary_aspect("test")
            async def summary(self, params, state, box, connections):
                return BaseResult()

        # Assert — _connection_info содержит одну запись
        assert hasattr(_Action, "_connection_info")
        assert len(_Action._connection_info) == 1
        info = _Action._connection_info[0]
        assert info.cls is _MockManager
        assert info.key == "db"
        assert info.description == "Основная БД"

    def test_multiple_connections(self) -> None:
        """
        Несколько @connection с разными ключами — все записываются.
        """
        # Arrange & Act
        @meta(description="Тест")
        @check_roles(ROLE_NONE)
        @connection(_MockManager, key="db", description="БД")
        @connection(_CacheManager, key="cache", description="Кеш")
        class _Action(BaseAction[BaseParams, BaseResult]):
            @summary_aspect("test")
            async def summary(self, params, state, box, connections):
                return BaseResult()

        # Assert — обе записи
        assert len(_Action._connection_info) == 2
        keys = [c.key for c in _Action._connection_info]
        assert "db" in keys
        assert "cache" in keys

    def test_connection_without_description(self) -> None:
        """
        @connection(Manager, key="db") без description — пустая строка.
        """
        # Arrange & Act
        @meta(description="Тест")
        @check_roles(ROLE_NONE)
        @connection(_MockManager, key="db")
        class _Action(BaseAction[BaseParams, BaseResult]):
            @summary_aspect("test")
            async def summary(self, params, state, box, connections):
                return BaseResult()

        # Assert — description по умолчанию ""
        assert _Action._connection_info[0].description == ""

    def test_returns_class_unchanged(self) -> None:
        """
        Декоратор возвращает класс без изменений.
        """
        # Arrange
        @meta(description="Тест")
        @check_roles(ROLE_NONE)
        class _Original(BaseAction[BaseParams, BaseResult]):
            custom = 77

            @summary_aspect("test")
            async def summary(self, params, state, box, connections):
                return BaseResult()

        # Act
        _Decorated = connection(_MockManager, key="db")(_Original)

        # Assert — тот же объект
        assert _Decorated is _Original
        assert _Decorated.custom == 77

    def test_connection_info_is_frozen(self) -> None:
        """
        ConnectionInfo — frozen dataclass, поля нельзя изменить после создания.
        """
        # Arrange
        info = ConnectionInfo(cls=_MockManager, key="db", description="БД")

        # Act & Assert — попытка изменения → FrozenInstanceError
        with pytest.raises(AttributeError):
            info.key = "changed"


# ═════════════════════════════════════════════════════════════════════════════
# Наследование connections
# ═════════════════════════════════════════════════════════════════════════════


class TestInheritance:
    """Дочерний класс наследует connections родителя."""

    def test_child_inherits_parent_connections(self) -> None:
        """
        Дочерний класс без @connection видит connections родителя.
        """
        # Arrange
        @meta(description="Родитель")
        @check_roles(ROLE_NONE)
        @connection(_MockManager, key="db")
        class _Parent(BaseAction[BaseParams, BaseResult]):
            @summary_aspect("test")
            async def summary(self, params, state, box, connections):
                return BaseResult()

        @meta(description="Дочерний")
        @check_roles(ROLE_NONE)
        class _Child(_Parent):
            pass

        # Act
        child_conns = getattr(_Child, "_connection_info", [])

        # Assert — дочерний видит connection родителя
        assert len(child_conns) == 1
        assert child_conns[0].key == "db"

    def test_child_adds_without_mutating_parent(self) -> None:
        """
        @connection на дочернем не мутирует _connection_info родителя.
        """
        # Arrange
        @meta(description="Родитель")
        @check_roles(ROLE_NONE)
        @connection(_MockManager, key="db")
        class _Parent(BaseAction[BaseParams, BaseResult]):
            @summary_aspect("test")
            async def summary(self, params, state, box, connections):
                return BaseResult()

        # Act
        @meta(description="Дочерний")
        @check_roles(ROLE_NONE)
        @connection(_CacheManager, key="cache")
        class _Child(_Parent):
            pass

        # Assert — родитель: только db
        parent_conns = _Parent.__dict__.get("_connection_info", [])
        assert len(parent_conns) == 1
        assert parent_conns[0].key == "db"

        # Assert — дочерний: db + cache
        child_conns = _Child._connection_info
        assert len(child_conns) == 2


# ═════════════════════════════════════════════════════════════════════════════
# Невалидные аргументы
# ═════════════════════════════════════════════════════════════════════════════


class TestInvalidArgs:
    """Невалидные аргументы → TypeError или ValueError."""

    def test_klass_not_resource_manager_raises(self) -> None:
        """
        @connection(str, key="db") → TypeError.

        klass должен быть подклассом BaseResourceManager.
        """
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="не является подклассом"):
            connection(str, key="db")

    def test_klass_not_type_raises(self) -> None:
        """
        @connection("строка", key="db") → TypeError.

        klass должен быть классом, не строкой.
        """
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="ожидает класс"):
            connection("not_a_class", key="db")

    def test_key_not_string_raises(self) -> None:
        """
        @connection(Manager, key=42) → TypeError.
        """
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="key должен быть строкой"):
            connection(_MockManager, key=42)

    def test_key_empty_raises(self) -> None:
        """
        @connection(Manager, key="") → ValueError.
        """
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="key не может быть пустой"):
            connection(_MockManager, key="")

    def test_key_whitespace_raises(self) -> None:
        """
        @connection(Manager, key="   ") → ValueError.

        Строка из пробелов считается пустой после strip().
        """
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="key не может быть пустой"):
            connection(_MockManager, key="   ")

    def test_description_not_string_raises(self) -> None:
        """
        @connection(Manager, key="db", description=42) → TypeError.
        """
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="description должен быть строкой"):
            connection(_MockManager, key="db", description=42)

    def test_duplicate_key_raises(self) -> None:
        """
        Два @connection с одинаковым key → ValueError.
        """
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match='ключ "db" уже объявлен'):
            @connection(_MockManager, key="db")
            @connection(_CacheManager, key="db")
            class _Action(ConnectionGateHost):
                pass


# ═════════════════════════════════════════════════════════════════════════════
# Невалидные цели
# ═════════════════════════════════════════════════════════════════════════════


class TestInvalidTarget:
    """Декоратор применён к невалидной цели → TypeError."""

    def test_applied_to_function_raises(self) -> None:
        """
        @connection(Manager, key="db") на функции → TypeError.
        """
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="только к классу"):
            @connection(_MockManager, key="db")
            def _func():
                pass

    def test_applied_to_class_without_gate_host_raises(self) -> None:
        """
        @connection на классе без ConnectionGateHost → TypeError.
        """
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="не наследует ConnectionGateHost"):
            @connection(_MockManager, key="db")
            class _Plain:
                pass


# ═════════════════════════════════════════════════════════════════════════════
# Интеграция с MetadataBuilder и GateCoordinator
# ═════════════════════════════════════════════════════════════════════════════


class TestMetadataIntegration:
    """_connection_info корректно собирается в ClassMetadata.connections."""

    def test_domain_action_connections(self) -> None:
        """
        FullAction из доменной модели имеет connection с key="db".
        """
        # Arrange
        coordinator = GateCoordinator()

        # Act
        metadata = coordinator.get(FullAction)

        # Assert — одно соединение с ключом "db"
        assert metadata.has_connections()
        keys = metadata.get_connection_keys()
        assert "db" in keys

    def test_connection_keys_tuple(self) -> None:
        """
        get_connection_keys() возвращает кортеж строковых ключей.

        Используется машиной в _check_connections() для сравнения
        с фактически переданными ключами.
        """
        # Arrange
        @meta(description="Тест")
        @check_roles(ROLE_NONE)
        @connection(_MockManager, key="db")
        @connection(_CacheManager, key="cache")
        class _Action(BaseAction[BaseParams, BaseResult]):
            @summary_aspect("test")
            async def summary(self, params, state, box, connections):
                return BaseResult()

        coordinator = GateCoordinator()

        # Act
        metadata = coordinator.get(_Action)
        keys = metadata.get_connection_keys()

        # Assert — кортеж из двух ключей
        assert isinstance(keys, tuple)
        assert "db" in keys
        assert "cache" in keys
        assert len(keys) == 2
