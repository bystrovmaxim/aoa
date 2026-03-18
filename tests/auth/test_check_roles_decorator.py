# tests/auth/test_check_roles_decorator.py
"""
Тесты декоратора CheckRoles.

Проверяем:
- NONE (доступ без аутентификации)
- ANY (любой аутентифицированный)
- Одна конкретная роль
- Список ролей
- Сохранение класса
- Множественные декораторы
"""

from action_machine.Auth.check_roles import CheckRoles

from .conftest import SampleActionBase


class TestCheckRolesDecorator:
    """Тесты декоратора CheckRoles."""

    # ------------------------------------------------------------------
    # ТЕСТЫ: Специальные значения
    # ------------------------------------------------------------------

    def test_check_roles_none(self):
        """Декоратор с NONE (доступ без аутентификации)."""

        @CheckRoles(CheckRoles.NONE, desc="Действие без аутентификации")
        class SampleAction(SampleActionBase):
            pass

        assert hasattr(SampleAction, "_role_spec")
        assert SampleAction._role_spec == CheckRoles.NONE

    def test_check_roles_any(self):
        """Декоратор с ANY (любой аутентифицированный пользователь)."""

        @CheckRoles(CheckRoles.ANY, desc="Действие для любого аутентифицированного")
        class SampleAction(SampleActionBase):
            pass

        assert SampleAction._role_spec == CheckRoles.ANY

    # ------------------------------------------------------------------
    # ТЕСТЫ: Конкретные роли
    # ------------------------------------------------------------------

    def test_check_roles_single_string(self):
        """Декоратор с одной ролью как строкой."""

        @CheckRoles("admin", desc="Только для админов")
        class SampleAction(SampleActionBase):
            pass

        assert SampleAction._role_spec == "admin"

    def test_check_roles_list(self):
        """Декоратор со списком ролей."""

        @CheckRoles(["admin", "manager"], desc="Для админов и менеджеров")
        class SampleAction(SampleActionBase):
            pass

        assert SampleAction._role_spec == ["admin", "manager"]

    def test_check_roles_list_with_single_item(self):
        """Список с одним элементом работает как список, а не строка."""

        @CheckRoles(["admin"], desc="Только админ")
        class SampleAction(SampleActionBase):
            pass

        assert SampleAction._role_spec == ["admin"]
        assert isinstance(SampleAction._role_spec, list)

    # ------------------------------------------------------------------
    # ТЕСТЫ: Сохранение класса
    # ------------------------------------------------------------------

    def test_check_roles_preserves_class(self):
        """Декоратор возвращает тот же класс (не создаёт новый)."""

        @CheckRoles(CheckRoles.NONE, desc="Тест")
        class OriginalClass(SampleActionBase):
            pass

        assert OriginalClass.x == 42
        assert isinstance(OriginalClass(), OriginalClass)

    def test_check_roles_preserves_methods(self):
        """Декоратор сохраняет методы класса."""

        @CheckRoles("admin", desc="Тест")
        class SampleAction(SampleActionBase):
            def test_method(self):
                return "test"

        obj = SampleAction()
        assert obj.test_method() == "test"

    # ------------------------------------------------------------------
    # ТЕСТЫ: Множественные декораторы
    # ------------------------------------------------------------------

    def test_check_roles_order_with_multiple_decorators(self):
        """Порядок декораторов важен: верхний применяется раньше."""

        @CheckRoles("manager", desc="Менеджер")
        @CheckRoles("admin", desc="Админ")
        class SampleAction(SampleActionBase):
            pass

        # Ближайший к классу - admin (снизу вверх)
        assert SampleAction._role_spec == "manager"

    # ------------------------------------------------------------------
    # ТЕСТЫ: Описание
    # ------------------------------------------------------------------

    def test_check_roles_without_description(self):
        """Описание может быть None."""

        @CheckRoles("admin", desc=None)
        class SampleAction(SampleActionBase):
            pass

        # Не должно быть ошибки
        assert SampleAction._role_spec == "admin"