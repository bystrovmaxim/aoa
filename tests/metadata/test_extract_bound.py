# tests/metadata/test_extract_bound.py
"""
Тесты для функции _extract_bound в DependencyGateHost.

Проверяется корректность извлечения bound-типа из дженерик-параметра
DependencyGateHost[T] при различных сценариях наследования:

- Класс с явным bound (конкретный тип).
- Класс без явного bound (ожидается object).
- Наследование в три уровня — bound сохраняется.
- Множественное наследование с другими миксинами.
- TypeVar вместо конкретного типа — ожидается object.
- Переопределение bound в дочернем классе.
- Diamond-наследование.
"""

from typing import TypeVar

from action_machine.dependencies.dependency_gate_host import DependencyGateHost
from action_machine.resource_managers.base_resource_manager import BaseResourceManager

# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные классы
# ═════════════════════════════════════════════════════════════════════════════


class SomeMixin:
    """Произвольный миксин для тестов множественного наследования."""
    pass


class AnotherMixin:
    """Ещё один миксин."""
    pass


class FakeResourceManager(BaseResourceManager):
    """Заглушка менеджера ресурсов."""
    def get_wrapper_class(self):
        return None


class CustomBase:
    """Кастомный базовый класс для тестов bound."""
    pass


T = TypeVar("T")


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Явный bound
# ═════════════════════════════════════════════════════════════════════════════


class TestExplicitBound:
    """Тесты для классов с явно указанным bound."""

    def test_object_bound(self):
        """DependencyGateHost[object] → bound = object."""
        class Host(DependencyGateHost[object]):
            pass

        assert Host.get_depends_bound() is object

    def test_base_resource_manager_bound(self):
        """DependencyGateHost[BaseResourceManager] → bound = BaseResourceManager."""
        class Host(DependencyGateHost[BaseResourceManager]):
            pass

        assert Host.get_depends_bound() is BaseResourceManager

    def test_custom_class_bound(self):
        """DependencyGateHost[CustomBase] → bound = CustomBase."""
        class Host(DependencyGateHost[CustomBase]):
            pass

        assert Host.get_depends_bound() is CustomBase


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Без явного bound
# ═════════════════════════════════════════════════════════════════════════════


class TestNoBound:
    """Тесты для классов без явного bound."""

    def test_no_generic_parameter(self):
        """DependencyGateHost без параметра → bound = object."""
        class Host(DependencyGateHost):
            pass

        assert Host.get_depends_bound() is object


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Наследование в несколько уровней
# ═════════════════════════════════════════════════════════════════════════════


class TestMultiLevelInheritance:
    """Тесты наследования bound через несколько уровней."""

    def test_two_levels(self):
        """Дочерний класс наследует bound от родителя."""
        class Parent(DependencyGateHost[BaseResourceManager]):
            pass

        class Child(Parent):
            pass

        assert Child.get_depends_bound() is BaseResourceManager

    def test_three_levels(self):
        """Внук наследует bound от деда через промежуточный класс."""
        class Grandparent(DependencyGateHost[BaseResourceManager]):
            pass

        class Parent(Grandparent):
            pass

        class Child(Parent):
            pass

        assert Child.get_depends_bound() is BaseResourceManager

    def test_four_levels(self):
        """Четыре уровня наследования — bound сохраняется."""
        class Level1(DependencyGateHost[CustomBase]):
            pass

        class Level2(Level1):
            pass

        class Level3(Level2):
            pass

        class Level4(Level3):
            pass

        assert Level4.get_depends_bound() is CustomBase

    def test_intermediate_without_generic(self):
        """
        Промежуточный класс без generic-параметра наследует bound
        от родителя, который указал параметр.
        """
        class Base(DependencyGateHost[BaseResourceManager]):
            pass

        class Middle(Base):
            """Не указывает DependencyGateHost[...]"""
            pass

        class Leaf(Middle):
            pass

        assert Middle.get_depends_bound() is BaseResourceManager
        assert Leaf.get_depends_bound() is BaseResourceManager


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Множественное наследование
# ═════════════════════════════════════════════════════════════════════════════


