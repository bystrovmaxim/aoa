# tests/core/test_machine_roles.py
"""
Тесты проверки ролей в ActionProductMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

``RoleChecker.check()`` (used from ``ActionProductMachine._run_internal``) is the
first gate. It reads the role spec from the coordinator facet and compares it to
``Context.user.roles``.

Четыре режима проверки ролей:

1. NoneRole — доступ без аутентификации.
2. AnyRole — требуется хотя бы одна роль.
3. Конкретная роль (тип ``BaseRole``) — требуется соответствующий токен у пользователя.
4. Кортеж типов ролей — требуется хотя бы одна из перечисленных ролей (OR).

Если действие не имеет @check_roles — TypeError (не AuthorizationError).

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

NoneRole:
    - Пользователь без ролей — проходит.
    - Пользователь с ролями — проходит.

AnyRole:
    - Пользователь с ролями — проходит.
    - Пользователь без ролей — AuthorizationError.

Конкретная роль:
    - Роль совпадает — проходит.
    - Роль не совпадает — AuthorizationError.

Список ролей:
    - Пересечение есть — проходит.
    - Пересечения нет — AuthorizationError.

Отсутствие @check_roles:
    - TypeError с информативным сообщением.

Интеграция с TestBench:
    - PingAction (NoneRole) через bench — проходит.
    - FullAction (ManagerRole) через manager_bench — проходит.
    - AdminAction (AdminRole) через admin_bench — проходит.
    - AdminAction через bench без AdminRole — AuthorizationError.
"""

import pytest

from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.auth import AnyRole, check_roles
from action_machine.intents.context.context import Context
from action_machine.intents.context.user_info import UserInfo
from action_machine.intents.logging.log_coordinator import LogCoordinator
from action_machine.intents.meta.meta_decorator import meta
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.model.exceptions import AuthorizationError
from action_machine.runtime.machines.action_product_machine import ActionProductMachine
from action_machine.testing import TestBench
from tests.scenarios.domain_model import AdminAction, FullAction, PingAction
from tests.scenarios.domain_model.domains import TestDomain
from tests.scenarios.domain_model.roles import AdminRole, EditorRole, ManagerRole, UserRole

# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные действия для edge-case тестов
# ═════════════════════════════════════════════════════════════════════════════


class _MockParams(BaseParams):
    """Пустые параметры для edge-case действий."""
    pass


class _MockResult(BaseResult):
    """Пустой результат для edge-case действий."""
    pass


@meta(description="Действие с AnyRole для тестов", domain=TestDomain)
@check_roles(AnyRole)
class _ActionRoleAnyAction(BaseAction[_MockParams, _MockResult]):
    """Требует любую роль — пользователь должен быть аутентифицирован."""

    @summary_aspect("test")
    async def build_summary(self, params, state, box, connections):
        return _MockResult()


@meta(description="Действие для менеджеров и редакторов", domain=TestDomain)
@check_roles([ManagerRole, EditorRole])
class _ActionRoleListAction(BaseAction[_MockParams, _MockResult]):
    """Требует одну из ролей: manager или editor."""

    @summary_aspect("test")
    async def build_summary(self, params, state, box, connections):
        return _MockResult()


@meta(description="Действие без @check_roles — баг разработчика", domain=TestDomain)
class _ActionNoCheckRolesAction(BaseAction[_MockParams, _MockResult]):
    """Нет @check_roles — TypeError при выполнении."""

    @summary_aspect("test")
    async def build_summary(self, params, state, box, connections):
        return _MockResult()


# ═════════════════════════════════════════════════════════════════════════════
# Фикстуры
# ═════════════════════════════════════════════════════════════════════════════


@pytest.fixture()
def machine() -> ActionProductMachine:
    """ActionProductMachine с тихим логгером для unit-тестов."""
    return ActionProductMachine(
        mode="test",
        log_coordinator=LogCoordinator(loggers=[]),
    )


@pytest.fixture()
def context_admin() -> Context:
    """Контекст с ролями admin и user."""
    return Context(user=UserInfo(user_id="admin_1", roles=(AdminRole, UserRole)))


@pytest.fixture()
def context_manager() -> Context:
    """Контекст с ролью manager."""
    return Context(user=UserInfo(user_id="mgr_1", roles=(ManagerRole,)))


@pytest.fixture()
def context_no_roles() -> Context:
    """Контекст без ролей — анонимный пользователь."""
    return Context(user=UserInfo(user_id="guest", roles=()))


# ═════════════════════════════════════════════════════════════════════════════
# NoneRole — доступ без аутентификации
# ═════════════════════════════════════════════════════════════════════════════


