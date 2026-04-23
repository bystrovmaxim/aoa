# tests/runtime/test_machine_roles.py
"""Role verification tests in ActionProductMachine.

═══════════════════ ════════════════════ ════════════════════ ════════════════════
PURPOSE
═══════════════════ ════════════════════ ════════════════════ ════════════════════

``RoleChecker.check()`` (used from ``ActionProductMachine._run_internal``) is the
first gate. It reads the role spec from the coordinator facet and compares it to
``Context.user.roles``.

Four role verification modes:

1. NoneRole - access without authentication.
2. AnyRole - at least one role is required.
3. Specific role (type ``BaseRole``) - the corresponding token is required from the user.
4. Tuple of role types - at least one of the listed roles (OR) is required.

If the action does not have @check_roles - TypeError (not AuthorizationError).

═══════════════════ ════════════════════ ════════════════════ ════════════════════
SCENARIOS COVERED
═══════════════════ ════════════════════ ════════════════════ ════════════════════

NoneRole:
    - User without roles - passes.
    - User with roles - passes.

AnyRole:
    - User with roles - passes.
    - User without roles - AuthorizationError.

Specific Role:
    - The role matches - it passes.
    - Role does not match - AuthorizationError.

List of roles:
    - There is an intersection - it passes.
    - There is no intersection - AuthorizationError.

Lack of @check_roles:
    - TypeError with an informative message.

TestBench Integration:
    - PingAction (NoneRole) via bench - passes.
    - FullAction (ManagerRole) via manager_bench - passes.
    - AdminAction (AdminRole) via admin_bench - passes.
    - AdminAction via bench without AdminRole - AuthorizationError."""

import pytest

from action_machine.context.context import Context
from action_machine.context.user_info import UserInfo
from action_machine.exceptions import AuthorizationError
from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.check_roles import AnyRole, check_roles
from action_machine.intents.meta.meta_decorator import meta
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.runtime.action_product_machine import ActionProductMachine
from action_machine.testing import TestBench
from tests.scenarios.domain_model import AdminAction, FullAction, PingAction
from tests.scenarios.domain_model.domains import TestDomain
from tests.scenarios.domain_model.roles import AdminRole, EditorRole, ManagerRole, UserRole

# ═════════════════════════════════════════════════════════════════════════════
#Helper steps for edge-case tests
# ═════════════════════════════════════════════════════════════════════════════


class _MockParams(BaseParams):
    """Empty parameters for edge-case actions."""
    pass


class _MockResult(BaseResult):
    """Empty result for edge-case actions."""
    pass


@meta(description="Action with AnyRole for tests", domain=TestDomain)
@check_roles(AnyRole)
class _ActionRoleAnyAction(BaseAction[_MockParams, _MockResult]):
    """Requires any role - the user must be authenticated."""

    @summary_aspect("test")
    async def build_summary(self, params, state, box, connections):
        return _MockResult()


@meta(description="Action for managers and editors", domain=TestDomain)
@check_roles([ManagerRole, EditorRole])
class _ActionRoleListAction(BaseAction[_MockParams, _MockResult]):
    """Requires one of the roles: manager or editor."""

    @summary_aspect("test")
    async def build_summary(self, params, state, box, connections):
        return _MockResult()


@meta(description="Action without @check_roles is a developer bug", domain=TestDomain)
class _ActionNoCheckRolesAction(BaseAction[_MockParams, _MockResult]):
    """No @check_roles - TypeError on execution."""

    @summary_aspect("test")
    async def build_summary(self, params, state, box, connections):
        return _MockResult()


# ═════════════════════════════════════════════════════════════════════════════
#Fittings
# ═════════════════════════════════════════════════════════════════════════════


@pytest.fixture()
def machine() -> ActionProductMachine:
    """ActionProductMachine with a silent logger for unit tests."""
    return ActionProductMachine(
        mode="test",
        log_coordinator=LogCoordinator(loggers=[]),
    )


@pytest.fixture()
def context_admin() -> Context:
    """Context with admin and user roles."""
    return Context(user=UserInfo(user_id="admin_1", roles=(AdminRole, UserRole)))


@pytest.fixture()
def context_manager() -> Context:
    """Context with the manager role."""
    return Context(user=UserInfo(user_id="mgr_1", roles=(ManagerRole,)))


@pytest.fixture()
def context_no_roles() -> Context:
    """A context without roles is an anonymous user."""
    return Context(user=UserInfo(user_id="guest", roles=()))


# ═════════════════════════════════════════════════════════════════════════════
#NoneRole - access without authentication
# ═════════════════════════════════════════════════════════════════════════════


