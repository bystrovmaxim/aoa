# tests/core/test_action_test_machine.py
"""
Тесты проверок декоратора @depends.

Покрывают все инварианты, включая дженерик-параметр DependencyGateHost[T]:
    - Применение к классу с DependencyGateHost[object] — любой тип допустим.
    - Применение к классу с DependencyGateHost[BaseResourceManager] —
      только подклассы BaseResourceManager.
    - Передача класса, не соответствующего bound — TypeError.
    - Все остальные проверки (дубликаты, не-класс, без миксина и т.д.).
"""

import pytest

from action_machine.dependencies.dependency_gate_host import DependencyGateHost
from action_machine.dependencies.depends import depends
from action_machine.resource_managers.base_resource_manager import BaseResourceManager

# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательные классы
# ─────────────────────────────────────────────────────────────────────────────

class FakeService:
    pass

class AnotherService:
    pass

class FakeResourceManager(BaseResourceManager):
    def get_wrapper_class(self): return None

class AnotherResourceManager(BaseResourceManager):
    def get_wrapper_class(self): return None

class ObjectBoundHost(DependencyGateHost[object]):
    pass

class ResourceBoundHost(DependencyGateHost[BaseResourceManager]):
    pass


# ─────────────────────────────────────────────────────────────────────────────
# Успешные сценарии: bound=object
# ─────────────────────────────────────────────────────────────────────────────

class TestDependsObjectBoundSuccess:
    def test_any_service_allowed(self):
        @depends(FakeService, description="Тестовый сервис")
        class MyAction(ObjectBoundHost):
            pass
        assert len(MyAction._depends_info) == 1
        assert MyAction._depends_info[0].cls is FakeService

    def test_resource_manager_also_allowed(self):
        @depends(FakeResourceManager, description="Менеджер ресурсов")
        class MyAction(ObjectBoundHost):
            pass
        assert MyAction._depends_info[0].cls is FakeResourceManager

    def test_multiple_dependencies(self):
        @depends(FakeService)
        @depends(AnotherService)
        class MyAction(ObjectBoundHost):
            pass
        assert len(MyAction._depends_info) == 2

    def test_bound_is_object(self):
        assert ObjectBoundHost.get_depends_bound() is object


# ─────────────────────────────────────────────────────────────────────────────
# Успешные сценарии: bound=BaseResourceManager
# ─────────────────────────────────────────────────────────────────────────────

class TestDependsResourceBoundSuccess:
    def test_resource_manager_allowed(self):
        @depends(FakeResourceManager, description="БД")
        class MyPool(ResourceBoundHost):
            pass
        assert len(MyPool._depends_info) == 1
        assert MyPool._depends_info[0].cls is FakeResourceManager

    def test_multiple_resource_managers(self):
        @depends(FakeResourceManager)
        @depends(AnotherResourceManager)
        class MyPool(ResourceBoundHost):
            pass
        assert len(MyPool._depends_info) == 2

    def test_bound_is_base_resource_manager(self):
        assert ResourceBoundHost.get_depends_bound() is BaseResourceManager


# ─────────────────────────────────────────────────────────────────────────────
# Ошибки: нарушение bound
# ─────────────────────────────────────────────────────────────────────────────

class TestDependsBoundErrors:
    def test_plain_service_with_resource_bound_raises(self):
        with pytest.raises(TypeError, match="не является подклассом"):
            @depends(FakeService)
            class MyPool(ResourceBoundHost):
                pass


# ─────────────────────────────────────────────────────────────────────────────
# Наследование bound
# ─────────────────────────────────────────────────────────────────────────────

class TestDependsBoundInheritance:
    def test_child_inherits_object_bound(self):
        class Child(ObjectBoundHost):
            pass
        assert Child.get_depends_bound() is object

    def test_child_inherits_resource_bound(self):
        class Child(ResourceBoundHost):
            pass
        assert Child.get_depends_bound() is BaseResourceManager


# ─────────────────────────────────────────────────────────────────────────────
# Изоляция наследования зависимостей
# ─────────────────────────────────────────────────────────────────────────────

class TestDependsInheritance:
    def test_child_does_not_mutate_parent(self):
        @depends(FakeService)
        class Parent(ObjectBoundHost):
            pass

        @depends(AnotherService)
        class Child(Parent):
            pass

        assert len(Parent._depends_info) == 1
        assert Parent._depends_info[0].cls is FakeService
        assert len(Child._depends_info) == 2


# ─────────────────────────────────────────────────────────────────────────────
# Ошибки: неправильная цель и аргументы
# ─────────────────────────────────────────────────────────────────────────────

class TestDependsTargetErrors:
    def test_applied_to_function_raises(self):
        with pytest.raises(TypeError, match="только к классу"):
            @depends(FakeService)
            def some_function():
                pass

    def test_applied_to_class_without_mixin_raises(self):
        with pytest.raises(TypeError, match="не наследует DependencyGateHost"):
            @depends(FakeService)
            class PlainClass:
                pass


class TestDependsArgumentErrors:
    def test_instance_instead_of_class_raises(self):
        with pytest.raises(TypeError, match="ожидает класс"):
            depends(FakeService())


class TestDependsDuplicates:
    def test_duplicate_raises(self):
        with pytest.raises(ValueError, match="уже объявлен"):
            @depends(FakeService)
            @depends(FakeService)
            class MyAction(ObjectBoundHost):
                pass
