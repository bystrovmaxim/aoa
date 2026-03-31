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
        """Одна роль строкой — сохраняется в _role_info с ключом spec."""

        @CheckRoles("admin")
        class MyAction(HostBase):
            pass

        assert hasattr(MyAction, '_role_info')
        assert MyAction._role_info["spec"] == "admin"

    def test_role_info_has_no_desc(self):
        """_role_info не содержит ключ desc — параметр удалён из API."""

        @CheckRoles("admin")
        class MyAction(HostBase):
            pass

        assert "desc" not in MyAction._role_info

    def test_list_of_roles(self):
        """Список ролей — сохраняется как список."""

        @CheckRoles(["user", "manager"])
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

        @CheckRoles(CheckRoles.NONE)
        class MyAction(HostBase):
            pass

        assert MyAction._role_info["spec"] == CheckRoles.NONE

    def test_any_marker(self):
        """CheckRoles.ANY — любая роль подходит."""

        @CheckRoles(CheckRoles.ANY)
        class MyAction(HostBase):
            pass

        assert MyAction._role_info["spec"] == CheckRoles.ANY

    def test_returns_same_class(self):
        """Декоратор возвращает тот же класс без замены."""

        class OriginalAction(HostBase):
            pass

        result = CheckRoles("user")(OriginalAction)
        assert result is OriginalAction

    def test_spec_property(self):
        """Свойство spec возвращает спецификацию ролей."""
        decorator = CheckRoles(["a", "b"])
        assert decorator.spec == ["a", "b"]


# ─────────────────────────────────────────────────────────────────────────────
# Ошибки применения к не-классу
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckRolesTargetErrors:
    """Проверка ошибок при применении к не-классу."""

    def test_function_target_raises(self):
        """Применение к функции — TypeError."""
        with pytest.raises(TypeError, match="только к классу"):
            @CheckRoles("admin")
            def my_function():
                pass

    def test_instance_target_raises(self):
        """Применение к экземпляру — TypeError."""
        obj = HostBase()
        with pytest.raises(TypeError, match="только к классу"):
            CheckRoles("admin")(obj)

    def test_string_target_raises(self):
        """Применение к строке — TypeError."""
        with pytest.raises(TypeError, match="только к классу"):
            CheckRoles("admin")("not_a_class")


# ─────────────────────────────────────────────────────────────────────────────
# Ошибки отсутствия миксина
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckRolesMixinErrors:
    """Проверка ошибок при отсутствии RoleGateHost."""

    def test_no_mixin_raises(self):
        """Класс без RoleGateHost — TypeError."""
        with pytest.raises(TypeError, match="не наследует RoleGateHost"):
            @CheckRoles("admin")
            class BadAction:
                pass


# ─────────────────────────────────────────────────────────────────────────────
# Ошибки spec
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckRolesSpecErrors:
    """Проверка ошибок в аргументе spec."""

    def test_number_spec_raises(self):
        """Число в spec — TypeError."""
        with pytest.raises(TypeError, match="строку или список строк"):
            CheckRoles(42)

    def test_none_spec_raises(self):
        """None в spec — TypeError."""
        with pytest.raises(TypeError, match="строку или список строк"):
            CheckRoles(None)

    def test_dict_spec_raises(self):
        """Словарь в spec — TypeError."""
        with pytest.raises(TypeError, match="строку или список строк"):
            CheckRoles({"role": "admin"})

    def test_empty_list_raises(self):
        """Пустой список — ValueError."""
        with pytest.raises(ValueError, match="пустой список"):
            CheckRoles([])

    def test_non_string_in_list_raises(self):
        """Нестроковый элемент в списке — ValueError."""
        with pytest.raises(ValueError, match="должен быть строкой"):
            CheckRoles(["admin", 42])

    def test_none_in_list_raises(self):
        """None в списке — ValueError."""
        with pytest.raises(ValueError, match="должен быть строкой"):
            CheckRoles(["admin", None])
