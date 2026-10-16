# tests/resources/test_wrapper_sql_resource.py
"""
Tests for WrapperSqlResource — a proxy wrapper that forbids transaction
management at nested levels.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

WrapperSqlResource is a proxy around a ``ProtocolSqlResource``
implementation (typically ``SqlResource``). It is created when
connections are passed to child actions via ToolsBox.run(). The wrapper forbids
the child action from managing the resource lifecycle (open, begin, commit,
rollback, close) and offers it **nothing** to run a statement with: the query
surface left the contract, and the proxy has no member of its own to delegate.
``rollup`` is delegated to the wrapped manager.

═══════════════════════════════════════════════════════════════════════════════
SCENARIOS COVERED
═══════════════════════════════════════════════════════════════════════════════

Constructor:
    - Holds a reference to the original manager.
    - ``rollup`` reads through to the original manager.

Transaction prohibition:
    - open() → TransactionProhibitedError.
    - begin() → TransactionProhibitedError.
    - commit() → TransactionProhibitedError.
    - rollback() → TransactionProhibitedError.

No query member:
    - the proxy exposes no ``execute``, ``_execute`` or ``_fetchrow``.
    - the owner's own members are not auto-delegated.

get_wrapper_class:
    - Returns WrapperSqlResource (for re-wrapping).
    - Synchronous method.

Double wrapping (nesting):
    - WrapperSqlResource is wrapped again via get_wrapper_class.
    - Double wrap forbids transactions.
    - Double wrap exposes no query member either.

Integration with ToolsBox._wrap_connections:
    - _wrap_connections wraps the manager correctly.
    - Repeated _wrap_connections on an already wrapped manager works.
    - What the framework hands a child action is the same absence.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.exceptions import TransactionProhibitedError
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.resources.sql import ProtocolSqlResource, SqlResource, WrapperSqlResource


class _WrapperSqlResourceTestDomain(BaseDomain):
    name = "wrapper_sql_resource_test"
    description = "Domain for wrapper SQL resource-layer tests."


def meta(description: str, domain: type[BaseDomain]):
    """Test-local metadata decorator matching the graph metadata contract."""

    def decorator(cls):
        cls._meta_info = {"description": description, "domain": domain}
        return cls

    return decorator


# ======================================================================
# Mock connection manager for tests
# ======================================================================


@meta(description="Wrapper SQL resource mock manager", domain=_WrapperSqlResourceTestDomain)
class MockConnectionManager(SqlResource):
    """
    Mock SqlResource for testing WrapperSqlResource.
    All methods are AsyncMock for call verification.
    """

    def __init__(self) -> None:
        self.open = AsyncMock()
        self.begin = AsyncMock()
        self.commit = AsyncMock()
        self.rollback = AsyncMock()

    async def open(self) -> None:
        pass  # overridden by AsyncMock in __init__

    async def begin(self) -> None:
        pass

    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        pass

    def get_wrapper_class(self) -> type[BaseResource] | None:
        return WrapperSqlResource


# ======================================================================
# Fixtures
# ======================================================================


@pytest.fixture
def mock_manager() -> MockConnectionManager:
    """Mock connection manager."""
    return MockConnectionManager()


@pytest.fixture
def wrapper(mock_manager: MockConnectionManager) -> WrapperSqlResource:
    """WrapperSqlResource wrapping the mock manager."""
    return WrapperSqlResource(mock_manager)


@pytest.fixture
def double_wrapper(wrapper: WrapperSqlResource) -> WrapperSqlResource:
    """Double wrap — WrapperSqlResource around WrapperSqlResource."""
    return WrapperSqlResource(wrapper)


# ======================================================================
# TESTS: Constructor
# ======================================================================


class TestConstructor:
    """WrapperSqlResource is constructed successfully."""

    def test_creates_successfully(self, mock_manager: MockConnectionManager) -> None:
        """Instance is created without error."""
        w = WrapperSqlResource(mock_manager)
        assert w is not None

    def test_stores_original_manager(self, wrapper: WrapperSqlResource, mock_manager: MockConnectionManager) -> None:
        """Stores a reference to the original manager."""
        assert wrapper._connection_manager is mock_manager

    def test_inherits_rollup_from_original(self, mock_manager: MockConnectionManager) -> None:
        """rollup is delegated to the original manager."""
        mock_manager._rollup = True
        wrapper = WrapperSqlResource(mock_manager)
        assert wrapper.rollup is True

    @pytest.mark.asyncio
    async def test_check_rollup_support_is_delegated(
        self,
        wrapper: WrapperSqlResource,
        mock_manager: MockConnectionManager,
    ) -> None:
        """check_rollup_support() forwards to the wrapped manager."""
        assert await wrapper.check_rollup_support() == await mock_manager.check_rollup_support()

    def test_is_instance_of_protocol_sql_resource(
        self,
        wrapper: WrapperSqlResource,
    ) -> None:
        """Is an instance of ProtocolSqlResource (not SqlResource)."""
        assert isinstance(wrapper, ProtocolSqlResource)
        assert not isinstance(wrapper, SqlResource)

    def test_acquire_is_not_exposed(self, wrapper: WrapperSqlResource) -> None:
        """A nested action has no way to take a connection of its own from the proxy."""
        assert not hasattr(wrapper, "acquire")


# ======================================================================
# TESTS: Transaction prohibition
# ======================================================================


class TestTransactionProhibited:
    """The wrapper forbids transaction management."""

    @pytest.mark.anyio
    async def test_open_raises_prohibited(self, wrapper: WrapperSqlResource) -> None:
        """open() raises TransactionProhibitedError."""
        with pytest.raises(TransactionProhibitedError, match="open is unavailable"):
            await wrapper.open()

    @pytest.mark.anyio
    async def test_commit_raises_prohibited(self, wrapper: WrapperSqlResource) -> None:
        """commit() raises TransactionProhibitedError."""
        with pytest.raises(TransactionProhibitedError, match="commit is unavailable"):
            await wrapper.commit()

    @pytest.mark.anyio
    async def test_close_raises_prohibited(self, wrapper: WrapperSqlResource) -> None:
        """close() raises TransactionProhibitedError: a nested action does not close what it does not own."""
        with pytest.raises(TransactionProhibitedError, match="close is unavailable"):
            await wrapper.close()

    @pytest.mark.anyio
    async def test_context_manager_is_refused(self, wrapper: WrapperSqlResource) -> None:
        """Entering the proxy as a context manager is refused, on both sides."""
        with pytest.raises(TransactionProhibitedError, match="context manager is unavailable"):
            async with wrapper:
                pass

    @pytest.mark.anyio
    async def test_rollback_raises_prohibited(self, wrapper: WrapperSqlResource) -> None:
        """rollback() raises TransactionProhibitedError."""
        with pytest.raises(TransactionProhibitedError, match="rollback is unavailable"):
            await wrapper.rollback()

    @pytest.mark.anyio
    async def test_begin_raises_prohibited(self, wrapper: WrapperSqlResource) -> None:
        """begin() raises TransactionProhibitedError."""
        with pytest.raises(TransactionProhibitedError, match="begin is unavailable"):
            await wrapper.begin()

    @pytest.mark.anyio
    async def test_open_does_not_call_original(
        self, wrapper: WrapperSqlResource, mock_manager: MockConnectionManager
    ) -> None:
        """open() does not call the original manager."""
        with pytest.raises(TransactionProhibitedError):
            await wrapper.open()
        mock_manager.open.assert_not_called()

    @pytest.mark.anyio
    async def test_commit_does_not_call_original(
        self, wrapper: WrapperSqlResource, mock_manager: MockConnectionManager
    ) -> None:
        """commit() does not call the original manager."""
        with pytest.raises(TransactionProhibitedError):
            await wrapper.commit()
        mock_manager.commit.assert_not_called()

    @pytest.mark.anyio
    async def test_rollback_does_not_call_original(
        self, wrapper: WrapperSqlResource, mock_manager: MockConnectionManager
    ) -> None:
        """rollback() does not call the original manager."""
        with pytest.raises(TransactionProhibitedError):
            await wrapper.rollback()
        mock_manager.rollback.assert_not_called()

    @pytest.mark.anyio
    async def test_begin_does_not_call_original(
        self, wrapper: WrapperSqlResource, mock_manager: MockConnectionManager
    ) -> None:
        """begin() does not call the original manager."""
        with pytest.raises(TransactionProhibitedError):
            await wrapper.begin()
        mock_manager.begin.assert_not_called()


# ======================================================================
# TESTS: No query member on the proxy
# ======================================================================


class TestNoQueryMember:
    """The proxy offers nothing to run a statement with — absence, not a refusal (FR-011, FR-012)."""

    def test_the_proxy_exposes_no_query_member(self, wrapper: WrapperSqlResource) -> None:
        """Neither the removed public member nor a protected helper is reachable on the proxy."""
        for member in ("execute", "_execute", "_fetchrow", "_require_connection"):
            assert not hasattr(wrapper, member), member

    def test_the_proxy_still_satisfies_the_contract(self, wrapper: WrapperSqlResource) -> None:
        """The absence does not cost the contract: what remains is what it answers."""
        assert isinstance(wrapper, ProtocolSqlResource)

    def test_the_owner_is_not_reached_for_a_statement(
        self,
        wrapper: WrapperSqlResource,
        mock_manager: MockConnectionManager,
    ) -> None:
        """The proxy holds the owner, and still delegates no statement to it."""
        assert wrapper._connection_manager is mock_manager
        assert not hasattr(wrapper, "execute")


# ======================================================================
# TESTS: get_wrapper_class
# ======================================================================


class TestGetWrapperClass:
    """get_wrapper_class() returns WrapperSqlResource."""

    def test_returns_wrapper_class(self, wrapper: WrapperSqlResource) -> None:
        """Returns WrapperSqlResource for re-wrapping."""
        result = wrapper.get_wrapper_class()
        assert result is WrapperSqlResource

    def test_is_synchronous(self, wrapper: WrapperSqlResource) -> None:
        """Method is synchronous — returns a class, not a coroutine."""
        result = wrapper.get_wrapper_class()
        assert isinstance(result, type)

    def test_returned_class_is_wrapper_and_resource_manager(
        self,
        wrapper: WrapperSqlResource,
    ) -> None:
        """Returned class is WrapperSqlResource (Protocol forbids issubclass here)."""
        result = wrapper.get_wrapper_class()
        assert result is not None
        assert result is WrapperSqlResource
        assert issubclass(result, BaseResource)


# ======================================================================
# TESTS: Double wrapping (nesting level 2+)
# ======================================================================


class TestDoubleWrapping:
    """WrapperSqlResource can be wrapped again correctly."""

    def test_double_wrapper_creates_successfully(self, wrapper: WrapperSqlResource) -> None:
        """Double wrap is created without error."""
        double = WrapperSqlResource(wrapper)
        assert double is not None

    def test_double_wrapper_stores_inner_wrapper(
        self,
        double_wrapper: WrapperSqlResource,
        wrapper: WrapperSqlResource,
    ) -> None:
        """Double wrap holds a reference to the inner wrapper."""
        assert double_wrapper._connection_manager is wrapper

    @pytest.mark.anyio
    async def test_double_wrapper_prohibits_open(self, double_wrapper: WrapperSqlResource) -> None:
        """Double wrap forbids open()."""
        with pytest.raises(TransactionProhibitedError):
            await double_wrapper.open()

    @pytest.mark.anyio
    async def test_double_wrapper_prohibits_commit(self, double_wrapper: WrapperSqlResource) -> None:
        """Double wrap forbids commit()."""
        with pytest.raises(TransactionProhibitedError):
            await double_wrapper.commit()

    @pytest.mark.anyio
    async def test_double_wrapper_prohibits_rollback(self, double_wrapper: WrapperSqlResource) -> None:
        """Double wrap forbids rollback()."""
        with pytest.raises(TransactionProhibitedError):
            await double_wrapper.rollback()

    @pytest.mark.anyio
    async def test_double_wrapper_prohibits_begin(self, double_wrapper: WrapperSqlResource) -> None:
        """Double wrap forbids begin()."""
        with pytest.raises(TransactionProhibitedError):
            await double_wrapper.begin()

    def test_double_wrapper_exposes_no_query_member(
        self,
        double_wrapper: WrapperSqlResource,
    ) -> None:
        """A second wrap brings no query member back."""
        for member in ("execute", "_execute", "_fetchrow"):
            assert not hasattr(double_wrapper, member), member

    @pytest.mark.anyio
    async def test_triple_wrapper_refuses_the_lifecycle_and_exposes_no_query_member(
        self,
        double_wrapper: WrapperSqlResource,
    ) -> None:
        """A third wrap behaves as the first: the lifecycle refused, no statement reachable (NA-2.1)."""
        triple = WrapperSqlResource(double_wrapper)

        for member in ("execute", "_execute", "_fetchrow"):
            assert not hasattr(triple, member), member
        with pytest.raises(TransactionProhibitedError):
            await triple.begin()


# ======================================================================
# TESTS: Integration with _wrap_connections
# ======================================================================


class TestWrapConnectionsIntegration:
    """
    Mimics ToolsBox._wrap_connections() logic — verifies
    WrapperSqlResource behaves in a realistic wrapping scenario.
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
        """Wraps MockConnectionManager in WrapperSqlResource."""
        connections = {"db": mock_manager}
        wrapped = self._wrap_connections(connections)

        assert "db" in wrapped
        assert isinstance(wrapped["db"], WrapperSqlResource)
        assert wrapped["db"]._connection_manager is mock_manager

    def test_wraps_wrapper_again(self, wrapper: WrapperSqlResource) -> None:
        """Re-wrapping WrapperSqlResource works."""
        connections = {"db": wrapper}
        wrapped = self._wrap_connections(connections)

        assert isinstance(wrapped["db"], WrapperSqlResource)
        assert wrapped["db"]._connection_manager is wrapper

    def test_the_wrapped_proxy_exposes_no_query_member(self, mock_manager: MockConnectionManager) -> None:
        """What _wrap_connections hands a child action has nothing to run a statement with."""
        connections = {"db": mock_manager}
        wrapped = self._wrap_connections(connections)

        assert not hasattr(wrapped["db"], "execute")

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

    def test_double_wrap_exposes_no_query_member(self, mock_manager: MockConnectionManager) -> None:
        """Twice through _wrap_connections, the proxy a grandchild receives is the same absence."""
        # First wrap (parent → child)
        wrapped_1 = self._wrap_connections({"db": mock_manager})
        # Second wrap (child → grandchild)
        wrapped_2 = self._wrap_connections({"db": wrapped_1["db"]})

        assert not hasattr(wrapped_2["db"], "execute")

    def test_none_connections_returns_none(self) -> None:
        """None connections → None."""
        assert self._wrap_connections(None) is None

    def test_empty_connections_returns_empty(self) -> None:
        """Empty dict → empty dict."""
        result = self._wrap_connections({})
        assert result == {}
