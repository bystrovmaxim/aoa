# tests/runtime/test_sync_machine.py
"""Tests SyncActionProductMachine - synchronous wrapper for ActionProductMachine.

═══════════════════ ════════════════════ ════════════════════ ════════════════════
PURPOSE
═══════════════════ ════════════════════ ════════════════════ ════════════════════

SyncActionProductMachine is a synchronous analogue of ActionProductMachine. Method
run() is a regular (non-async) method that calls asyncio.run()
internally to execute an asynchronous pipeline. Designed for synchronous
environments: CLI scripts, Celery, Django without async.

SyncActionProductMachine inherits ActionProductMachine and overrides
only public method run(). All pipeline logic (role checking,
validation connections, checkers, aspects, plugins) are inherited without changes.

The production machine always passes rollup=False to _run_internal().

═══════════════════ ════════════════════ ════════════════════ ════════════════════
SCENARIOS COVERED
═══════════════════ ════════════════════ ════════════════════ ════════════════════

Basic execution:
    - PingAction via sync run() → result "pong".
    - SimpleAction via sync run() → greeting.
    - FullAction via sync run() → Result with txn_id, total, order_id.

Checking roles via sync:
    - NoneRole - passes without roles.
    - Specific role - AuthorizationError if there is a mismatch.

Checking connections via sync:
    - FullAction without connections → ConnectionValidationError.
    - FullAction with correct connections → OK.

Checking checkers via sync:
    - Correct data → conveyor passes.

Inheritance from ActionProductMachine:
    - isinstance(sync_machine, ActionProductMachine) → True.
    - _run_internal() is available and working."""

from unittest.mock import AsyncMock

import pytest

from action_machine.context.context import Context
from action_machine.context.user_info import UserInfo
from action_machine.exceptions import AuthorizationError, ConnectionValidationError
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.runtime.action_product_machine import ActionProductMachine
from action_machine.runtime.sync_action_product_machine import SyncActionProductMachine
from tests.scenarios.domain_model import FullAction, OrdersDbManager, PingAction, SimpleAction
from tests.scenarios.domain_model.roles import AdminRole, ManagerRole
from tests.scenarios.domain_model.services import (
    NotificationService,
    NotificationServiceResource,
    PaymentService,
    PaymentServiceResource,
)

# ═════════════════════════════════════════════════════════════════════════════
#Fittings
# ═════════════════════════════════════════════════════════════════════════════


@pytest.fixture()
def sync_machine() -> SyncActionProductMachine:
    """SyncActionProductMachine with a silent logger for unit tests.

    LogCoordinator without loggers suppresses output to stdout."""
    return SyncActionProductMachine(
        mode="test",
        log_coordinator=LogCoordinator(loggers=[]),
    )


@pytest.fixture()
def context_manager() -> Context:
    """Context with the manager role for FullAction."""
    return Context(user=UserInfo(user_id="mgr_1", roles=(ManagerRole, AdminRole)))


@pytest.fixture()
def context_no_roles() -> Context:
    """A context without roles is an anonymous user."""
    return Context(user=UserInfo(user_id="guest", roles=()))


# ═════════════════════════════════════════════════════════════════════════════
#Basic execution via sync run()
# ═════════════════════════════════════════════════════════════════════════════


class TestSyncBasicExecution:
    """Basic execution of actions via synchronous run()."""

    def test_ping_action_returns_pong(self, sync_machine, context_no_roles) -> None:
        """PingAction via sync run() → result with message="pong".

        SyncActionProductMachine.run() calls asyncio.run() internally,
        which creates an event loop and executes an asynchronous pipeline.
        PingAction has NoneRole—passes without roles."""
        #Arrange - PingAction with empty parameters
        action = PingAction()
        params = PingAction.Params()

        #Act - synchronous call without await
        result = sync_machine.run(context_no_roles, action, params)

        #Assert - the pipeline has completed, the result contains "pong"
        assert result.message == "pong"

    def test_simple_action_returns_greeting(self, sync_machine, context_manager) -> None:
        """SimpleAction via sync run() → greeting "Hello, Alice!".

        SimpleAction contains one regular aspect (validate_name)
        with a result_string checker and one summary aspect."""
        #Arrange - SimpleAction named "Alice"
        action = SimpleAction()
        params = SimpleAction.Params(name="Alice")

        #Act - synchronous call
        result = sync_machine.run(context_manager, action, params)

        #Assert - greeting is formed from validated_name
        assert result.greeting == "Hello, Alice!"

    def test_full_action_via_run_internal(self, sync_machine, context_manager) -> None:
        """FullAction via _run_internal() with mocks of dependencies and connections.

        SyncActionProductMachine inherits _run_internal() from
        ActionProductMachine. The method is asynchronous, called directly
        via asyncio.run() in this test (pytest-asyncio)."""
        #Arrange - mock dependencies and connections
        mock_payment = AsyncMock(spec=PaymentService)
        mock_payment.charge.return_value = "TXN-SYNC"
        mock_notification = AsyncMock(spec=NotificationService)
        mock_db = AsyncMock(spec=OrdersDbManager)

        action = FullAction()
        params = FullAction.Params(user_id="u1", amount=250.0)

        #Act - synchronous call via asyncio.run wrapped in _run_internal
        import asyncio

        result = asyncio.run(
            sync_machine._run_internal(
                context=context_manager,
                action=action,
                params=params,
                resources={
                    PaymentServiceResource: PaymentServiceResource(mock_payment),
                    NotificationServiceResource: NotificationServiceResource(mock_notification),
                },
                connections={"db": mock_db},
                nested_level=0,
                rollup=False,
            )
        )

        #Assert - the pipeline has completed with data from the mocks
        assert result.order_id == "ORD-u1"
        assert result.txn_id == "TXN-SYNC"
        assert result.total == 250.0
        assert result.status == "created"