class TestRoleNone:
    """NoneRole — действие доступно всем, включая анонимных."""

    def test_user_without_roles_passes(self, machine, context_no_roles) -> None:
        """
        Пользователь без ролей проходит проверку NoneRole.
        """
        # Arrange — PingAction с NoneRole, контекст без ролей
        action = PingAction()
        # Act — проверка ролей не бросает исключений
        rt = machine._get_execution_cache(action.__class__)
        machine._role_checker.check(action, context_no_roles, rt)

    def test_user_with_roles_passes(self, machine, context_admin) -> None:
        """
        Пользователь с ролями тоже проходит NoneRole.
        """
        # Arrange — PingAction с NoneRole, контекст с ролями admin, user
        action = PingAction()
        # Act — проверка не бросает исключений
        rt = machine._get_execution_cache(action.__class__)
        machine._role_checker.check(action, context_admin, rt)


# ═════════════════════════════════════════════════════════════════════════════
# AnyRole — требуется хотя бы одна роль
# ═════════════════════════════════════════════════════════════════════════════


class TestRoleAny:
    """AnyRole — пользователь должен быть аутентифицирован (иметь роли)."""

    def test_user_with_roles_passes(self, machine, context_admin) -> None:
        """
        Пользователь с ролями проходит AnyRole.
        """
        # Arrange — _ActionRoleAnyAction с AnyRole, контекст с ролями
        action = _ActionRoleAnyAction()

        # Act — проверка проходит
        rt = machine._get_execution_cache(action.__class__)
        machine._role_checker.check(action, context_admin, rt)

    def test_user_without_roles_rejected(self, machine, context_no_roles) -> None:
        """
        Пользователь без ролей отклоняется AnyRole → AuthorizationError.
        """
        # Arrange — _ActionRoleAnyAction с AnyRole, контекст без ролей
        action = _ActionRoleAnyAction()
        # Act & Assert — AuthorizationError с информативным сообщением
        with pytest.raises(AuthorizationError, match="Authentication required"):
            rt = machine._get_execution_cache(action.__class__)
            machine._role_checker.check(action, context_no_roles, rt)


# ═════════════════════════════════════════════════════════════════════════════
# Конкретная роль — один тип BaseRole
# ═════════════════════════════════════════════════════════════════════════════


class TestSingleRole:
    """Проверка конкретной роли: spec — тип BaseRole (не NoneRole, не AnyRole)."""

    def test_matching_role_passes(self, machine, context_admin) -> None:
        """
        Пользователь с AdminRole проходит проверку @check_roles(AdminRole).
        """
        # Arrange — AdminAction, контекст с AdminRole
        action = AdminAction()
        # Act — проверка проходит
        rt = machine._get_execution_cache(action.__class__)
        machine._role_checker.check(action, context_admin, rt)

    def test_non_matching_role_rejected(self, machine, context_manager) -> None:
        """
        Пользователь только с ManagerRole отклоняется для @check_roles(AdminRole).
        """
        # Arrange — AdminAction, контекст с ManagerRole (без AdminRole)
        action = AdminAction()
        # Act & Assert — AuthorizationError с указанием требуемой роли
        with pytest.raises(AuthorizationError, match="Required role: 'admin'"):
            rt = machine._get_execution_cache(action.__class__)
            machine._role_checker.check(action, context_manager, rt)

    def test_no_roles_rejected(self, machine, context_no_roles) -> None:
        """
        Пользователь без ролей отклоняется для @check_roles(AdminRole).
        """
        # Arrange — AdminAction, анонимный контекст
        action = AdminAction()
        # Act & Assert
        with pytest.raises(AuthorizationError):
            rt = machine._get_execution_cache(action.__class__)
            machine._role_checker.check(action, context_no_roles, rt)


# ═════════════════════════════════════════════════════════════════════════════
# Список ролей
# ═════════════════════════════════════════════════════════════════════════════


class TestRoleList:
    """Проверка OR по ролям: spec — кортеж типов BaseRole."""

    def test_intersection_passes(self, machine, context_manager) -> None:
        """
        Пользователь с ManagerRole проходит @check_roles([ManagerRole, EditorRole]).
        """
        # Arrange — список требований ManagerRole|EditorRole, у пользователя ManagerRole
        action = _ActionRoleListAction()
        # Act — проверка проходит
        rt = machine._get_execution_cache(action.__class__)
        machine._role_checker.check(action, context_manager, rt)

    def test_no_intersection_rejected(self, machine, context_admin) -> None:
        """
        Пользователь с AdminRole и UserRole отклоняется
        для @check_roles([ManagerRole, EditorRole]).
        """
        # Arrange — требования ManagerRole|EditorRole, у пользователя AdminRole, UserRole
        action = _ActionRoleListAction()
        # Act & Assert — AuthorizationError с указанием требуемых ролей
        with pytest.raises(AuthorizationError, match="Required one of the roles"):
            rt = machine._get_execution_cache(action.__class__)
            machine._role_checker.check(action, context_admin, rt)

    def test_no_roles_rejected(self, machine, context_no_roles) -> None:
        """
        Пользователь без ролей отклоняется для списка ролей.
        """
        # Arrange — _ActionRoleListAction, анонимный контекст
        action = _ActionRoleListAction()
        # Act & Assert
        with pytest.raises(AuthorizationError):
            rt = machine._get_execution_cache(action.__class__)
            machine._role_checker.check(action, context_no_roles, rt)