class TestMultipleInheritance:
    """Тесты множественного наследования с другими миксинами."""

    def test_with_one_mixin(self):
        """DependencyGateHost[T] + SomeMixin → bound сохраняется."""
        class Host(DependencyGateHost[BaseResourceManager], SomeMixin):
            pass

        assert Host.get_depends_bound() is BaseResourceManager

    def test_with_multiple_mixins(self):
        """DependencyGateHost[T] + несколько миксинов → bound сохраняется."""
        class Host(DependencyGateHost[CustomBase], SomeMixin, AnotherMixin):
            pass

        assert Host.get_depends_bound() is CustomBase

    def test_mixin_first_in_bases(self):
        """Миксин первый в списке базовых классов — bound всё равно корректен."""
        class Host(SomeMixin, DependencyGateHost[BaseResourceManager]):
            pass

        assert Host.get_depends_bound() is BaseResourceManager

    def test_child_of_multiple_inheritance(self):
        """Дочерний класс наследует bound через множественное наследование."""
        class Parent(DependencyGateHost[BaseResourceManager], SomeMixin):
            pass

        class Child(Parent, AnotherMixin):
            pass

        assert Child.get_depends_bound() is BaseResourceManager


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: TypeVar вместо конкретного типа
# ═════════════════════════════════════════════════════════════════════════════


class TestTypeVarBound:
    """Тесты для случая, когда generic-параметр — TypeVar, а не конкретный тип."""

    def test_typevar_parameter_falls_back_to_object(self):
        """
        DependencyGateHost[T] где T — TypeVar → bound = object.
        TypeVar не является конкретным типом (isinstance(T, type) == False),
        поэтому _extract_bound не может его использовать и возвращает object.
        """
        class Host(DependencyGateHost[T]):
            pass

        assert Host.get_depends_bound() is object


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Переопределение bound в дочернем классе
# ═════════════════════════════════════════════════════════════════════════════


class TestBoundOverride:
    """Тесты переопределения bound в дочернем классе."""

    def test_child_narrows_bound(self):
        """
        Дочерний класс может сузить bound: object → BaseResourceManager.
        Указав DependencyGateHost[BaseResourceManager] в своих базовых классах,
        дочерний класс переопределяет bound.
        """
        class Parent(DependencyGateHost[object]):
            pass

        class Child(Parent, DependencyGateHost[BaseResourceManager]):
            pass

        assert Child.get_depends_bound() is BaseResourceManager

    def test_parent_bound_unchanged_after_child_override(self):
        """Переопределение bound в дочернем классе не влияет на родителя."""
        class Parent(DependencyGateHost[object]):
            pass

        class Child(Parent, DependencyGateHost[BaseResourceManager]):
            pass

        assert Parent.get_depends_bound() is object
        assert Child.get_depends_bound() is BaseResourceManager


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Diamond-наследование
# ═════════════════════════════════════════════════════════════════════════════


class TestDiamondInheritance:
    """Тесты diamond-наследования с DependencyGateHost."""

    def test_diamond_same_bound(self):
        """
        Diamond: оба родителя наследуют от одного DependencyGateHost[T].
        Bound одинаковый — конфликта нет.
        """
        class Base(DependencyGateHost[BaseResourceManager]):
            pass

        class Left(Base):
            pass

        class Right(Base):
            pass

        class Diamond(Left, Right):
            pass

        assert Diamond.get_depends_bound() is BaseResourceManager

    def test_diamond_different_branches_same_bound(self):
        """
        Обе ветки diamond-а ведут к одному и тому же bound.
        """
        class Base(DependencyGateHost[CustomBase]):
            pass

        class BranchA(Base):
            pass

        class BranchB(Base):
            pass

        class Merged(BranchA, BranchB):
            pass

        assert Merged.get_depends_bound() is CustomBase
