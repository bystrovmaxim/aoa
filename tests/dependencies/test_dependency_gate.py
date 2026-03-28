# tests/dependencies/test_dependency_gate.py
"""
Тесты для DependencyGateHost — маркерного generic-миксина,
разрешающего применение декоратора @depends.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

DependencyGateHost[T] выполняет две функции:

1. МАРКЕР: декоратор @depends при применении проверяет
   issubclass(cls, DependencyGateHost). Без наследования — TypeError.

2. ОГРАНИЧИТЕЛЬ ТИПА (bound): параметр T определяет, какие классы
   допускаются в качестве зависимостей:
   - DependencyGateHost[object]              → любой класс
   - DependencyGateHost[BaseResourceManager] → только ресурс-менеджеры

Bound извлекается из generic-параметра в __init_subclass__ и сохраняется
в cls._depends_bound. Метод get_depends_bound() возвращает его.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕЧАНИЕ
═══════════════════════════════════════════════════════════════════════════════

DependencyGate и BaseGate удалены. Фабрика зависимостей (DependencyFactory)
работает напрямую с tuple[DependencyInfo, ...] из ClassMetadata.dependencies.
Промежуточный реестр не нужен — фабрика иммутабельна после создания.
"""

from action_machine.dependencies.dependency_gate_host import DependencyGateHost
from action_machine.resource_managers.base_resource_manager import BaseResourceManager


class TestDependencyGateHostDefaultBound:
    """Тесты извлечения bound-типа по умолчанию."""

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


class TestDependencyGateHostCustomBound:
    """Тесты извлечения кастомного bound-типа."""

    def test_custom_bound(self):
        """Указание BaseResourceManager ограничивает допустимые зависимости."""
        class MyResourceAction(DependencyGateHost[BaseResourceManager]):
            pass
        assert MyResourceAction.get_depends_bound() is BaseResourceManager


class TestDependencyGateHostInheritance:
    """Тесты наследования bound-типа через несколько уровней."""

    def test_child_inherits_object_bound(self):
        """Дочерний класс наследует bound=object от родителя."""
        class Parent(DependencyGateHost[object]):
            pass
        class Child(Parent):
            pass
        assert Child.get_depends_bound() is object

    def test_child_inherits_resource_bound(self):
        """Дочерний класс наследует bound=BaseResourceManager."""
        class Parent(DependencyGateHost[BaseResourceManager]):
            pass
        class Child(Parent):
            pass
        assert Child.get_depends_bound() is BaseResourceManager

    def test_inherited_bound_multiple_levels(self):
        """Наследование bound через три уровня."""
        class Base(DependencyGateHost[BaseResourceManager]):
            pass
        class Intermediate(Base):
            pass
        class Final(Intermediate):
            pass
        assert Final.get_depends_bound() is BaseResourceManager
