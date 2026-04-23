# tests/runtime/test_machine_connections.py
"""Connections validation tests in ActionProductMachine.

═══════════════════ ════════════════════ ════════════════════ ════════════════════
PURPOSE
═══════════════════ ════════════════════ ════════════════════ ════════════════════

``ConnectionValidator.validate()`` (invoked from ``ActionProductMachine._run_internal``)
is the connections gate: declared keys vs passed ``connections`` and
``BaseResourceManager`` value types.

Two-level validation:

1. Key verification - declared keys must match exactly
   with actual ones.

2. Type checking - every value must be an instance
   BaseResourceManager.

═══════════════════ ════════════════════ ════════════════════ ════════════════════
SCENARIOS COVERED
═══════════════════ ════════════════════ ════════════════════ ════════════════════

Action without @connection:
    - Without connections (None) → empty dict.
    - With connections → ConnectionValidationError.

Action with one @connection:
    - Correct connections with matching key → OK.
    - Without connections → ConnectionValidationError.
    - Extra key → ConnectionValidationError.
    - The value is not BaseResourceManager -> ConnectionValidationError.

Action with two @connections:
    - Both keys have been transferred → OK.
    - One key is missing → ConnectionValidationError.

Integration via run():
    - FullAction with correct connections → result.
    - FullAction without connections → ConnectionValidationError.
    - FullAction with an extra key → ConnectionValidationError."""

from unittest.mock import AsyncMock

import pytest
from pydantic import Field

from action_machine.context.context import Context
from action_machine.context.user_info import UserInfo
from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.check_roles import NoneRole, check_roles
from action_machine.intents.connection import connection
from action_machine.intents.meta.meta_decorator import meta
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.exceptions import ConnectionValidationError
from action_machine.resources.base_resource_manager import BaseResourceManager
from action_machine.runtime.action_product_machine import ActionProductMachine
from tests.scenarios.domain_model import FullAction, NotificationService, PaymentService, PingAction, TestDbManager
from tests.scenarios.domain_model.domains import TestDomain
from tests.scenarios.domain_model.roles import AdminRole, ManagerRole


def _validate_connections(
    machine: ActionProductMachine,
    action: BaseAction[BaseParams, BaseResult],  # any concrete action binding
    connections: dict[str, BaseResourceManager] | None,
) -> dict[str, BaseResourceManager]:
    rt = machine._get_execution_cache(action.__class__)
    return machine._connection_validator.validate(action, connections, rt)


# ═════════════════════════════════════════════════════════════════════════════
# Helper steps for edge-case tests
# ═════════════════════════════════════════════════════════════════════════════


class _TwoConnParams(BaseParams):
    token: str = Field(default="x", description="Test token for two-connection probe")


class _TwoConnResult(BaseResult):
    ok: bool = Field(default=True, description="Two-connection probe result")


@meta(description="Resource manager stub for connections tests", domain=TestDomain)
class _MockResourceManager(BaseResourceManager):
    """Minimal implementation of BaseResourceManager for tests."""

    def get_wrapper_class(self):
        return None


@meta(description="Action with two connections", domain=TestDomain)
@check_roles(NoneRole)
@connection(_MockResourceManager, key="db", description="Database")
@connection(_MockResourceManager, key="cache", description="Cash")
class _ActionTwoConnectionsAction(BaseAction[_TwoConnParams, _TwoConnResult]):
    """Declares two connections: db and cache."""

    @summary_aspect("test")
    async def build_summary(self, params, state, box, connections):
        return _TwoConnResult()


# ═════════════════════════════════════════════════════════════════════════════
# Fittings
# ═════════════════════════════════════════════════════════════════════════════


@pytest.fixture()
def machine() -> ActionProductMachine:
    """ActionProductMachine with a silent logger for unit tests."""
    return ActionProductMachine(
        mode="test",
        log_coordinator=LogCoordinator(loggers=[]),
    )


