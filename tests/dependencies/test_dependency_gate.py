# tests/dependencies/test_dependency_gate.py
"""
Тесты для DependencyGate и DependencyGateHost.

Проверяем:
- Регистрацию зависимостей (DependencyInfo)
- Повторную регистрацию (должна вызывать ValueError)
- Получение по классу (get_by_class)
- Получение всех классов (get_all_classes)
- Получение всех компонентов (get_components)
- Удаление зависимостей (unregister)
- Заморозку шлюза (freeze)
- Извлечение типа-ограничителя (bound) через DependencyGateHost
"""

import pytest

from action_machine.dependencies.dependency_gate import DependencyGate, DependencyInfo
from action_machine.dependencies.dependency_gate_host import DependencyGateHost
from action_machine.resource_managers.base_resource_manager import BaseResourceManager


# ----------------------------------------------------------------------
# Тестовые классы для зависимостей
# ----------------------------------------------------------------------
class ServiceA:
    pass


class ServiceB:
    pass


def factory_a():
    return ServiceA()


def factory_b():
    return ServiceB()


# ======================================================================
# Тесты для DependencyGate
# ======================================================================

class TestDependencyGate:
    """Тесты для DependencyGate."""

    # ------------------------------------------------------------------
    # Регистрация
    # ------------------------------------------------------------------
    def test_register(self):
        """Регистрация зависимости."""
        gate = DependencyGate()
        info = DependencyInfo(cls=ServiceA, factory=None, description="Test service")

        result = gate.register(info)

        assert result is info
        assert gate.get_components() == [info]
        assert gate.get_by_class(ServiceA) is info
        assert gate.get_all_classes() == [ServiceA]

    def test_register_with_factory(self):
        """Регистрация зависимости с фабрикой."""
        gate = DependencyGate()
        info = DependencyInfo(cls=ServiceA, factory=factory_a, description="With factory")

        gate.register(info)
        assert gate.get_by_class(ServiceA).factory is factory_a

    def test_register_duplicate_raises(self):
        """Повторная регистрация зависимости с тем же классом вызывает ValueError."""
        gate = DependencyGate()
        info1 = DependencyInfo(cls=ServiceA, factory=None, description="First")
        info2 = DependencyInfo(cls=ServiceA, factory=None, description="Second")

        gate.register(info1)
        with pytest.raises(ValueError, match="уже зарегистрирована"):
            gate.register(info2)

    def test_register_multiple_different_classes(self):
        """Регистрация нескольких зависимостей разных классов."""
        gate = DependencyGate()
        info_a = DependencyInfo(cls=ServiceA, factory=None, description="A")
        info_b = DependencyInfo(cls=ServiceB, factory=None, description="B")

        gate.register(info_a)
        gate.register(info_b)

        assert gate.get_components() == [info_a, info_b]
        assert gate.get_all_classes() == [ServiceA, ServiceB]
        assert gate.get_by_class(ServiceA) is info_a
        assert gate.get_by_class(ServiceB) is info_b

    # ------------------------------------------------------------------
    # Получение
    # ------------------------------------------------------------------
    def test_get_by_class_returns_none_if_not_registered(self):
        """get_by_class для незарегистрированного класса возвращает None."""
        gate = DependencyGate()
        assert gate.get_by_class(ServiceA) is None

    def test_get_components_returns_copy(self):
        """get_components возвращает копию, внешние изменения не влияют на шлюз."""
        gate = DependencyGate()
        info = DependencyInfo(cls=ServiceA, factory=None, description="")
        gate.register(info)

        components = gate.get_components()
        components.append(DependencyInfo(cls=ServiceB, factory=None, description=""))

        assert gate.get_components() == [info]

    def test_get_all_classes_returns_copy(self):
        """get_all_classes возвращает копию списка."""
        gate = DependencyGate()
        info = DependencyInfo(cls=ServiceA, factory=None, description="")
        gate.register(info)

        classes = gate.get_all_classes()
        classes.append(ServiceB)

        assert gate.get_all_classes() == [ServiceA]

    # ------------------------------------------------------------------
    # Удаление
    # ------------------------------------------------------------------
    def test_unregister(self):
        """Удаление зависимости по ссылке."""
        gate = DependencyGate()
        info = DependencyInfo(cls=ServiceA, factory=None, description="")
        gate.register(info)

        gate.unregister(info)
        assert gate.get_components() == []
        assert gate.get_by_class(ServiceA) is None

    def test_unregister_nonexistent_ignored(self):
        """Удаление незарегистрированной зависимости не вызывает ошибку."""
        gate = DependencyGate()
        info = DependencyInfo(cls=ServiceA, factory=None, description="")
        gate.unregister(info)  # не падает

    def test_unregister_wrong_instance_does_nothing(self):
        """
        Если передан другой объект DependencyInfo с тем же классом,
        удаление не происходит (требуется точное совпадение по ссылке).
        """
        gate = DependencyGate()
        original = DependencyInfo(cls=ServiceA, factory=None, description="Original")
        other = DependencyInfo(cls=ServiceA, factory=None, description="Other")

        gate.register(original)
        gate.unregister(other)

        assert gate.get_components() == [original]

    # ------------------------------------------------------------------
    # Заморозка
    # ------------------------------------------------------------------
    def test_freeze_disables_register(self):
        """После freeze() регистрация запрещена."""
        gate = DependencyGate()
        gate.freeze()

        info = DependencyInfo(cls=ServiceA, factory=None, description="")
        with pytest.raises(RuntimeError, match="заморожен"):
            gate.register(info)

    def test_freeze_disables_unregister(self):
        """После freeze() удаление запрещено."""
        gate = DependencyGate()
        info = DependencyInfo(cls=ServiceA, factory=None, description="")
        gate.register(info)
        gate.freeze()

        with pytest.raises(RuntimeError, match="заморожен"):
            gate.unregister(info)

    def test_freeze_idempotent(self):
        """Повторный вызов freeze() не вызывает ошибок."""
        gate = DependencyGate()
        gate.freeze()
        gate.freeze()  # не падает

    # ------------------------------------------------------------------
    # Методы после заморозки
    # ------------------------------------------------------------------
    def test_get_methods_work_after_freeze(self):
        """Методы получения работают после заморозки (только чтение)."""
        gate = DependencyGate()
        info = DependencyInfo(cls=ServiceA, factory=None, description="Test")
        gate.register(info)
        gate.freeze()

        assert gate.get_by_class(ServiceA) is info
        assert gate.get_all_classes() == [ServiceA]
        assert gate.get_components() == [info]