class TestRoleNone:
    """NoneRole - the action is available to everyone, including anonymous ones."""

    def test_user_without_roles_passes(self, machine, context_no_roles) -> None:
        """A user without roles passes the NoneRole check."""
        #Arrange - PingAction with NoneRole, context without roles
        action = PingAction()
        #Act - role check does not throw exceptions
        rt = machine._get_execution_cache(action.__class__)
        machine._role_checker.check(action, context_no_roles, rt)

    def test_user_with_roles_passes(self, machine, context_admin) -> None:
        """A user with roles also passes NoneRole."""
        #Arrange - PingAction with NoneRole, context with roles admin, user
        action = PingAction()
        #Act - check does not throw exceptions
        rt = machine._get_execution_cache(action.__class__)
        machine._role_checker.check(action, context_admin, rt)


# ═════════════════════════════════════════════════════════════════════════════
#AnyRole - at least one role is required
# ═════════════════════════════════════════════════════════════════════════════


class TestRoleAny:
    """AnyRole - the user must be authenticated (have roles)."""

    def test_user_with_roles_passes(self, machine, context_admin) -> None:
        """A user with roles passes AnyRole."""
        #Arrange - _ActionRoleAnyAction with AnyRole, context with roles
        action = _ActionRoleAnyAction()

        #Act—check passes
        rt = machine._get_execution_cache(action.__class__)
        machine._role_checker.check(action, context_admin, rt)

    def test_user_without_roles_rejected(self, machine, context_no_roles) -> None:
        """A user without roles is rejected by AnyRole → AuthorizationError."""
        #Arrange - _ActionRoleAnyAction with AnyRole, context without roles
        action = _ActionRoleAnyAction()
        #Act & Assert - AuthorizationError with informative message
        with pytest.raises(AuthorizationError, match="Authentication required"):
            rt = machine._get_execution_cache(action.__class__)
            machine._role_checker.check(action, context_no_roles, rt)


# ═════════════════════════════════════════════════════════════════════════════
#Specific role - one type BaseRole
# ═════════════════════════════════════════════════════════════════════════════


class TestSingleRole:
    """Checking a specific role: spec - BaseRole type (not NoneRole, not AnyRole)."""

    def test_matching_role_passes(self, machine, context_admin) -> None:
        """A user with AdminRole passes the @check_roles(AdminRole) check."""
        #Arrange — AdminAction, context with AdminRole
        action = AdminAction()
        #Act—check passes
        rt = machine._get_execution_cache(action.__class__)
        machine._role_checker.check(action, context_admin, rt)

    def test_non_matching_role_rejected(self, machine, context_manager) -> None:
        """A user with only ManagerRole is rejected for @check_roles(AdminRole)."""
        #Arrange - AdminAction, context with ManagerRole (without AdminRole)
        action = AdminAction()
        #Act & Assert - AuthorizationError indicating the required role
        with pytest.raises(AuthorizationError, match="Required role: 'admin'"):
            rt = machine._get_execution_cache(action.__class__)
            machine._role_checker.check(action, context_manager, rt)

    def test_no_roles_rejected(self, machine, context_no_roles) -> None:
        """A user without roles is rejected for @check_roles(AdminRole)."""
        #Arrange - AdminAction, anonymous context
        action = AdminAction()
        # Act & Assert
        with pytest.raises(AuthorizationError):
            rt = machine._get_execution_cache(action.__class__)
            machine._role_checker.check(action, context_no_roles, rt)


# ═════════════════════════════════════════════════════════════════════════════
#List of roles
# ═════════════════════════════════════════════════════════════════════════════


class TestRoleList:
    """Checking OR by roles: spec is a tuple of BaseRole types."""

    def test_intersection_passes(self, machine, context_manager) -> None:
        """A user with ManagerRole passes @check_roles([ManagerRole, EditorRole])."""
        #Arrange — list of ManagerRole|EditorRole requirements, for the ManagerRole user
        action = _ActionRoleListAction()
        #Act—check passes
        rt = machine._get_execution_cache(action.__class__)
        machine._role_checker.check(action, context_manager, rt)

    def test_no_intersection_rejected(self, machine, context_admin) -> None:
        """User with AdminRole and UserRole is rejected
        for @check_roles([ManagerRole, EditorRole])."""
        #Arrange - requirements ManagerRole|EditorRole, for the user AdminRole, UserRole
        action = _ActionRoleListAction()
        #Act & Assert - AuthorizationError indicating required roles
        with pytest.raises(AuthorizationError, match="Required one of the roles"):
            rt = machine._get_execution_cache(action.__class__)
            machine._role_checker.check(action, context_admin, rt)

    def test_no_roles_rejected(self, machine, context_no_roles) -> None:
        """A user without roles is rejected for the list of roles."""
        #Arrange - _ActionRoleListAction, anonymous context
        action = _ActionRoleListAction()
        # Act & Assert
        with pytest.raises(AuthorizationError):
            rt = machine._get_execution_cache(action.__class__)
            machine._role_checker.check(action, context_no_roles, rt)


