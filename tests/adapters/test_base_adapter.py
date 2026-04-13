# tests/adapters/test_base_adapter.py
"""
Tests for BaseAdapter — the abstract base class for all protocol adapters.

BaseAdapter[R] stores the machine, auth_coordinator, connections_factory,
and a list of route records. It enforces mandatory auth_coordinator (no None
allowed) and validates that machine is an ActionProductMachine instance.
The _add_route method provides a fluent API by returning self.

Scenarios covered:
    - Constructor rejects None auth_coordinator with TypeError.
    - Constructor rejects non-ActionProductMachine machine with TypeError.
    - Constructor accepts valid machine + auth_coordinator.
    - Properties expose machine, auth_coordinator, connections_factory, routes.
    - _add_route appends a record and returns self (fluent).
    - routes starts empty.
    - connections_factory defaults to None.
    - build() is abstract — cannot be called on BaseAdapter directly.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from action_machine.adapters.base_adapter import BaseAdapter
from action_machine.adapters.base_route_record import BaseRouteRecord
from action_machine.graph.gate_coordinator import GateCoordinator
from action_machine.runtime.machines.action_product_machine import ActionProductMachine

# ─────────────────────────────────────────────────────────────────────────────
# Concrete subclass for testing — BaseAdapter is abstract and cannot be
# instantiated directly. This minimal subclass implements build() as a no-op.
# ─────────────────────────────────────────────────────────────────────────────


class _TestAdapter(BaseAdapter[BaseRouteRecord]):
    """Minimal concrete adapter for testing BaseAdapter behavior."""

    def build(self):
        """No-op build — returns None. Only needed to satisfy the abstract contract."""
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _make_machine() -> ActionProductMachine:
    """Create a minimal ActionProductMachine for adapter tests."""
    return ActionProductMachine(mode="test")


def _make_auth() -> AsyncMock:
    """Create a mock auth_coordinator with a process method."""
    auth = AsyncMock()
    auth.process.return_value = None
    return auth


# ═════════════════════════════════════════════════════════════════════════════
# Constructor validation
# ═════════════════════════════════════════════════════════════════════════════


class TestConstructorValidation:
    """Verify that BaseAdapter enforces mandatory parameters at construction time."""

    def test_rejects_none_auth_coordinator(self) -> None:
        """Passing auth_coordinator=None raises TypeError with guidance message."""
        machine = _make_machine()

        with pytest.raises(TypeError, match="auth_coordinator"):
            _TestAdapter(machine=machine, auth_coordinator=None)

    def test_rejects_non_machine(self) -> None:
        """Passing a non-ActionProductMachine object as machine raises TypeError."""
        with pytest.raises(TypeError, match="ActionProductMachine"):
            _TestAdapter(machine="not_a_machine", auth_coordinator=_make_auth())

    def test_rejects_mock_as_machine(self) -> None:
        """Even a MagicMock is rejected — must be a real ActionProductMachine."""
        with pytest.raises(TypeError, match="ActionProductMachine"):
            _TestAdapter(machine=MagicMock(), auth_coordinator=_make_auth())

    def test_accepts_valid_arguments(self) -> None:
        """Valid machine + auth_coordinator creates the adapter without error."""
        machine = _make_machine()
        auth = _make_auth()

        adapter = _TestAdapter(machine=machine, auth_coordinator=auth)

        assert adapter.machine is machine
        assert adapter.auth_coordinator is auth


# ═════════════════════════════════════════════════════════════════════════════
# Properties
# ═════════════════════════════════════════════════════════════════════════════


class TestProperties:
    """Verify read-only properties expose internal state correctly."""

    def test_machine_property(self) -> None:
        """machine property returns the ActionProductMachine passed to constructor."""
        machine = _make_machine()
        adapter = _TestAdapter(machine=machine, auth_coordinator=_make_auth())
        assert adapter.machine is machine

    def test_auth_coordinator_property(self) -> None:
        """auth_coordinator property returns the coordinator passed to constructor."""
        auth = _make_auth()
        adapter = _TestAdapter(machine=_make_machine(), auth_coordinator=auth)
        assert adapter.auth_coordinator is auth

    def test_connections_factory_defaults_to_none(self) -> None:
        """When not provided, connections_factory is None."""
        adapter = _TestAdapter(machine=_make_machine(), auth_coordinator=_make_auth())
        assert adapter.connections_factory is None

    def test_connections_factory_stored(self) -> None:
        """Explicitly passed connections_factory is stored and returned."""
        factory = MagicMock()
        adapter = _TestAdapter(
            machine=_make_machine(),
            auth_coordinator=_make_auth(),
            connections_factory=factory,
        )
        assert adapter.connections_factory is factory

    def test_gate_coordinator_defaults_to_machine(self) -> None:
        """When omitted, gate_coordinator matches machine.gate_coordinator."""
        machine = _make_machine()
        adapter = _TestAdapter(machine=machine, auth_coordinator=_make_auth())
        assert adapter.gate_coordinator is machine.gate_coordinator

    def test_gate_coordinator_explicit_override(self) -> None:
        """Optional gate_coordinator replaces the machine's coordinator reference."""
        machine = _make_machine()
        alt = MagicMock(spec=GateCoordinator)
        adapter = _TestAdapter(
            machine=machine,
            auth_coordinator=_make_auth(),
            gate_coordinator=alt,
        )
        assert adapter.gate_coordinator is alt

    def test_routes_starts_empty(self) -> None:
        """routes list is empty immediately after construction."""
        adapter = _TestAdapter(machine=_make_machine(), auth_coordinator=_make_auth())
        assert adapter.routes == []


# ═════════════════════════════════════════════════════════════════════════════
# Fluent _add_route
# ═════════════════════════════════════════════════════════════════════════════


class TestAddRoute:
    """Verify _add_route appends records and supports fluent chaining."""

    def test_returns_self(self) -> None:
        """_add_route returns the same adapter instance for fluent chaining."""
        adapter = _TestAdapter(machine=_make_machine(), auth_coordinator=_make_auth())
        sentinel = MagicMock()

        result = adapter._add_route(sentinel)

        assert result is adapter

    def test_appends_record(self) -> None:
        """Each _add_route call appends the record to routes."""
        adapter = _TestAdapter(machine=_make_machine(), auth_coordinator=_make_auth())
        r1 = MagicMock()
        r2 = MagicMock()

        adapter._add_route(r1)
        adapter._add_route(r2)

        assert len(adapter.routes) == 2
        assert adapter.routes[0] is r1
        assert adapter.routes[1] is r2

    def test_fluent_chain(self) -> None:
        """Multiple _add_route calls can be chained."""
        adapter = _TestAdapter(machine=_make_machine(), auth_coordinator=_make_auth())
        r1 = MagicMock()
        r2 = MagicMock()

        result = adapter._add_route(r1)._add_route(r2)

        assert result is adapter
        assert len(adapter.routes) == 2
