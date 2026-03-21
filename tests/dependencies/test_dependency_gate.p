# tests/dependencies/test_dependency_gate.py
"""
Тесты для DependencyGate — шлюза управления зависимостями действий.

Проверяем:
- Регистрацию зависимостей (DependencyInfo)
- Получение по классу (get_by_class)
- Получение всех классов (get_all_classes)
- Получение всех компонентов (get_components)
- Удаление зависимостей (unregister)
- Заморозку шлюза (freeze)
- Обработку ошибок (повторная регистрация, регистрация после заморозки)
"""

import pytest

from action_machine.dependencies.dependency_gate import DependencyGate, DependencyInfo


# ----------------------------------------------------------------------
# Тестовые классы
# ----------------------------------------------------------------------
class ServiceA:
    pass


class ServiceB:
    pass


def factory_a():
    return ServiceA()


# ======================================================================
# Тесты
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
        assert gate.get_by_class(ServiceA) is info
        assert gate.get_components() == [info]
        assert gate.get_all_classes() == [ServiceA]

    def test_register_duplicate_raises(self):
        """Повторная регистрация зависимости для того же класса вызывает ValueError."""
        gate = DependencyGate()
        info1 = DependencyInfo(cls=ServiceA, factory=None, description="First")
        info2 = DependencyInfo(cls=ServiceA, factory=None, description="Second")

        gate.register(info1)
        with pytest.raises(ValueError, match="already registered"):
            gate.register(info2)

    def test_register_with_factory(self):
        """Регистрация зависимости с фабрикой."""
        gate = DependencyGate()
        info = DependencyInfo(cls=ServiceA, factory=factory_a, description="With factory")

        gate.register(info)
        assert gate.get_by_class(ServiceA).factory is factory_a

    # ------------------------------------------------------------------
    # Получение
    # ------------------------------------------------------------------
    def test_get_by_class_returns_none_if_not_found(self):
        """get_by_class для неизвестного класса возвращает None."""
        gate = DependencyGate()
        assert gate.get_by_class(ServiceA) is None

    def test_get_all_classes_returns_copy(self):
        """get_all_classes возвращает копию списка, внешние изменения не влияют на шлюз."""
        gate = DependencyGate()
        info = DependencyInfo(cls=ServiceA, factory=None, description="")
        gate.register(info)

        classes = gate.get_all_classes()
        classes.append(ServiceB)

        assert gate.get_all_classes() == [ServiceA]

    def test_get_components_returns_copy(self):
        """get_components возвращает копию списка, внешние изменения не влияют на шлюз."""
        gate = DependencyGate()
        info = DependencyInfo(cls=ServiceA, factory=None, description="")
        gate.register(info)

        components = gate.get_components()
        components.append(DependencyInfo(cls=ServiceB, factory=None, description="Extra"))

        assert gate.get_components() == [info]

    # ------------------------------------------------------------------
    # Удаление
    # ------------------------------------------------------------------
    def test_unregister(self):
        """Удаление зависимости по ссылке."""
        gate = DependencyGate()
        info = DependencyInfo(cls=ServiceA, factory=None, description="")
        gate.register(info)

        gate.unregister(info)
        assert gate.get_by_class(ServiceA) is None
        assert gate.get_components() == []

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

        assert gate.get_by_class(ServiceA) is original

    # ------------------------------------------------------------------
    # Заморозка
    # ------------------------------------------------------------------
    def test_freeze_disables_register(self):
        """После freeze() регистрация новых зависимостей запрещена."""
        gate = DependencyGate()
        gate.freeze()

        info = DependencyInfo(cls=ServiceA, factory=None, description="")
        with pytest.raises(RuntimeError, match="DependencyGate is frozen"):
            gate.register(info)

    def test_freeze_disables_unregister(self):
        """После freeze() удаление зависимостей запрещено."""
        gate = DependencyGate()
        info = DependencyInfo(cls=ServiceA, factory=None, description="")
        gate.register(info)
        gate.freeze()

        with pytest.raises(RuntimeError, match="DependencyGate is frozen"):
            gate.unregister(info)

    def test_freeze_idempotent(self):
        """Повторный вызов freeze() не вызывает ошибок."""
        gate = DependencyGate()
        gate.freeze()
        gate.freeze()  # не падает

    # ------------------------------------------------------------------
    # Методы get_by_class и get_all_classes после заморозки
    # ------------------------------------------------------------------
    def test_get_methods_work_after_freeze(self):
        """Методы получения работают после заморозки (только чтение)."""
        gate = DependencyGate()
        info = DependencyInfo(cls=ServiceA, factory=None, description="")
        gate.register(info)
        gate.freeze()

        assert gate.get_by_class(ServiceA) is info
        assert gate.get_all_classes() == [ServiceA]
        assert gate.get_components() == [info]


# ======================================================================
# Тесты для DependencyGateHost (миксин, который собирает зависимости)
# ======================================================================

class TestDependencyGateHost:
    """
    Тесты для DependencyGateHost — миксина, который присоединяет DependencyGate к классу действия.
    Проверяем:
    - Сбор зависимостей из __depends_info
    - Заморозку шлюза после сборки
    - Отсутствие мутации родительских данных при наследовании
    """

    def test_dependencies_are_collected(self):
        """Зависимости из __depends_info регистрируются в шлюзе."""

        from action_machine.dependencies.dependency_gate_host import DependencyGateHost

        class MyAction(DependencyGateHost):
            __depends_info = [
                DependencyInfo(cls=ServiceA, factory=None, description="A"),
                DependencyInfo(cls=ServiceB, factory=factory_a, description="B"),
            ]

        # Шлюз должен содержать обе зависимости
        gate = MyAction.get_dependency_gate()
        assert gate.get_by_class(ServiceA) is MyAction.__depends_info[0]
        assert gate.get_by_class(ServiceB) is MyAction.__depends_info[1]

    def test_gate_is_frozen_after_collection(self):
        """После сбора шлюз замораживается, регистрация новых зависимостей невозможна."""

        from action_machine.dependencies.dependency_gate_host import DependencyGateHost

        class MyAction(DependencyGateHost):
            __depends_info = [DependencyInfo(cls=ServiceA, factory=None, description="A")]

        gate = MyAction.get_dependency_gate()
        with pytest.raises(RuntimeError, match="DependencyGate is frozen"):
            gate.register(DependencyInfo(cls=ServiceB, factory=None, description="B"))

    def test_inheritance_does_not_share_gate(self):
        """
        При наследовании каждый класс получает свой собственный шлюз,
        а не разделяет с родителем.
        """

        from action_machine.dependencies.dependency_gate_host import DependencyGateHost

        class Parent(DependencyGateHost):
            __depends_info = [DependencyInfo(cls=ServiceA, factory=None, description="Parent")]

        class Child(Parent):
            __depends_info = [DependencyInfo(cls=ServiceB, factory=None, description="Child")]

        parent_gate = Parent.get_dependency_gate()
        child_gate = Child.get_dependency_gate()

        # Гейты разные
        assert parent_gate is not child_gate

        # У родителя только ServiceA
        assert parent_gate.get_by_class(ServiceA) is not None
        assert parent_gate.get_by_class(ServiceB) is None

        # У ребёнка только ServiceB
        assert child_gate.get_by_class(ServiceA) is None
        assert child_gate.get_by_class(ServiceB) is not None