# tests/decorators/test_connection_checks.py
"""
Тесты проверок декоратора @connection.

Покрывают все инварианты, объявленные в модуле connection.py:
    - Применение к классу с миксином — успех.
    - Несколько соединений с разными ключами — успех.
    - Наследование: дочерний класс не мутирует список родителя.
    - klass не является классом — TypeError.
    - klass не подкласс BaseResourceManager — TypeError.
    - key не строка — TypeError.
    - key пустая строка — ValueError.
    - Дубликат ключа — ValueError.
    - description не строка — TypeError.
    - Декоратор применён не к классу — TypeError.
    - Класс не наследует ConnectionGateHost — TypeError.

Архитектурная справка:
В новой архитектуре (через ClassMetadata) декоратор только добавляет записи 
в атрибут `_connection_info` класса. Дальнейшая валидация и сборка 
осуществляется в `MetadataBuilder`.
"""

import pytest

from action_machine.ResourceManagers.BaseResourceManager import BaseResourceManager
from action_machine.ResourceManagers.connection import ConnectionInfo, connection
from action_machine.ResourceManagers.connection_gate_host import ConnectionGateHost

# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательные классы
# ─────────────────────────────────────────────────────────────────────────────

class FakeDbManager(BaseResourceManager):
    """Заглушка менеджера базы данных для тестов."""
    def get_wrapper_class(self):
        """Обязательная реализация абстрактного метода."""
        return None

class FakeRedisManager(BaseResourceManager):
    """Заглушка менеджера Redis для тестов."""
    def get_wrapper_class(self):
        return None

class FakeMqManager(BaseResourceManager):
    """Заглушка менеджера очереди сообщений для тестов."""
    def get_wrapper_class(self):
        return None

class NotAResourceManager:
    """Обычный класс, не наследующий BaseResourceManager. Используется для тестов ошибок."""
    pass


class HostBase(ConnectionGateHost):
    """Минимальный класс с миксином ConnectionGateHost для тестов."""
    pass


# ─────────────────────────────────────────────────────────────────────────────
# Успешные сценарии
# ─────────────────────────────────────────────────────────────────────────────

class TestConnectionSuccess:
    """Проверка корректного применения @connection."""

    def test_single_connection(self):
        """Одно соединение успешно регистрируется в _connection_info."""
        @connection(FakeDbManager, key="db", description="Основная БД")
        class MyAction(HostBase):
            pass

        assert hasattr(MyAction, '_connection_info')
        assert len(MyAction._connection_info) == 1
        info = MyAction._connection_info[0]
        assert info.cls is FakeDbManager
        assert info.key == "db"
        assert info.description == "Основная БД"

    def test_multiple_connections(self):
        """Несколько соединений с разными ключами регистрируются корректно."""
        @connection(FakeDbManager, key="db")
        @connection(FakeRedisManager, key="cache")
        @connection(FakeMqManager, key="mq")
        class MyAction(HostBase):
            pass

        assert len(MyAction._connection_info) == 3
        keys = {info.key for info in MyAction._connection_info}
        assert keys == {"db", "cache", "mq"}

    def test_default_description(self):
        """Если описание не передано, используется пустая строка."""
        @connection(FakeDbManager, key="db")
        class MyAction(HostBase):
            pass

        assert MyAction._connection_info[0].description == ""

    def test_class_returned_unchanged(self):
        """Декоратор возвращает сам класс, не создавая оберток."""
        @connection(FakeDbManager, key="db")
        class MyAction(HostBase):
            pass

        assert isinstance(MyAction, type)
        assert issubclass(MyAction, HostBase)


# ─────────────────────────────────────────────────────────────────────────────
# Изоляция наследования
# ─────────────────────────────────────────────────────────────────────────────

