# tests/resources/test_wrapper_sql_connection_manager.py
"""
Tests for WrapperSqlConnectionManager — a proxy wrapper that forbids transaction
management at nested levels.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

WrapperSqlConnectionManager is a proxy around a real SqlConnectionManager.
It is created automatically when connections are passed to child actions via
ToolsBox.run(). The wrapper forbids the child action from managing the resource
lifecycle (open, begin, commit, rollback) but allows executing queries (execute).
The rollup flag is inherited from the original manager.

═══════════════════════════════════════════════════════════════════════════════
SCENARIOS COVERED
═══════════════════════════════════════════════════════════════════════════════

Constructor:
    - Holds a reference to the original manager.
    - Inherits rollup from the original manager.

Transaction prohibition:
    - open() → TransactionProhibitedError.
    - begin() → TransactionProhibitedError.
    - commit() → TransactionProhibitedError.
    - rollback() → TransactionProhibitedError.

Execute delegation:
    - execute() delegates to the original manager.
    - execute() with parameters — parameters are forwarded.
    - execute() on original error — wraps in HandleError.

get_wrapper_class:
    - Returns WrapperSqlConnectionManager (for re-wrapping).
    - Synchronous method.

Double wrapping (nesting):
    - WrapperSqlConnectionManager is wrapped again via get_wrapper_class.
    - Double wrap forbids transactions.
    - Double wrap delegates execute to the original.

Integration with ToolsBox._wrap_connections:
    - _wrap_connections wraps the manager correctly.
    - Repeated _wrap_connections on an already wrapped manager works.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from action_machine.model.exceptions import HandleError, TransactionProhibitedError
from action_machine.resources.sql_connection_manager import SqlConnectionManager
from action_machine.resources.wrapper_sql_connection_manager import (
    WrapperSqlConnectionManager,
)

# ======================================================================
# Mock connection manager for tests
# ======================================================================

class MockConnectionManager(SqlConnectionManager):
    """
    Mock SqlConnectionManager for testing WrapperSqlConnectionManager.
    All methods are AsyncMock for call verification.
    """

    def __init__(self) -> None:
        self.open = AsyncMock()
        self.begin = AsyncMock()
        self.commit = AsyncMock()
        self.rollback = AsyncMock()
        self.execute = AsyncMock(return_value="query_result")

    async def open(self) -> None:
        pass  # overridden by AsyncMock in __init__

    async def begin(self) -> None:
        pass

    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        pass

    async def execute(self, query: str, params: tuple[Any, ...] | None = None) -> Any:
        pass

    def get_wrapper_class(self) -> type[SqlConnectionManager] | None:
        return WrapperSqlConnectionManager


# ======================================================================
# Fixtures
# ======================================================================

@pytest.fixture
def mock_manager() -> MockConnectionManager:
    """Mock connection manager."""
    return MockConnectionManager()


@pytest.fixture
def wrapper(mock_manager: MockConnectionManager) -> WrapperSqlConnectionManager:
    """WrapperSqlConnectionManager wrapping the mock manager."""
    return WrapperSqlConnectionManager(mock_manager)


@pytest.fixture
def double_wrapper(wrapper: WrapperSqlConnectionManager) -> WrapperSqlConnectionManager:
    """Double wrap — WrapperSqlConnectionManager around WrapperSqlConnectionManager."""
    return WrapperSqlConnectionManager(wrapper)


# ======================================================================
# TESTS: Constructor
# ======================================================================

class TestConstructor:
    """WrapperSqlConnectionManager is constructed successfully."""

    def test_creates_successfully(self, mock_manager: MockConnectionManager) -> None:
        """Instance is created without error."""
        w = WrapperSqlConnectionManager(mock_manager)
        assert w is not None

    def test_stores_original_manager(self, wrapper: WrapperSqlConnectionManager, mock_manager: MockConnectionManager) -> None:
        """Stores a reference to the original manager."""
        assert wrapper._connection_manager is mock_manager

    def test_inherits_rollup_from_original(self, mock_manager: MockConnectionManager) -> None:
        """rollup is inherited from the original manager."""
        mock_manager._rollup = True
        wrapper = WrapperSqlConnectionManager(mock_manager)
        assert wrapper.rollup is True

    def test_is_instance_of_sql_connection_manager(self, wrapper: WrapperSqlConnectionManager) -> None:
        """Is an instance of SqlConnectionManager."""
        assert isinstance(wrapper, SqlConnectionManager)


# ======================================================================
# TESTS: Transaction prohibition
# ======================================================================

class TestTransactionProhibited:
    """The wrapper forbids transaction management."""

    @pytest.mark.anyio
    async def test_open_raises_prohibited(self, wrapper: WrapperSqlConnectionManager) -> None:
        """open() raises TransactionProhibitedError."""
        with pytest.raises(TransactionProhibitedError, match="open is unavailable"):
            await wrapper.open()

    @pytest.mark.anyio
    async def test_commit_raises_prohibited(self, wrapper: WrapperSqlConnectionManager) -> None:
        """commit() raises TransactionProhibitedError."""
        with pytest.raises(TransactionProhibitedError, match="commit is unavailable"):
            await wrapper.commit()

    @pytest.mark.anyio
    async def test_rollback_raises_prohibited(self, wrapper: WrapperSqlConnectionManager) -> None:
        """rollback() raises TransactionProhibitedError."""
        with pytest.raises(TransactionProhibitedError, match="rollback is unavailable"):
            await wrapper.rollback()

    @pytest.mark.anyio
    async def test_begin_raises_prohibited(self, wrapper: WrapperSqlConnectionManager) -> None:
        """begin() raises TransactionProhibitedError."""
        with pytest.raises(TransactionProhibitedError, match="begin is unavailable"):
            await wrapper.begin()

    @pytest.mark.anyio
    async def test_open_does_not_call_original(self, wrapper: WrapperSqlConnectionManager, mock_manager: MockConnectionManager) -> None:
        """open() does not call the original manager."""
        with pytest.raises(TransactionProhibitedError):
            await wrapper.open()
        mock_manager.open.assert_not_called()

    @pytest.mark.anyio
    async def test_commit_does_not_call_original(self, wrapper: WrapperSqlConnectionManager, mock_manager: MockConnectionManager) -> None:
        """commit() does not call the original manager."""
        with pytest.raises(TransactionProhibitedError):
            await wrapper.commit()
        mock_manager.commit.assert_not_called()

    @pytest.mark.anyio
    async def test_rollback_does_not_call_original(self, wrapper: WrapperSqlConnectionManager, mock_manager: MockConnectionManager) -> None:
        """rollback() does not call the original manager."""
        with pytest.raises(TransactionProhibitedError):
            await wrapper.rollback()
        mock_manager.rollback.assert_not_called()

    @pytest.mark.anyio
    async def test_begin_does_not_call_original(self, wrapper: WrapperSqlConnectionManager, mock_manager: MockConnectionManager) -> None:
        """begin() does not call the original manager."""
        with pytest.raises(TransactionProhibitedError):
            await wrapper.begin()
        mock_manager.begin.assert_not_called()


# ======================================================================
# TESTS: Execute delegation
# ======================================================================

class TestExecuteDelegation:
    """execute() delegates to the original manager."""

    @pytest.mark.anyio
    async def test_execute_delegates_to_original(
        self, wrapper: WrapperSqlConnectionManager, mock_manager: MockConnectionManager,
    ) -> None:
        """execute() calls the original manager's execute."""
        result = await wrapper.execute("SELECT 1")
        mock_manager.execute.assert_called_once_with("SELECT 1", None)
        assert result == "query_result"

    @pytest.mark.anyio
    async def test_execute_passes_params(
        self, wrapper: WrapperSqlConnectionManager, mock_manager: MockConnectionManager,
    ) -> None:
        """execute() forwards parameters."""
        await wrapper.execute("SELECT * FROM users WHERE id = $1", (42,))
        mock_manager.execute.assert_called_once_with(
            "SELECT * FROM users WHERE id = $1", (42,)
        )

    @pytest.mark.anyio
    async def test_execute_wraps_error_in_handle_error(
        self, wrapper: WrapperSqlConnectionManager, mock_manager: MockConnectionManager,
    ) -> None:
        """execute() wraps the original error in HandleError."""
        mock_manager.execute.side_effect = RuntimeError("connection lost")

        with pytest.raises(HandleError, match="SQL execution error"):
            await wrapper.execute("SELECT 1")

    @pytest.mark.anyio
    async def test_execute_preserves_original_error_as_cause(
        self, wrapper: WrapperSqlConnectionManager, mock_manager: MockConnectionManager,
    ) -> None:
        """HandleError keeps the original error in __cause__."""
        original_error = RuntimeError("timeout")
        mock_manager.execute.side_effect = original_error

        with pytest.raises(HandleError) as exc_info:
            await wrapper.execute("SELECT 1")

        assert exc_info.value.__cause__ is original_error


