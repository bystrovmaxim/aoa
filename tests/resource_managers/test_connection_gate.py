"""
Тесты для ConnectionGate и ConnectionGateHost — шлюза управления соединениями действия.

Проверяем:
- Регистрацию соединений (ConnectionInfo)
- Повторную регистрацию (должна вызывать ValueError)
- Получение по ключу (get_by_key)
- Получение всех ключей (get_all_keys)
- Получение всех компонентов (get_components)
- Удаление соединений (unregister)
- Заморозку шлюза (freeze)
- Обработку ошибок (регистрация/удаление после заморозки)
- Сбор соединений через ConnectionGateHost (миксин)
"""

import pytest

from action_machine.ResourceManagers.BaseResourceManager import BaseResourceManager
from action_machine.ResourceManagers.connection_gate import ConnectionGate, ConnectionInfo
from action_machine.ResourceManagers.connection_gate_host import ConnectionGateHost


# ----------------------------------------------------------------------
# Тестовые классы ресурсных менеджеров
# ----------------------------------------------------------------------
class MockResourceManager(BaseResourceManager):
    def get_wrapper_class(self):
        return None


class AnotherResourceManager(BaseResourceManager):
    def get_wrapper_class(self):
        return None


# ======================================================================
# Тесты для ConnectionGate
# ======================================================================