# ═════════════════════════════════════════════════════════════════════════════
#Missing @check_roles - TypeError
# ═════════════════════════════════════════════════════════════════════════════


class TestMissingCheckRoles:
    """An action without @check_roles is a TypeError, not an AuthorizationError."""

    def test_no_decorator_raises_type_error(self, machine, context_admin) -> None:
        """Action without @check_roles → TypeError when checking roles."""
        #Arrange — _ActionNoCheckRolesAction without @check_roles
        action = _ActionNoCheckRolesAction()
        #Act & Assert - TypeError, not AuthorizationError
        with pytest.raises(TypeError, match="does not have a @check_roles"):
            rt = machine._get_execution_cache(action.__class__)
            machine._role_checker.check(action, context_admin, rt)


# ═════════════════════════════════════════════════════════════════════════════
#TestBench Integration
# ═════════════════════════════════════════════════════════════════════════════


class TestRolesWithBench:
    """Verifying roles via TestBench - a full two-machine pipeline."""

    @pytest.fixture()
    def bench(self) -> TestBench:
        """TestBench without roles (anonymous user)."""
        return TestBench(log_coordinator=LogCoordinator(loggers=[]))

    @pytest.fixture()
    def manager_bench(self, bench) -> TestBench:
        """TestBench with the manager role."""
        return bench.with_user(user_id="mgr_1", roles=(ManagerRole,))

    @pytest.fixture()
    def admin_bench(self, bench) -> TestBench:
        """TestBench with the admin role."""
        return bench.with_user(user_id="admin_1", roles=(AdminRole,))

    @pytest.mark.asyncio
    async def test_ping_with_anonymous_bench(self, bench) -> None:
        """PingAction (NoneRole) goes through a bench without roles."""
        #Arrange - PingAction with NoneRole
        action = PingAction()
        params = PingAction.Params()

        #Act - full pipeline via bench
        result = await bench.run(action, params, rollup=False)

        #Assert - the pipeline completed successfully
        assert result.message == "pong"

    @pytest.mark.asyncio
    async def test_full_action_with_manager_bench(self, manager_bench) -> None:
        """FullAction (role "manager") goes through manager_bench."""
        #Arrange - FullAction with the role "manager", db mock for connections
        from unittest.mock import AsyncMock

        from tests.scenarios.domain_model import OrdersDbManager
        from tests.scenarios.domain_model.services import (
            NotificationService,
            NotificationServiceResource,
            PaymentService,
            PaymentServiceResource,
        )

        mock_payment = AsyncMock(spec=PaymentService)
        mock_payment.charge.return_value = "TXN-BENCH"
        mock_notification = AsyncMock(spec=NotificationService)
        mock_db = AsyncMock(spec=OrdersDbManager)

        bench_with_mocks = manager_bench.with_mocks({
            PaymentServiceResource: PaymentServiceResource(mock_payment),
            NotificationServiceResource: NotificationServiceResource(mock_notification),
        })

        action = FullAction()
        params = FullAction.Params(user_id="u1", amount=100.0)

        #Act - full pipeline
        result = await bench_with_mocks.run(
            action, params, rollup=False, connections={"db": mock_db},
        )

        #Assert - the pipeline has completed, the result contains data
        assert result.status == "created"

    @pytest.mark.asyncio
    async def test_admin_action_rejected_without_admin_role(self, bench) -> None:
        """AdminAction (AdminRole) is rejected via bench without roles."""
        #Arrange — AdminAction, bench without AdminRole
        action = AdminAction()
        params = AdminAction.Params(target="user_456")

        #Act & Assert - AuthorizationError from machine
        with pytest.raises(AuthorizationError):
            await bench.run(action, params, rollup=False)

    @pytest.mark.asyncio
    async def test_admin_action_passes_with_admin_bench(self, admin_bench) -> None:
        """AdminAction (AdminRole) goes through admin_bench."""
        #Arrange - AdminAction, admin_bench with AdminRole
        action = AdminAction()
        params = AdminAction.Params(target="user_456")

        #Act - full pipeline
        result = await admin_bench.run(action, params, rollup=False)

        #Assert - the result contains data
        assert result.success is True
        assert result.target == "user_456"
        assert result.target == "user_456"