# ======================================================================
# TESTS: get_wrapper_class
# ======================================================================

class TestGetWrapperClass:
    """get_wrapper_class() returns WrapperSqlConnectionManager."""

    def test_returns_wrapper_class(self, wrapper: WrapperSqlConnectionManager) -> None:
        """Returns WrapperSqlConnectionManager for re-wrapping."""
        result = wrapper.get_wrapper_class()
        assert result is WrapperSqlConnectionManager

    def test_is_synchronous(self, wrapper: WrapperSqlConnectionManager) -> None:
        """Method is synchronous — returns a class, not a coroutine."""
        result = wrapper.get_wrapper_class()
        assert isinstance(result, type)

    def test_returned_class_is_subclass_of_sql_connection_manager(self, wrapper: WrapperSqlConnectionManager) -> None:
        """Returned class is a subclass of SqlConnectionManager."""
        result = wrapper.get_wrapper_class()
        assert issubclass(result, SqlConnectionManager)


# ======================================================================
# TESTS: Double wrapping (nesting level 2+)
# ======================================================================

class TestDoubleWrapping:
    """WrapperSqlConnectionManager can be wrapped again correctly."""

    def test_double_wrapper_creates_successfully(self, wrapper: WrapperSqlConnectionManager) -> None:
        """Double wrap is created without error."""
        double = WrapperSqlConnectionManager(wrapper)
        assert double is not None

    def test_double_wrapper_stores_inner_wrapper(
        self, double_wrapper: WrapperSqlConnectionManager, wrapper: WrapperSqlConnectionManager,
    ) -> None:
        """Double wrap holds a reference to the inner wrapper."""
        assert double_wrapper._connection_manager is wrapper

    @pytest.mark.anyio
    async def test_double_wrapper_prohibits_open(self, double_wrapper: WrapperSqlConnectionManager) -> None:
        """Double wrap forbids open()."""
        with pytest.raises(TransactionProhibitedError):
            await double_wrapper.open()

    @pytest.mark.anyio
    async def test_double_wrapper_prohibits_commit(self, double_wrapper: WrapperSqlConnectionManager) -> None:
        """Double wrap forbids commit()."""
        with pytest.raises(TransactionProhibitedError):
            await double_wrapper.commit()

    @pytest.mark.anyio
    async def test_double_wrapper_prohibits_rollback(self, double_wrapper: WrapperSqlConnectionManager) -> None:
        """Double wrap forbids rollback()."""
        with pytest.raises(TransactionProhibitedError):
            await double_wrapper.rollback()

    @pytest.mark.anyio
    async def test_double_wrapper_prohibits_begin(self, double_wrapper: WrapperSqlConnectionManager) -> None:
        """Double wrap forbids begin()."""
        with pytest.raises(TransactionProhibitedError):
            await double_wrapper.begin()

    @pytest.mark.anyio
    async def test_double_wrapper_delegates_execute_to_original(
        self, double_wrapper: WrapperSqlConnectionManager, mock_manager: MockConnectionManager,
    ) -> None:
        """execute() through double wrap reaches the original manager."""
        result = await double_wrapper.execute("SELECT 1")
        mock_manager.execute.assert_called_once_with("SELECT 1", None)
        assert result == "query_result"

    @pytest.mark.anyio
    async def test_triple_wrapper_works(
        self, double_wrapper: WrapperSqlConnectionManager, mock_manager: MockConnectionManager,
    ) -> None:
        """Triple wrap also works — execute reaches the original."""
        triple = WrapperSqlConnectionManager(double_wrapper)
        result = await triple.execute("SELECT 42")
        mock_manager.execute.assert_called_once_with("SELECT 42", None)
        assert result == "query_result"