class TestConnectionGate:
    """Тесты для ConnectionGate."""

    # ------------------------------------------------------------------
    # Регистрация
    # ------------------------------------------------------------------
    def test_register(self):
        """Регистрация соединения."""
        gate = ConnectionGate()
        info = ConnectionInfo(key="db", klass=MockResourceManager, description="Database connection")

        result = gate.register(info)

        assert result is info
        assert gate.get_components() == [info]
        assert gate.get_by_key("db") is info
        assert gate.get_all_keys() == ["db"]

    def test_register_with_description(self):
        """Регистрация соединения с описанием."""
        gate = ConnectionGate()
        info = ConnectionInfo(key="cache", klass=MockResourceManager, description="Redis cache")

        gate.register(info)
        assert gate.get_by_key("cache").description == "Redis cache"

    def test_register_duplicate_raises(self):
        """Повторная регистрация соединения с тем же ключом вызывает ValueError."""
        gate = ConnectionGate()
        info1 = ConnectionInfo(key="db", klass=MockResourceManager, description="First")
        info2 = ConnectionInfo(key="db", klass=AnotherResourceManager, description="Second")

        gate.register(info1)
        with pytest.raises(ValueError, match="Connection with key 'db' already registered"):
            gate.register(info2)

    def test_register_multiple_different_keys(self):
        """Регистрация нескольких соединений с разными ключами."""
        gate = ConnectionGate()
        info_db = ConnectionInfo(key="db", klass=MockResourceManager, description="DB")
        info_cache = ConnectionInfo(key="cache", klass=AnotherResourceManager, description="Cache")

        gate.register(info_db)
        gate.register(info_cache)

        assert gate.get_components() == [info_db, info_cache]
        assert gate.get_all_keys() == ["db", "cache"]
        assert gate.get_by_key("db") is info_db
        assert gate.get_by_key("cache") is info_cache

    # ------------------------------------------------------------------
    # Получение
    # ------------------------------------------------------------------
    def test_get_by_key_returns_none_if_not_registered(self):
        """get_by_key для незарегистрированного ключа возвращает None."""
        gate = ConnectionGate()
        assert gate.get_by_key("missing") is None

    def test_get_components_returns_copy(self):
        """get_components возвращает копию, внешние изменения не влияют на шлюз."""
        gate = ConnectionGate()
        info = ConnectionInfo(key="db", klass=MockResourceManager, description="")
        gate.register(info)

        components = gate.get_components()
        components.append(ConnectionInfo(key="fake", klass=MockResourceManager, description=""))

        assert gate.get_components() == [info]

    def test_get_all_keys_returns_copy(self):
        """get_all_keys возвращает копию списка."""
        gate = ConnectionGate()
        info = ConnectionInfo(key="db", klass=MockResourceManager, description="")
        gate.register(info)

        keys = gate.get_all_keys()
        keys.append("extra")

        assert gate.get_all_keys() == ["db"]

    # ------------------------------------------------------------------
    # Удаление
    # ------------------------------------------------------------------
    def test_unregister(self):
        """Удаление соединения по ссылке."""
        gate = ConnectionGate()
        info = ConnectionInfo(key="db", klass=MockResourceManager, description="")
        gate.register(info)

        gate.unregister(info)
        assert gate.get_components() == []
        assert gate.get_by_key("db") is None

    def test_unregister_nonexistent_ignored(self):
        """Удаление незарегистрированного соединения не вызывает ошибку."""
        gate = ConnectionGate()
        info = ConnectionInfo(key="db", klass=MockResourceManager, description="")
        gate.unregister(info)  # не падает

    def test_unregister_wrong_instance_does_nothing(self):
        """
        Если передан другой объект ConnectionInfo с тем же ключом,
        удаление не происходит (требуется точное совпадение по ссылке).
        """
        gate = ConnectionGate()
        original = ConnectionInfo(key="db", klass=MockResourceManager, description="Original")
        other = ConnectionInfo(key="db", klass=MockResourceManager, description="Other")

        gate.register(original)
        gate.unregister(other)

        assert gate.get_components() == [original]

    # ------------------------------------------------------------------
    # Заморозка
    # ------------------------------------------------------------------
    def test_freeze_disables_register(self):
        """После freeze() регистрация запрещена."""
        gate = ConnectionGate()
        gate.freeze()

        info = ConnectionInfo(key="db", klass=MockResourceManager, description="")
        with pytest.raises(RuntimeError, match="ConnectionGate is frozen"):
            gate.register(info)

    def test_freeze_disables_unregister(self):
        """После freeze() удаление запрещено."""
        gate = ConnectionGate()
        info = ConnectionInfo(key="db", klass=MockResourceManager, description="")
        gate.register(info)
        gate.freeze()

        with pytest.raises(RuntimeError, match="ConnectionGate is frozen"):
            gate.unregister(info)

    def test_freeze_idempotent(self):
        """Повторный вызов freeze() не вызывает ошибок."""
        gate = ConnectionGate()
        gate.freeze()
        gate.freeze()  # не падает

    # ------------------------------------------------------------------
    # Методы после заморозки
    # ------------------------------------------------------------------
    def test_get_methods_work_after_freeze(self):
        """Методы получения работают после заморозки (только чтение)."""
        gate = ConnectionGate()
        info = ConnectionInfo(key="db", klass=MockResourceManager, description="Test")
        gate.register(info)
        gate.freeze()

        assert gate.get_by_key("db") is info
        assert gate.get_all_keys() == ["db"]
        assert gate.get_components() == [info]


# ======================================================================
# Тесты для ConnectionGateHost (миксин, который собирает соединения)
# ======================================================================

