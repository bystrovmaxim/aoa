# tests2/auth/test_check_roles_decorator.py
"""
Тесты декоратора @check_roles — объявление ролевых ограничений на классе.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Декоратор @check_roles — часть грамматики намерений ActionMachine. Он
записывает спецификацию ролей в атрибут cls._role_info, который затем
читается MetadataBuilder при сборке ClassMetadata.role (RoleMeta).

Декоратор при применении проверяет:
1. spec — строка или список строк (не число, не None, не пустой список).
2. Целевой объект — класс (type), не функция и не экземпляр.
3. Класс наследует RoleGateHost — миксин, разрешающий @check_roles.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Валидные спецификации:
    - ROLE_NONE — строка "__NONE__", доступ без аутентификации.
    - ROLE_ANY — строка "__ANY__", любая роль.
    - Конкретная роль — строка "admin".
    - Список ролей — ["admin", "manager"].

Запись _role_info:
    - Декоратор записывает {"spec": ...} в cls._role_info.
    - MetadataBuilder читает _role_info при сборке.

Невалидные аргументы:
    - spec не строка и не список → TypeError.
    - Пустой список → ValueError.
    - Элемент списка не строка → ValueError.

Невалидные цели:
    - Применён к функции, не к классу → TypeError.
    - Класс не наследует RoleGateHost → TypeError.
"""

import pytest

from action_machine.auth import ROLE_ANY, ROLE_NONE, check_roles
from action_machine.auth.role_gate_host import RoleGateHost
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult

# ═════════════════════════════════════════════════════════════════════════════
# Валидные спецификации
# ═════════════════════════════════════════════════════════════════════════════


class TestValidSpec:
    """Декоратор принимает валидные спецификации ролей и записывает _role_info."""

    def test_role_none(self) -> None:
        """
        @check_roles(ROLE_NONE) — доступ без аутентификации.

        ROLE_NONE = "__NONE__". Декоратор записывает spec="__NONE__"
        в cls._role_info. Машина при проверке ролей пропускает действие
        без каких-либо проверок.
        """
        # Arrange & Act — декоратор с ROLE_NONE
        @check_roles(ROLE_NONE)
        class _Action(RoleGateHost):
            pass

        # Assert — _role_info записан с правильным spec
        assert hasattr(_Action, "_role_info")
        assert _Action._role_info["spec"] == ROLE_NONE
        assert _Action._role_info["spec"] == "__NONE__"

    def test_role_any(self) -> None:
        """
        @check_roles(ROLE_ANY) — требуется любая роль.

        ROLE_ANY = "__ANY__". Пользователь обязан быть аутентифицирован
        (иметь хотя бы одну роль), но конкретная роль не важна.
        """
        # Arrange & Act — декоратор с ROLE_ANY
        @check_roles(ROLE_ANY)
        class _Action(RoleGateHost):
            pass

        # Assert
        assert _Action._role_info["spec"] == ROLE_ANY
        assert _Action._role_info["spec"] == "__ANY__"

    def test_single_role(self) -> None:
        """
        @check_roles("admin") — требуется конкретная роль.

        Машина проверяет "admin" in user.roles.
        """
        # Arrange & Act
        @check_roles("admin")
        class _Action(RoleGateHost):
            pass

        # Assert
        assert _Action._role_info["spec"] == "admin"

    def test_role_list(self) -> None:
        """
        @check_roles(["admin", "manager"]) — требуется одна из списка.

        Машина проверяет any(role in user.roles for role in spec).
        """
        # Arrange & Act
        @check_roles(["admin", "manager"])
        class _Action(RoleGateHost):
            pass

        # Assert — spec сохранён как список
        assert _Action._role_info["spec"] == ["admin", "manager"]

    def test_single_element_list(self) -> None:
        """
        @check_roles(["editor"]) — список из одного элемента.

        Допустимо, хотя эквивалентно @check_roles("editor").
        """
        # Arrange & Act
        @check_roles(["editor"])
        class _Action(RoleGateHost):
            pass

        # Assert
        assert _Action._role_info["spec"] == ["editor"]

    def test_returns_class_unchanged(self) -> None:
        """
        Декоратор возвращает класс без изменений.

        @check_roles не оборачивает класс — только записывает _role_info.
        Класс остаётся тем же объектом.
        """
        # Arrange
        class _Original(RoleGateHost):
            custom_attr = 42

        # Act — применение декоратора
        _Decorated = check_roles("admin")(_Original)

        # Assert — тот же класс, атрибуты сохранены
        assert _Decorated is _Original
        assert _Decorated.custom_attr == 42


# ═════════════════════════════════════════════════════════════════════════════
# Применение к BaseAction
# ═════════════════════════════════════════════════════════════════════════════