# ═════════════════════════════════════════════════════════════════════════════
# Отсутствие @check_roles — TypeError
# ═════════════════════════════════════════════════════════════════════════════


class TestMissingCheckRoles:
    """Действие без @check_roles — TypeError, не AuthorizationError."""

    def test_no_decorator_raises_type_error(self, machine, context_admin) -> None:
        """
        Действие без @check_roles → TypeError при проверке ролей.
        """
        # Arrange — _ActionNoCheckRolesAction без @check_roles
        action = _ActionNoCheckRolesAction()
        # Act & Assert — TypeError, не AuthorizationError
        with pytest.raises(TypeError, match="does not have a @check_roles"):
            rt = machine._get_execution_cache(action.__class__)
            machine._role_checker.check(action, context_admin, rt)


# ═════════════════════════════════════════════════════════════════════════════
# Интеграция с TestBench
# ═════════════════════════════════════════════════════════════════════════════


class TestRolesWithBench:
    """Проверка ролей через TestBench — полный конвейер с двумя машинами."""

    @pytest.fixture()
    def bench(self) -> TestBench:
        """TestBench без ролей (анонимный пользователь)."""
        return TestBench(log_coordinator=LogCoordinator(loggers=[]))

    @pytest.fixture()
    def manager_bench(self, bench) -> TestBench:
        """TestBench с ролью manager."""
        return bench.with_user(user_id="mgr_1", roles=(ManagerRole,))

    @pytest.fixture()
    def admin_bench(self, bench) -> TestBench:
        """TestBench с ролью admin."""
        return bench.with_user(user_id="admin_1", roles=(AdminRole,))

    @pytest.mark.asyncio
    async def test_ping_with_anonymous_bench(self, bench) -> None:
        """
        PingAction (NoneRole) проходит через bench без ролей.
        """
        # Arrange — PingAction с NoneRole
        action = PingAction()
        params = PingAction.Params()

        # Act — полный конвейер через bench
        result = await bench.run(action, params, rollup=False)

        # Assert — конвейер завершился успешно
        assert result.message == "pong"

    @pytest.mark.asyncio
    async def test_full_action_with_manager_bench(self, manager_bench) -> None:
        """
        FullAction (роль "manager") проходит через manager_bench.
        """
        # Arrange — FullAction с ролью "manager", мок db для connections
        from unittest.mock import AsyncMock

        from tests.scenarios.domain_model import NotificationService, PaymentService, TestDbManager

        mock_payment = AsyncMock(spec=PaymentService)
        mock_payment.charge.return_value = "TXN-BENCH"
        mock_notification = AsyncMock(spec=NotificationService)
        mock_db = AsyncMock(spec=TestDbManager)

        bench_with_mocks = manager_bench.with_mocks({
            PaymentService: mock_payment,
            NotificationService: mock_notification,
        })

        action = FullAction()
        params = FullAction.Params(user_id="u1", amount=100.0)

        # Act — полный конвейер
        result = await bench_with_mocks.run(
            action, params, rollup=False, connections={"db": mock_db},
        )

        # Assert — конвейер завершился, результат содержит данные
        assert result.status == "created"

    @pytest.mark.asyncio
    async def test_admin_action_rejected_without_admin_role(self, bench) -> None:
        """
        AdminAction (AdminRole) отклоняется через bench без ролей.
        """
        # Arrange — AdminAction, bench без AdminRole
        action = AdminAction()
        params = AdminAction.Params(target="user_456")

        # Act & Assert — AuthorizationError от машины
        with pytest.raises(AuthorizationError):
            await bench.run(action, params, rollup=False)

    @pytest.mark.asyncio
    async def test_admin_action_passes_with_admin_bench(self, admin_bench) -> None:
        """
        AdminAction (AdminRole) проходит через admin_bench.
        """
        # Arrange — AdminAction, admin_bench с AdminRole
        action = AdminAction()
        params = AdminAction.Params(target="user_456")

        # Act — полный конвейер
        result = await admin_bench.run(action, params, rollup=False)

        # Assert — результат содержит данные
        assert result.success is True
        assert result.target == "user_456"