@pytest.fixture()
def context() -> Context:
    """Context with roles to pass the role check."""
    return Context(user=UserInfo(user_id="mgr_1", roles=(ManagerRole, AdminRole)))


@pytest.fixture()
def mock_resource() -> _MockResourceManager:
    """An instance of _MockResourceManager to pass to connections."""
    return _MockResourceManager()


# ═════════════════════════════════════════════════════════════════════════════
# Action without @connection
# ═════════════════════════════════════════════════════════════════════════════


class TestNoConnectionDeclaration:
    """Action without @connection - connections are not expected."""

    def test_no_connections_returns_empty_dict(self, machine, context) -> None:
        """Action without @connection + connections=None → empty dict."""
        # Arrange - PingAction without @connection
        action = PingAction()
        # Act - check with connections=None
        result = _validate_connections(machine, action, None)

        # Assert - empty dict, not None
        assert result == {}

    def test_connections_provided_raises(self, machine, context, mock_resource) -> None:
        """Action without @connection + connections={"db": ...} → ConnectionValidationError."""
        # Arrange — PingAction without @connection, but with passed connections
        action = PingAction()
        connections = {"db": mock_resource}

        # Act & Assert - ConnectionValidationError specifying keys
        with pytest.raises(ConnectionValidationError, match="does not declare any @connection"):
            _validate_connections(machine, action, connections)


# ═════════════════════════════════════════════════════════════════════════════
# Action with one @connection
# ═════════════════════════════════════════════════════════════════════════════


class TestSingleConnection:
    """Action with one @connection("db") - FullAction."""

    def test_correct_key_passes(self, machine, context) -> None:
        """
        FullAction + connections={"db": MockResourceManager} → OK.
        """
        # Arrange - FullAction with @connection(key="db")
        action = FullAction()
        mock_db = AsyncMock(spec=TestDbManager)

        # Act - check connections
        result = _validate_connections(machine, action, {"db": mock_db})

        # Assert - connections passed the test, returned as is
        assert "db" in result

    def test_no_connections_raises(self, machine, context) -> None:
        """
        FullAction + connections=None → ConnectionValidationError.
        """
        # Arrange — FullAction, connections=None
        action = FullAction()
        # Act & Assert — ConnectionValidationError
        with pytest.raises(ConnectionValidationError, match="declares connections"):
            _validate_connections(machine, action, None)

    def test_extra_key_raises(self, machine, context, mock_resource) -> None:
        """
        FullAction + connections={"db": ..., "extra": ...} → ConnectionValidationError.
        """
        # Arrange — FullAction with extra key "extra"
        action = FullAction()
        mock_db = AsyncMock(spec=TestDbManager)
        connections = {"db": mock_db, "extra": mock_resource}

        # Act & Assert — ConnectionValidationError
        with pytest.raises(ConnectionValidationError, match="received extra connections"):
            _validate_connections(machine, action, connections)

    def test_value_not_resource_manager_raises(self, machine, context) -> None:
        """connections={"db": "string"} → ConnectionValidationError."""
        # Arrange - string instead of manager
        action = FullAction()
        connections = {"db": "it's a string, not a manager"}

        # Act & Assert - checking value type
        with pytest.raises(ConnectionValidationError, match="must be an instance of BaseResourceManager"):
            _validate_connections(machine, action, connections)

    def test_value_none_raises(self, machine, context) -> None:
        """
        connections={"db": None} → ConnectionValidationError.
        """
        # Arrange - None instead of manager
        action = FullAction()
        connections = {"db": None}

        # Act & Assert
        with pytest.raises(ConnectionValidationError, match="must be an instance of BaseResourceManager"):
            _validate_connections(machine, action, connections)

    def test_value_int_raises(self, machine, context) -> None:
        """
        connections={"db": 42} → ConnectionValidationError.
        """
        # Arrange - number instead of manager
        action = FullAction()
        connections = {"db": 42}

        # Act & Assert
        with pytest.raises(ConnectionValidationError, match="must be an instance of BaseResourceManager"):
            _validate_connections(machine, action, connections)