class TestWithBaseAction:
    """Декоратор применяется к наследникам BaseAction (которые наследуют RoleGateHost)."""

    def test_base_action_inherits_role_gate_host(self) -> None:
        """
        BaseAction наследует RoleGateHost — @check_roles допустим.

        BaseAction[P, R] включает RoleGateHost в цепочку наследования,
        поэтому все действия могут использовать @check_roles.
        """
        # Arrange & Act & Assert — issubclass проверка
        assert issubclass(BaseAction, RoleGateHost)

    def test_check_roles_on_action(self) -> None:
        """
        @check_roles("manager") на наследнике BaseAction — записывает _role_info.
        """
        # Arrange & Act
        from action_machine.aspects.summary_aspect import summary_aspect
        from action_machine.core.meta_decorator import meta

        @meta(description="Тестовое действие")
        @check_roles("manager")
        class _TestAction(BaseAction[BaseParams, BaseResult]):
            @summary_aspect("test")
            async def summary(self, params, state, box, connections):
                return BaseResult()

        # Assert — _role_info записан
        assert _TestAction._role_info["spec"] == "manager"


# ═════════════════════════════════════════════════════════════════════════════
# Интеграция с MetadataBuilder
# ═════════════════════════════════════════════════════════════════════════════


class TestMetadataIntegration:
    """_role_info корректно читается MetadataBuilder → ClassMetadata.role."""

    def test_role_in_class_metadata(self) -> None:
        """
        GateCoordinator.get() собирает RoleMeta из _role_info.

        MetadataBuilder.build() вызывает collect_role(cls), который
        читает cls._role_info и создаёт RoleMeta(spec=...).
        """
        # Arrange
        from action_machine.aspects.summary_aspect import summary_aspect
        from action_machine.core.gate_coordinator import GateCoordinator
        from action_machine.core.meta_decorator import meta

        @meta(description="Действие с ролью")
        @check_roles("admin")
        class _RoledAction(BaseAction[BaseParams, BaseResult]):
            @summary_aspect("test")
            async def summary(self, params, state, box, connections):
                return BaseResult()

        coordinator = GateCoordinator()

        # Act — сборка метаданных
        metadata = coordinator.get(_RoledAction)

        # Assert — RoleMeta содержит spec="admin"
        assert metadata.has_role()
        assert metadata.role is not None
        assert metadata.role.spec == "admin"


# ═════════════════════════════════════════════════════════════════════════════
# Невалидные аргументы spec
# ═════════════════════════════════════════════════════════════════════════════


class TestInvalidSpec:
    """Невалидные аргументы spec → TypeError или ValueError."""

    def test_spec_int_raises_type_error(self) -> None:
        """
        @check_roles(42) → TypeError.

        spec должен быть строкой или списком строк, не числом.
        """
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="строку или список строк"):
            check_roles(42)

    def test_spec_none_raises_type_error(self) -> None:
        """
        @check_roles(None) → TypeError.
        """
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="строку или список строк"):
            check_roles(None)

    def test_spec_empty_list_raises_value_error(self) -> None:
        """
        @check_roles([]) → ValueError.

        Пустой список ролей — вероятная ошибка. Используйте ROLE_NONE
        для действий без аутентификации.
        """
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="пустой список"):
            check_roles([])

    def test_spec_list_with_non_string_raises_value_error(self) -> None:
        """
        @check_roles(["admin", 42]) → ValueError.

        Все элементы списка должны быть строками.
        """
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="должен быть строкой"):
            check_roles(["admin", 42])

    def test_spec_dict_raises_type_error(self) -> None:
        """
        @check_roles({"role": "admin"}) → TypeError.

        Словарь не является допустимым типом для spec.
        """
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="строку или список строк"):
            check_roles({"role": "admin"})


# ═════════════════════════════════════════════════════════════════════════════
# Невалидные цели декоратора
# ═════════════════════════════════════════════════════════════════════════════


class TestInvalidTarget:
    """Декоратор применён к невалидной цели → TypeError."""

    def test_applied_to_function_raises_type_error(self) -> None:
        """
        @check_roles("admin") на функции → TypeError.

        Декоратор уровня класса — не может применяться к функциям.
        """
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="только к классу"):
            @check_roles("admin")
            def _func():
                pass

    def test_applied_to_class_without_role_gate_host_raises(self) -> None:
        """
        @check_roles("admin") на классе без RoleGateHost → TypeError.

        Класс должен наследовать RoleGateHost для использования
        @check_roles. Это защита от случайного применения.
        """
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="не наследует RoleGateHost"):
            @check_roles("admin")
            class _Plain:
                pass

    def test_applied_to_instance_raises_type_error(self) -> None:
        """
        check_roles("admin")(instance) → TypeError.

        Декоратор ожидает класс (type), не экземпляр.
        """
        # Arrange
        class _MyClass(RoleGateHost):
            pass

        instance = _MyClass()

        # Act & Assert
        with pytest.raises(TypeError, match="только к классу"):
            check_roles("admin")(instance)