class TestConnectionInheritance:
    """Проверка правильного наследования метаданных соединений."""

    def test_child_does_not_mutate_parent(self):
        """Дочерний класс получает свою копию соединений, родитель не меняется."""
        @connection(FakeDbManager, key="db")
        class Parent(HostBase):
            pass

        @connection(FakeRedisManager, key="cache")
        class Child(Parent):
            pass

        # У родителя только db
        assert len(Parent._connection_info) == 1
        assert Parent._connection_info[0].key == "db"

        # У ребенка db (от родителя) + cache (свой)
        child_keys = {info.key for info in Child._connection_info}
        assert child_keys == {"db", "cache"}

    def test_empty_child_inherits_parent_connections(self):
        """Дочерний класс без своих @connection наследует соединения родителя."""
        @connection(FakeDbManager, key="db")
        class Parent(HostBase):
            pass

        class Child(Parent):
            pass

        parent_info = getattr(Parent, '_connection_info', [])
        child_info = getattr(Child, '_connection_info', [])
        assert len(parent_info) == 1
        assert len(child_info) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# Ошибки
# ─────────────────────────────────────────────────────────────────────────────

class TestConnectionKlassErrors:
    """Проверка валидации целевого класса менеджера."""

    def test_not_a_class_raises(self):
        """Передача экземпляра вместо класса вызывает TypeError."""
        instance = FakeDbManager()
        with pytest.raises(TypeError, match="ожидает класс"):
            @connection(instance, key="db")
            class MyAction(HostBase):
                pass

    def test_string_instead_of_class_raises(self):
        """Передача строки вместо класса вызывает TypeError."""
        with pytest.raises(TypeError, match="ожидает класс"):
            @connection("FakeDbManager", key="db")
            class MyAction(HostBase):
                pass

    def test_not_resource_manager_raises(self):
        """Класс, не наследующий BaseResourceManager, вызывает TypeError."""
        with pytest.raises(TypeError, match="не является подклассом"):
            @connection(NotAResourceManager, key="db")
            class MyAction(HostBase):
                pass

    def test_none_instead_of_class_raises(self):
        """Передача None вместо класса вызывает TypeError."""
        with pytest.raises(TypeError, match="ожидает класс"):
            @connection(None, key="db")
            class MyAction(HostBase):
                pass


class TestConnectionKeyErrors:
    """Проверка валидации ключа (key)."""

    def test_key_not_string_raises(self):
        with pytest.raises(TypeError, match="key должен быть строкой"):
            @connection(FakeDbManager, key=123)
            class MyAction(HostBase):
                pass

    def test_key_none_raises(self):
        with pytest.raises(TypeError, match="key должен быть строкой"):
            @connection(FakeDbManager, key=None)
            class MyAction(HostBase):
                pass

    def test_key_empty_raises(self):
        with pytest.raises(ValueError, match="key не может быть пустой строкой"):
            @connection(FakeDbManager, key="")
            class MyAction(HostBase):
                pass


class TestConnectionDuplicateErrors:
    """Проверка на дубликаты ключей."""

    def test_duplicate_key_raises(self):
        """Повторное использование одного ключа вызывает ValueError."""
        with pytest.raises(ValueError, match="ключ.*уже объявлен"):
            @connection(FakeDbManager, key="db")
            @connection(FakeRedisManager, key="db")
            class MyAction(HostBase):
                pass


class TestConnectionTargetErrors:
    """Проверка цели декорирования."""

    def test_applied_to_function_raises(self):
        """Применение к функции вместо класса вызывает TypeError."""
        with pytest.raises(TypeError, match="только к классу"):
            @connection(FakeDbManager, key="db")
            def some_function():
                pass

    def test_applied_to_class_without_mixin_raises(self):
        """Применение к классу без ConnectionGateHost вызывает TypeError."""
        with pytest.raises(TypeError, match="не наследует ConnectionGateHost"):
            @connection(FakeDbManager, key="db")
            class PlainClass:
                pass


class TestConnectionDescriptionErrors:
    """Проверка параметра description."""

    def test_number_description_raises(self):
        with pytest.raises(TypeError, match="description должен быть строкой"):
            @connection(FakeDbManager, key="db", description=123)
            class MyAction(HostBase):
                pass


class TestConnectionInfoImmutability:
    """Проверка иммутабельности датакласса ConnectionInfo."""

    def test_cannot_modify_cls(self):
        info = ConnectionInfo(cls=FakeDbManager, key="db")
        with pytest.raises(AttributeError):
            info.cls = FakeRedisManager