class TestConnectionGateHost:
    """
    Тесты для ConnectionGateHost — миксина, который присоединяет ConnectionGate к классу действия.
    Проверяем:
    - Сбор соединений из временного атрибута _connection_info
    - Заморозку шлюза после сборки
    - Отсутствие мутации родительских данных при наследовании
    """

    def test_connections_are_collected(self):
        """Соединения из _connection_info регистрируются в шлюзе."""
        class MyAction(ConnectionGateHost):
            _connection_info = [
                ConnectionInfo(key="db", klass=MockResourceManager, description="Database"),
                ConnectionInfo(key="cache", klass=AnotherResourceManager, description="Cache"),
            ]

        gate = MyAction.get_connection_gate()
        assert gate.get_by_key("db") is not None
        assert gate.get_by_key("db").description == "Database"
        assert gate.get_by_key("cache") is not None
        assert gate.get_by_key("cache").klass is AnotherResourceManager

    def test_gate_is_frozen_after_collection(self):
        """После сбора шлюз замораживается, регистрация новых соединений невозможна."""
        class MyAction(ConnectionGateHost):
            _connection_info = [
                ConnectionInfo(key="db", klass=MockResourceManager, description=""),
            ]

        gate = MyAction.get_connection_gate()
        with pytest.raises(RuntimeError, match="ConnectionGate is frozen"):
            gate.register(ConnectionInfo(key="new", klass=MockResourceManager, description=""))

    def test_inheritance_does_not_share_gate(self):
        """
        При наследовании каждый класс получает свой собственный шлюз,
        а не разделяет с родителем.
        """
        class Parent(ConnectionGateHost):
            _connection_info = [
                ConnectionInfo(key="parent_db", klass=MockResourceManager, description="Parent DB"),
            ]

        class Child(Parent):
            _connection_info = [
                ConnectionInfo(key="child_cache", klass=AnotherResourceManager, description="Child Cache"),
            ]

        parent_gate = Parent.get_connection_gate()
        child_gate = Child.get_connection_gate()

        # Гейты разные
        assert parent_gate is not child_gate

        # У родителя только parent_db
        assert parent_gate.get_by_key("parent_db") is not None
        assert parent_gate.get_by_key("child_cache") is None

        # У ребёнка только child_cache
        assert child_gate.get_by_key("child_cache") is not None
        assert child_gate.get_by_key("parent_db") is None

    def test_class_without_connections_has_empty_gate(self):
        """Если класс не имеет _connection_info, шлюз остаётся пустым (но замороженным)."""
        class MyAction(ConnectionGateHost):
            pass

        gate = MyAction.get_connection_gate()
        assert gate.get_components() == []
        # Шлюз заморожен, регистрация невозможна
        with pytest.raises(RuntimeError, match="ConnectionGate is frozen"):
            gate.register(ConnectionInfo(key="db", klass=MockResourceManager, description=""))


# ======================================================================
# Тесты для декоратора @connection (интеграция с ConnectionGateHost)
# ======================================================================

class TestConnectionDecorator:
    """Тесты для декоратора @connection."""

    def test_connection_decorator_adds_info(self):
        """Декоратор @connection добавляет информацию в _connection_info."""
        from action_machine.ResourceManagers.connection import connection

        @connection("db", MockResourceManager, description="Test DB")
        class MyAction(ConnectionGateHost):
            pass

        assert MyAction._connection_info is not None
        assert len(MyAction._connection_info) == 1
        info = MyAction._connection_info[0]
        assert info.key == "db"
        assert info.klass is MockResourceManager
        assert info.description == "Test DB"

    def test_connection_decorator_multiple(self):
        """Несколько декораторов @connection добавляют несколько записей в правильном порядке."""
        from action_machine.ResourceManagers.connection import connection

        @connection("db", MockResourceManager, description="Database")
        @connection("cache", AnotherResourceManager, description="Cache")
        class MyAction(ConnectionGateHost):
            pass

        assert MyAction._connection_info is not None
        assert len(MyAction._connection_info) == 2
        # Декораторы применяются снизу вверх, поэтому первым будет "cache"
        assert MyAction._connection_info[0].key == "cache"
        assert MyAction._connection_info[1].key == "db"

    def test_connection_decorator_raises_if_not_inheriting_gate_host(self):
        """Если класс не наследует ConnectionGateHost, декоратор выбрасывает TypeError."""
        from action_machine.ResourceManagers.connection import connection

        class NotHost:
            pass

        with pytest.raises(TypeError, match="can only be applied to classes inheriting ConnectionGateHost"):
            @connection("db", MockResourceManager)
            class BadAction(NotHost):
                pass