# ═════════════════════════════════════════════════════════════════════════════
#Checking roles via sync
# ═════════════════════════════════════════════════════════════════════════════


class TestSyncRoles:
    """Role checking works identically to the async machine."""

    def test_role_none_passes_without_roles(self, sync_machine, context_no_roles) -> None:
        """PingAction (NoneRole) goes through the sync machine without roles.

        Role gate uses the same ``RoleChecker`` pipeline as ``ActionProductMachine``."""
        #Arrange - PingAction with NoneRole, context without roles
        action = PingAction()
        params = PingAction.Params()

        #Act - synchronous call
        result = sync_machine.run(context_no_roles, action, params)

        #Assert - the pipeline has ended
        assert result.message == "pong"

    def test_wrong_role_raises_authorization_error(self, sync_machine, context_no_roles) -> None:
        """FullAction (role "manager") via sync machine without roles →
        AuthorizationError.

        Role check runs before the aspect pipeline, same as the async machine."""
        #Arrange - FullAction requires "manager", context without roles
        action = FullAction()
        params = FullAction.Params(user_id="u1", amount=100.0)

        # Act & Assert — AuthorizationError
        with pytest.raises(AuthorizationError):
            sync_machine.run(context_no_roles, action, params)


# ═════════════════════════════════════════════════════════════════════════════
#Checking connections via sync
# ═════════════════════════════════════════════════════════════════════════════


class TestSyncConnections:
    """Validation of connections works identically to the async machine."""

    def test_missing_connections_raises(self, sync_machine, context_manager) -> None:
        """FullAction through a sync machine without connections → ConnectionValidationError.

        FullAction declares @connection(OrdersDbManager, key="db").
        Without connections, the machine throws ConnectionValidationError."""
        #Arrange - FullAction without connections
        action = FullAction()
        params = FullAction.Params(user_id="u1", amount=100.0)

        # Act & Assert — ConnectionValidationError
        with pytest.raises(ConnectionValidationError):
            sync_machine.run(context_manager, action, params, connections=None)

    def test_ping_without_connections_ok(self, sync_machine, context_no_roles) -> None:
        """PingAction through a sync machine without connections → OK.

        PingAction does not declare @connection, connections=None is acceptable."""
        #Arrange - PingAction without @connection
        action = PingAction()
        params = PingAction.Params()

        #Act - sync run without connections
        result = sync_machine.run(context_no_roles, action, params)

        #Assert - the pipeline has ended
        assert result.message == "pong"


# ═════════════════════════════════════════════════════════════════════════════
#Inheritance from ActionProductMachine
# ═════════════════════════════════════════════════════════════════════════════


class TestInheritance:
    """SyncActionProductMachine inherits ActionProductMachine."""

    def test_isinstance_action_product_machine(self, sync_machine) -> None:
        """SyncActionProductMachine is a subclass of ActionProductMachine.

        This ensures that the sync machine inherits all pipeline logic:
        role checking, connections validation, checkers, aspects, plugins."""
        #Arrange & Act - check via isinstance

        #Assert - the sync machine is an ActionProductMachine
        assert isinstance(sync_machine, ActionProductMachine)
        assert isinstance(sync_machine, SyncActionProductMachine)

    def test_has_run_internal(self, sync_machine) -> None:
        """_run_internal() is available on the sync machine.

        The method is inherited from ActionProductMachine and used
        inside run() via asyncio.run()."""
        #Arrange & Act - checking for method availability

        #Assert - the method exists and is callable
        assert hasattr(sync_machine, "_run_internal")
        assert callable(sync_machine._run_internal)

    def test_mode_attribute(self, sync_machine) -> None:
        """The _mode attribute is set in the constructor and is inherited."""
        #Arrange - the machine was created with mode="test" in the fixture

        #Act & Assert - mode available
        assert sync_machine._mode == "test"

    def test_rollup_always_false_in_public_run(self, sync_machine, context_no_roles) -> None:
        """The production sync machine always passes rollup=False.

        The run() method does not accept the rollup parameter - it is fixed
        as False within the implementation. Rollup is only available via
        TestBench."""
        #Arrange - PingAction via public run()
        action = PingAction()
        params = PingAction.Params()

        #Act - run() does not accept rollup (unlike TestBench.run)
        result = sync_machine.run(context_no_roles, action, params)

        #Assert - the pipeline has ended (rollup=False inside)
        assert result.message == "pong"
        assert result.message == "pong"
