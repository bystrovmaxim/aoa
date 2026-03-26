# tests/decorators/test_check_roles_checks.py
"""
Тесты проверок декоратора @CheckRoles.

Покрывают все инварианты, объявленные в check_roles.py:
    - Применение к классу с миксином — успех (строка, список, NONE, ANY).
    - Применение к функции — TypeError.
    - Применение к классу без миксина — TypeError.
    - Некорректный тип spec (число, None, dict) — TypeError.
    - Пустой список ролей — ValueError.
    - Нестроковые элементы в списке — ValueError.
    - Некорректный desc — TypeError.
    - Проверка сохранённых данных в _role_info.
"""

import pytest

from action_machine.auth.check_roles import CheckRoles
from action_machine.auth.role_gate_host import RoleGateHost

# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательные классы
# ─────────────────────────────────────────────────────────────────────────────

class HostBase(RoleGateHost):
    """Минимальный класс с миксином RoleGateHost для тестов."""
    pass


# ─────────────────────────────────────────────────────────────────────────────
# Успешные сценарии
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckRolesSuccess:
    """Проверка корректного применения @CheckRoles."""

    def test_single_role_string(self):
        """Одна роль строкой — сохраняется в _role_info."""

        @CheckRoles("admin", desc="Только администраторы")
        class MyAction(HostBase):
            pass

        assert hasattr(MyAction, '_role_info')
        assert MyAction._role_info["spec"] == "admin"
        assert MyAction._role_info["desc"] == "Только администраторы"

    def test_list_of_roles(self):
        """Список ролей — сохраняется как список."""

        @CheckRoles(["user", "manager"], desc="Пользователи и менеджеры")
        class MyAction(HostBase):
            pass

        assert MyAction._role_info["spec"] == ["user", "manager"]

    def test_single_element_list(self):
        """Список из одного элемента — допустим."""

        @CheckRoles(["admin"])
        class MyAction(HostBase):
            pass

        assert MyAction._role_info["spec"] == ["admin"]

    def test_none_marker(self):
        """CheckRoles.NONE — аутентификация не требуется."""

        @CheckRoles(CheckRoles.NONE, desc="Без аутентификации")
        class MyAction(HostBase):
            pass

        assert MyAction._role_info["spec"] == CheckRoles.NONE

    def test_any_marker(self):
        """CheckRoles.ANY — любая роль подходит."""

        @CheckRoles(CheckRoles.ANY, desc="Любая роль")
        class MyAction(HostBase):
            pass

        assert MyAction._role_info["spec"] == CheckRoles.ANY

    def test_default_desc(self):
        """desc по умолчанию — пустая строка."""

        @CheckRoles("user")
        class MyAction(HostBase):
            pass

        assert MyAction._role_info["desc"] == ""

    def test_class_returned_unchanged(self):
        """Декоратор возвращает тот же класс."""

        @CheckRoles("user")
        class MyAction(HostBase):
            pass

        assert isinstance(MyAction, type)
        assert issubclass(MyAction, HostBase)


# ─────────────────────────────────────────────────────────────────────────────
# Ошибки: неправильная цель декоратора
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckRolesTargetErrors:
    """Проверка ошибок при неправильном применении @CheckRoles."""

    def test_applied_to_function_raises(self):
        """@CheckRoles на функции — TypeError."""
        with pytest.raises(TypeError, match="только к классу"):
            @CheckRoles("admin")
            def some_function():
                pass

    def test_applied_to_class_without_mixin_raises(self):
        """@CheckRoles на классе без RoleGateHost — TypeError."""
        with pytest.raises(TypeError, match="не наследует RoleGateHost"):
            @CheckRoles("admin")
            class PlainClass:
                pass

    def test_applied_to_lambda_raises(self):
        """@CheckRoles на лямбде — TypeError."""
        with pytest.raises(TypeError, match="только к классу"):
            CheckRoles("admin")(lambda: None)

    def test_applied_to_instance_raises(self):
        """@CheckRoles на экземпляре — TypeError."""
        obj = HostBase()
        with pytest.raises(TypeError, match="только к классу"):
            CheckRoles("admin")(obj)


# ─────────────────────────────────────────────────────────────────────────────
# Ошибки: неправильный spec
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckRolesSpecErrors:
    """Проверка ошибок при передаче некорректного spec."""

    def test_number_spec_raises(self):
        """Число вместо spec — TypeError."""
        with pytest.raises(TypeError, match="ожидает строку или список строк"):
            CheckRoles(42)

    def test_none_spec_raises(self):
        """None вместо spec — TypeError."""
        with pytest.raises(TypeError, match="ожидает строку или список строк"):
            CheckRoles(None)

    def test_dict_spec_raises(self):
        """dict вместо spec — TypeError."""
        with pytest.raises(TypeError, match="ожидает строку или список строк"):
            CheckRoles({"role": "admin"})

    def test_empty_list_raises(self):
        """Пустой список — ValueError."""
        with pytest.raises(ValueError, match="пустой список ролей"):
            CheckRoles([])

    def test_non_string_items_in_list_raises(self):
        """Нестроковый элемент в списке — ValueError."""
        with pytest.raises(ValueError, match="элемент списка ролей"):
            CheckRoles(["admin", 123])

    def test_none_item_in_list_raises(self):
        """None в списке ролей — ValueError."""
        with pytest.raises(ValueError, match="элемент списка ролей"):
            CheckRoles(["admin", None])


# ─────────────────────────────────────────────────────────────────────────────
# Ошибки: неправильный desc
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckRolesDescErrors:
    """Проверка ошибок при передаче некорректного desc."""

    def test_number_desc_raises(self):
        """Числовой desc — TypeError."""
        with pytest.raises(TypeError, match="desc должен быть строкой"):
            CheckRoles("admin", desc=123)

    def test_none_desc_raises(self):
        """None вместо desc — TypeError."""
        with pytest.raises(TypeError, match="desc должен быть строкой"):
            CheckRoles("admin", desc=None)

    def test_list_desc_raises(self):
        """Список вместо desc — TypeError."""
        with pytest.raises(TypeError, match="desc должен быть строкой"):
            CheckRoles("admin", desc=["описание"])