# ═════════════════════════════════════════════════════════════════════════════
# Action with two @connections
# ═════════════════════════════════════════════════════════════════════════════


class TestTwoConnections:
    """Action with two @connection("db", "cache")."""

    def test_both_keys_present_passes(self, machine, context, mock_resource) -> None:
        """
        _ActionTwoConnectionsAction + connections={"db": ..., "cache": ...} → OK.
        """
        # Arrange - action with two @connections, both keys are transferred
        action = _ActionTwoConnectionsAction()
        connections = {
            "db": _MockResourceManager(),
            "cache": _MockResourceManager(),
        }

        # Act—check passes
        result = _validate_connections(machine, action, connections)

        # Assert - both keys as a result
        assert "db" in result
        assert "cache" in result

    def test_missing_key_raises(self, machine, context, mock_resource) -> None:
        """_ActionTwoConnectionsAction + connections={"db": ...} (without cache) →
        ConnectionValidationError."""
        # Arrange - only one key out of two declared
        action = _ActionTwoConnectionsAction()
        connections = {"db": mock_resource}

        # Act & Assert — ConnectionValidationError
        with pytest.raises(ConnectionValidationError, match="missing required connections"):
            _validate_connections(machine, action, connections)


# ═════════════════════════════════════════════════════════════════════════════
# Integration via run()
# ═════════════════════════════════════════════════════════════════════════════


class TestConnectionsViaRun:
    """Checking connections through the full run() pipeline."""

    @pytest.mark.asyncio
    async def test_full_action_with_valid_connections(self, machine, context) -> None:
        """FullAction via run() with correct connections → result."""
        # Arrange - FullAction with dependency and connection mocks
        mock_payment = AsyncMock(spec=PaymentService)
        mock_payment.charge.return_value = "TXN-RUN"
        mock_notification = AsyncMock(spec=NotificationService)
        mock_db = AsyncMock(spec=TestDbManager)

        action = FullAction()
        params = FullAction.Params(user_id="u1", amount=100.0)

        # Act - run() with resources (mocks) and connections
        result = await machine._run_internal(
            context=context,
            action=action,
            params=params,
            resources={PaymentService: mock_payment, NotificationService: mock_notification},
            connections={"db": mock_db},
            nested_level=0,
            rollup=False,
        )

        # Assert - the pipeline has completed, the result contains data
        assert result.order_id == "ORD-u1"
        assert result.txn_id == "TXN-RUN"
        assert result.status == "created"

    @pytest.mark.asyncio
    async def test_full_action_without_connections_raises(self, machine, context) -> None:
        """FullAction via run() without connections → ConnectionValidationError."""
        # Arrange - FullAction without connections
        action = FullAction()
        params = FullAction.Params(user_id="u1", amount=100.0)

        # Act & Assert - ConnectionValidationError before pipeline starts
        with pytest.raises(ConnectionValidationError):
            await machine.run(context, action, params, connections=None)

    @pytest.mark.asyncio
    async def test_full_action_with_extra_key_raises(self, machine, context) -> None:
        """FullAction via run() with an extra key → ConnectionValidationError."""
        # Arrange — FullAction with extra key "extra"
        mock_db = AsyncMock(spec=TestDbManager)
        extra_resource = _MockResourceManager()

        action = FullAction()
        params = FullAction.Params(user_id="u1", amount=100.0)
        connections = {"db": mock_db, "extra": extra_resource}

        # Act & Assert - ConnectionValidationError indicating an extra key
        with pytest.raises(ConnectionValidationError, match="extra"):
            await machine.run(context, action, params, connections=connections)

    @pytest.mark.asyncio
    async def test_ping_action_without_connections_ok(self, machine, context) -> None:
        """PingAction via run() without connections → OK."""
        # Arrange - PingAction without @connection
        action = PingAction()
        params = PingAction.Params()

        # Act - run() without connections
        result = await machine.run(context, action, params)

        # Assert - the pipeline completed successfully
        assert result.message == "pong"
        assert result.message == "pong"
