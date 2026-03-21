# tests/auth/test_role_gate.py
"""
Тесты для RoleGate — шлюза управления ролевой спецификацией действия.

Проверяем:
- Регистрацию ролевой спецификации (RoleInfo)
- Повторную регистрацию (должна вызывать ValueError)
- Получение спецификации (get_role_spec), описания (get_description), наличие роли (has_role)
- Удаление спецификации (unregister)
- Заморозку шлюза (freeze)
- Обработку ошибок (регистрация/удаление после заморозки)
- Сбор спецификации через RoleGateHost (миксин)
"""

import pytest

from action_machine.Auth.role_gate import RoleGate, RoleInfo

# ======================================================================
# Тесты для RoleGate
# ======================================================================

class TestRoleGate:
    """Тесты для RoleGate."""

    # ------------------------------------------------------------------
    # Регистрация
    # ------------------------------------------------------------------
    def test_register_single_role_spec(self):
        """Регистрация одной ролевой спецификации."""
        gate = RoleGate()
        info = RoleInfo(spec="admin", description="Administrator role")

        result = gate.register(info)

        assert result is info
        assert gate.get_role_spec() == "admin"
        assert gate.get_description() == "Administrator role"
        assert gate.has_role() is True
        assert gate.get_components() == [info]

    def test_register_list_role_spec(self):
        """Регистрация спецификации в виде списка."""
        gate = RoleGate()
        info = RoleInfo(spec=["admin", "manager"], description="Admin or manager")

        gate.register(info)
        assert gate.get_role_spec() == ["admin", "manager"]
        # Список возвращается копией, чтобы предотвратить внешние модификации
        spec = gate.get_role_spec()
        spec.append("user")
        assert gate.get_role_spec() == ["admin", "manager"]

    def test_register_duplicate_raises(self):
        """Повторная регистрация спецификации вызывает ValueError."""
        gate = RoleGate()
        info1 = RoleInfo(spec="admin", description="First")
        info2 = RoleInfo(spec="admin", description="Second")

        gate.register(info1)
        with pytest.raises(ValueError, match="already has a registered role specification"):
            gate.register(info2)

    # ------------------------------------------------------------------
    # Получение
    # ------------------------------------------------------------------
    def test_get_role_spec_returns_none_if_not_registered(self):
        """get_role_spec для незарегистрированного шлюза возвращает None."""
        gate = RoleGate()
        assert gate.get_role_spec() is None
        assert gate.get_description() is None
        assert gate.has_role() is False

    def test_get_components_returns_copy(self):
        """get_components возвращает копию, внешние изменения не влияют на шлюз."""
        gate = RoleGate()
        info = RoleInfo(spec="admin", description="")
        gate.register(info)

        components = gate.get_components()
        components.append(RoleInfo(spec="manager", description=""))

        assert gate.get_components() == [info]

    # ------------------------------------------------------------------
    # Удаление
    # ------------------------------------------------------------------
    def test_unregister(self):
        """Удаление спецификации по ссылке."""
        gate = RoleGate()
        info = RoleInfo(spec="admin", description="")
        gate.register(info)

        gate.unregister(info)
        assert gate.get_role_spec() is None
        assert gate.get_description() is None
        assert gate.has_role() is False
        assert gate.get_components() == []

    def test_unregister_nonexistent_ignored(self):
        """Удаление незарегистрированной спецификации не вызывает ошибку."""
        gate = RoleGate()
        info = RoleInfo(spec="admin", description="")
        gate.unregister(info)  # не падает

    def test_unregister_wrong_instance_does_nothing(self):
        """
        Если передан другой объект RoleInfo с той же спецификацией,
        удаление не происходит (требуется точное совпадение по ссылке).
        """
        gate = RoleGate()
        original = RoleInfo(spec="admin", description="Original")
        other = RoleInfo(spec="admin", description="Other")

        gate.register(original)
        gate.unregister(other)

        assert gate.get_role_spec() == "admin"
        assert gate.get_description() == "Original"

    # ------------------------------------------------------------------
    # Заморозка
    # ------------------------------------------------------------------
    def test_freeze_disables_register(self):
        """После freeze() регистрация запрещена."""
        gate = RoleGate()
        gate.freeze()

        info = RoleInfo(spec="admin", description="")
        with pytest.raises(RuntimeError, match="RoleGate is frozen"):
            gate.register(info)

    def test_freeze_disables_unregister(self):
        """После freeze() удаление запрещено."""
        gate = RoleGate()
        info = RoleInfo(spec="admin", description="")
        gate.register(info)
        gate.freeze()

        with pytest.raises(RuntimeError, match="RoleGate is frozen"):
            gate.unregister(info)

    def test_freeze_idempotent(self):
        """Повторный вызов freeze() не вызывает ошибок."""
        gate = RoleGate()
        gate.freeze()
        gate.freeze()  # не падает

    # ------------------------------------------------------------------
    # Методы после заморозки
    # ------------------------------------------------------------------
    def test_get_methods_work_after_freeze(self):
        """Методы получения работают после заморозки (только чтение)."""
        gate = RoleGate()
        info = RoleInfo(spec="admin", description="Test")
        gate.register(info)
        gate.freeze()

        assert gate.get_role_spec() == "admin"
        assert gate.get_description() == "Test"
        assert gate.has_role() is True
        assert gate.get_components() == [info]


