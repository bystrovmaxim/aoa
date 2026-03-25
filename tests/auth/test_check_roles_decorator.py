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

Тесты теперь проверяют не прямой атрибут _role_spec, а шлюз ролей,
доступный через get_role_gate() после создания класса.
"""


from action_machine.Auth.check_roles import CheckRoles

# Добавляем импорты BaseAction и заглушек для параметров
from action_machine.Core.BaseAction import BaseAction
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseResult import BaseResult


# ======================================================================
# Вспомогательные классы
# ======================================================================
class MockParams(BaseParams):
    pass


class MockResult(BaseResult):
    pass


class SampleActionBase(BaseAction[MockParams, MockResult]):
    """Базовый класс для тестовых действий, наследует BaseAction, чтобы получить шлюзы."""
    pass


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

        gate = SampleAction.get_role_gate()
        spec = gate.get_role_spec()
        assert spec == CheckRoles.NONE

    def test_check_roles_any(self):
        """Декоратор с ANY (любой аутентифицированный пользователь)."""

        @CheckRoles(CheckRoles.ANY, desc="Действие для любого аутентифицированного")
        class SampleAction(SampleActionBase):
            pass

        gate = SampleAction.get_role_gate()
        assert gate.get_role_spec() == CheckRoles.ANY

    # ------------------------------------------------------------------
    # ТЕСТЫ: Конкретные роли
    # ------------------------------------------------------------------

    def test_check_roles_single_string(self):
        """Декоратор с одной ролью как строкой."""

        @CheckRoles("admin", desc="Только для админов")
        class SampleAction(SampleActionBase):
            pass

        gate = SampleAction.get_role_gate()
        assert gate.get_role_spec() == "admin"

    def test_check_roles_list(self):
        """Декоратор со списком ролей."""

        @CheckRoles(["admin", "manager"], desc="Для админов и менеджеров")
        class SampleAction(SampleActionBase):
            pass

        gate = SampleAction.get_role_gate()
        assert gate.get_role_spec() == ["admin", "manager"]

    def test_check_roles_list_with_single_item(self):
        """Список с одним элементом работает как список, а не строка."""

        @CheckRoles(["admin"], desc="Только админ")
        class SampleAction(SampleActionBase):
            pass

        gate = SampleAction.get_role_gate()
        assert gate.get_role_spec() == ["admin"]
        assert isinstance(gate.get_role_spec(), list)

    # ------------------------------------------------------------------
    # ТЕСТЫ: Сохранение класса
    # ------------------------------------------------------------------

    def test_check_roles_preserves_class(self):
        """Декоратор возвращает тот же класс (не создаёт новый)."""

        @CheckRoles(CheckRoles.NONE, desc="Тест")
        class OriginalClass(SampleActionBase):
            pass

        # Проверяем, что класс не изменился (можно добавить любой атрибут для проверки)
        assert OriginalClass.__name__ == "OriginalClass"

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

        gate = SampleAction.get_role_gate()
        # Ближайший к классу - manager (верхний, после обработки)
        # Порядок: сначала применяется @CheckRoles("admin"), затем @CheckRoles("manager")
        # поэтому последний (manager) перезаписывает спецификацию.
        assert gate.get_role_spec() == "manager"

    # ------------------------------------------------------------------
    # ТЕСТЫ: Описание
    # ------------------------------------------------------------------

    def test_check_roles_without_description(self):
        """Описание может быть None."""

        @CheckRoles("admin", desc=None)
        class SampleAction(SampleActionBase):
            pass

        gate = SampleAction.get_role_gate()
        # Не должно быть ошибки, description должен быть None
        assert gate.get_description() is None
        assert gate.get_role_spec() == "admin"