# ======================================================================
# TESTS: Integration with _wrap_connections
# ======================================================================

class TestWrapConnectionsIntegration:
    """
    Mimics ToolsBox._wrap_connections() logic — verifies
    WrapperSqlConnectionManager behaves in a realistic wrapping scenario.
    """

    @staticmethod
    def _wrap_connections(connections: dict | None) -> dict | None:
        """Copy of ToolsBox._wrap_connections logic for an isolated test."""
        if connections is None:
            return None
        wrapped = {}
        for key, connection in connections.items():
            wrapper_class = connection.get_wrapper_class()
            if wrapper_class is not None:
                wrapped[key] = wrapper_class(connection)
            else:
                wrapped[key] = connection
        return wrapped

    def test_wraps_mock_manager(self, mock_manager: MockConnectionManager) -> None:
        """Wraps MockConnectionManager in WrapperSqlConnectionManager."""
        connections = {"db": mock_manager}
        wrapped = self._wrap_connections(connections)

        assert "db" in wrapped
        assert isinstance(wrapped["db"], WrapperSqlConnectionManager)
        assert wrapped["db"]._connection_manager is mock_manager

    def test_wraps_wrapper_again(self, wrapper: WrapperSqlConnectionManager) -> None:
        """Re-wrapping WrapperSqlConnectionManager works."""
        connections = {"db": wrapper}
        wrapped = self._wrap_connections(connections)

        assert isinstance(wrapped["db"], WrapperSqlConnectionManager)
        assert wrapped["db"]._connection_manager is wrapper

    @pytest.mark.anyio
    async def test_wrapped_execute_works(self, mock_manager: MockConnectionManager) -> None:
        """execute() through the wrapped manager works."""
        connections = {"db": mock_manager}
        wrapped = self._wrap_connections(connections)

        result = await wrapped["db"].execute("INSERT INTO orders VALUES ($1)", (1,))
        mock_manager.execute.assert_called_once_with(
            "INSERT INTO orders VALUES ($1)", (1,)
        )
        assert result == "query_result"

    @pytest.mark.anyio
    async def test_wrapped_prohibits_transactions(self, mock_manager: MockConnectionManager) -> None:
        """Wrapped manager forbids transactions."""
        connections = {"db": mock_manager}
        wrapped = self._wrap_connections(connections)

        with pytest.raises(TransactionProhibitedError):
            await wrapped["db"].open()

        with pytest.raises(TransactionProhibitedError):
            await wrapped["db"].commit()

        with pytest.raises(TransactionProhibitedError):
            await wrapped["db"].rollback()

        with pytest.raises(TransactionProhibitedError):
            await wrapped["db"].begin()

    @pytest.mark.anyio
    async def test_double_wrap_execute_reaches_original(self, mock_manager: MockConnectionManager) -> None:
        """Double wrap via _wrap_connections — execute reaches the original."""
        # First wrap (parent → child)
        wrapped_1 = self._wrap_connections({"db": mock_manager})
        # Second wrap (child → grandchild)
        wrapped_2 = self._wrap_connections({"db": wrapped_1["db"]})

        result = await wrapped_2["db"].execute("SELECT 1")
        mock_manager.execute.assert_called_once_with("SELECT 1", None)
        assert result == "query_result"

    def test_none_connections_returns_none(self) -> None:
        """None connections → None."""
        assert self._wrap_connections(None) is None

    def test_empty_connections_returns_empty(self) -> None:
        """Empty dict → empty dict."""
        result = self._wrap_connections({})
        assert result == {}