# ======================================================================
# Тесты для RoleGateHost (миксин, который собирает ролевую спецификацию)
# ======================================================================

class TestRoleGateHost:
    """
    Тесты для RoleGateHost — миксина, который присоединяет RoleGate к классу действия.
    Проверяем:
    - Сбор ролевой спецификации из _role_info
    - Заморозку шлюза после сборки
    - Отсутствие мутации родительских данных при наследовании
    """

    def test_role_info_is_collected(self):
        """Ролевая спецификация из _role_info регистрируется в шлюзе."""
        from action_machine.Auth.role_gate_host import RoleGateHost

        class MyAction(RoleGateHost):
            _role_info = RoleInfo(spec="admin", description="Admin only")

        gate = MyAction.get_role_gate()
        assert gate.get_role_spec() == "admin"
        assert gate.get_description() == "Admin only"
        assert gate.has_role() is True

    def test_gate_is_frozen_after_collection(self):
        """После сбора шлюз замораживается, регистрация новой спецификации невозможна."""
        from action_machine.Auth.role_gate_host import RoleGateHost

        class MyAction(RoleGateHost):
            _role_info = RoleInfo(spec="admin", description="Admin only")

        gate = MyAction.get_role_gate()
        with pytest.raises(RuntimeError, match="RoleGate is frozen"):
            gate.register(RoleInfo(spec="manager", description=""))

    def test_inheritance_does_not_share_gate(self):
        """
        При наследовании каждый класс получает свой собственный шлюз,
        а не разделяет с родителем.
        """
        from action_machine.Auth.role_gate_host import RoleGateHost

        class Parent(RoleGateHost):
            _role_info = RoleInfo(spec="parent", description="Parent role")

        class Child(Parent):
            _role_info = RoleInfo(spec="child", description="Child role")

        parent_gate = Parent.get_role_gate()
        child_gate = Child.get_role_gate()

        # Гейты разные
        assert parent_gate is not child_gate

        # У родителя спецификация parent
        assert parent_gate.get_role_spec() == "parent"
        # У ребёнка спецификация child (родительская не наследуется)
        assert child_gate.get_role_spec() == "child"

    def test_class_without_role_info_has_empty_gate(self):
        """Если класс не имеет _role_info, шлюз остаётся пустым (но замороженным)."""
        from action_machine.Auth.role_gate_host import RoleGateHost

        class MyAction(RoleGateHost):
            pass

        gate = MyAction.get_role_gate()
        assert gate.get_role_spec() is None
        assert gate.has_role() is False
        # Шлюз заморожен, регистрация невозможна
        with pytest.raises(RuntimeError, match="RoleGate is frozen"):
            gate.register(RoleInfo(spec="admin", description=""))