# ======================================================================
# Тесты для DependencyGateHost
# ======================================================================

class TestDependencyGateHost:
    """
    Тесты для DependencyGateHost — миксина, разрешающего @depends.
    В новой архитектуре шлюз больше не собирается внутри класса (этим занят MetadataBuilder),
    поэтому мы тестируем только корректное извлечение типа-ограничителя (bound).
    """

    def test_default_bound_is_object(self):
        """Если дженерик не указан явно, bound равен object."""
        class MyAction(DependencyGateHost):
            pass

        assert MyAction.get_depends_bound() is object

    def test_explicit_object_bound(self):
        """Явное указание object в дженерике."""
        class MyAction(DependencyGateHost[object]):
            pass

        assert MyAction.get_depends_bound() is object

    def test_custom_bound(self):
        """Указание кастомного базового класса (например, BaseResourceManager)."""
        class MyResourceAction(DependencyGateHost[BaseResourceManager]):
            pass

        assert MyResourceAction.get_depends_bound() is BaseResourceManager

    def test_inherited_bound(self):
        """Дочерний класс наследует bound от родителя."""
        class Parent(DependencyGateHost[BaseResourceManager]):
            pass

        class Child(Parent):
            pass

        assert Child.get_depends_bound() is BaseResourceManager

    def test_inherited_bound_multiple_levels(self):
        """Наследование bound через несколько уровней."""
        class Base(DependencyGateHost[BaseResourceManager]):
            pass

        class Intermediate(Base):
            pass

        class Final(Intermediate):
            pass

        assert Final.get_depends_bound() is BaseResourceManager
