# tests/adapters/test_base_adapter.py
"""
Unit tests for ``BaseAdapter`` — the abstract base for protocol adapters.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Assert constructor validation (machine type, mandatory ``auth_coordinator``),
property surfaces (including optional ``gate_coordinator`` override and
``connections_factory``), fluent ``_add_route``, and that the abstract class
cannot be instantiated without a concrete ``build()``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    pytest
      |
      v
    _TestAdapter (concrete ``build()`` no-op)
      |
      v
    BaseAdapter[R]  --stores-->  machine, auth_coordinator,
                                 gate_coordinator (default / override),
                                 connections_factory, _routes
      |
      v
    _add_route(record)  ->  append + return self (fluent)

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``machine`` must be a real ``ActionProductMachine`` instance (mocks are rejected).
- ``auth_coordinator`` must not be ``None``.
- ``routes`` mirrors registration order; initial list is empty.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    uv run pytest tests/adapters/test_base_adapter.py -q

Edge case: explicit ``gate_coordinator`` replaces ``machine.gate_coordinator`` on
the adapter without mutating the machine.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Assertions match substring patterns in ``TypeError`` messages from
  ``BaseAdapter.__init__``; message tweaks in production require test updates.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Regression tests for adapter base state and validation.
CONTRACT: TypeError on bad ctor args; fluent route list; abstract class guard.
INVARIANTS: ``_TestAdapter`` is the only concrete subclass used here.
═══════════════════════════════════════════════════════════════════════════════
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from action_machine.adapters.base_adapter import BaseAdapter
from action_machine.adapters.base_route_record import BaseRouteRecord
from action_machine.graph.gate_coordinator import GateCoordinator
from action_machine.runtime.machines.action_product_machine import ActionProductMachine

# ─────────────────────────────────────────────────────────────────────────────
# Concrete subclass — ``BaseAdapter`` is abstract and cannot be instantiated
# directly. This minimal subclass implements ``build()`` as a no-op.
# ─────────────────────────────────────────────────────────────────────────────


class _TestAdapter(BaseAdapter[BaseRouteRecord]):
    """Minimal concrete adapter used only to exercise ``BaseAdapter`` behavior."""

    def build(self):
        """No-op ``build`` — satisfies the abstract contract for tests."""
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _make_machine() -> ActionProductMachine:
    """Return a minimal ``ActionProductMachine`` in ``test`` mode."""
    return ActionProductMachine(mode="test")


def _make_auth() -> AsyncMock:
    """Return a mock ``auth_coordinator`` with ``process`` stubbed."""
    auth = AsyncMock()
    auth.process.return_value = None
    return auth


# ═════════════════════════════════════════════════════════════════════════════
# Abstract class guard
# ═════════════════════════════════════════════════════════════════════════════


class TestAbstractBaseAdapter:
    """``BaseAdapter`` stays abstract until ``build()`` is implemented."""

    def test_cannot_instantiate_without_concrete_build(self) -> None:
        """Direct ``BaseAdapter`` construction raises (abstract ``build()``)."""
        with pytest.raises(TypeError, match="abstract"):
            BaseAdapter(
                machine=_make_machine(),
                auth_coordinator=_make_auth(),
            )


# ═════════════════════════════════════════════════════════════════════════════
# Constructor validation
# ═════════════════════════════════════════════════════════════════════════════


class TestConstructorValidation:
    """Constructor rejects invalid ``machine`` and missing ``auth_coordinator``."""

    def test_rejects_none_auth_coordinator(self) -> None:
        """``auth_coordinator=None`` raises ``TypeError`` mentioning auth."""
        machine = _make_machine()

        with pytest.raises(TypeError, match="auth_coordinator"):
            _TestAdapter(machine=machine, auth_coordinator=None)

    def test_rejects_non_machine(self) -> None:
        """A non-``ActionProductMachine`` ``machine`` raises ``TypeError``."""
        with pytest.raises(TypeError, match="ActionProductMachine"):
            _TestAdapter(machine="not_a_machine", auth_coordinator=_make_auth())

    def test_rejects_mock_as_machine(self) -> None:
        """``MagicMock`` is not accepted as ``machine`` — type must be concrete."""
        with pytest.raises(TypeError, match="ActionProductMachine"):
            _TestAdapter(machine=MagicMock(), auth_coordinator=_make_auth())

    def test_accepts_valid_arguments(self) -> None:
        """Valid ``machine`` + ``auth_coordinator`` constructs without error."""
        machine = _make_machine()
        auth = _make_auth()

        adapter = _TestAdapter(machine=machine, auth_coordinator=auth)

        assert adapter.machine is machine
        assert adapter.auth_coordinator is auth


# ═════════════════════════════════════════════════════════════════════════════
# Properties
# ═════════════════════════════════════════════════════════════════════════════


class TestProperties:
    """Read-only properties mirror constructor inputs and defaults."""

    def test_machine_property(self) -> None:
        """``machine`` returns the instance passed into the constructor."""
        machine = _make_machine()
        adapter = _TestAdapter(machine=machine, auth_coordinator=_make_auth())
        assert adapter.machine is machine

    def test_auth_coordinator_property(self) -> None:
        """``auth_coordinator`` returns the object passed into the constructor."""
        auth = _make_auth()
        adapter = _TestAdapter(machine=_make_machine(), auth_coordinator=auth)
        assert adapter.auth_coordinator is auth

    def test_connections_factory_defaults_to_none(self) -> None:
        """Omitted ``connections_factory`` is ``None``."""
        adapter = _TestAdapter(machine=_make_machine(), auth_coordinator=_make_auth())
        assert adapter.connections_factory is None

    def test_connections_factory_stored(self) -> None:
        """Explicit ``connections_factory`` is stored and exposed."""
        factory = MagicMock()
        adapter = _TestAdapter(
            machine=_make_machine(),
            auth_coordinator=_make_auth(),
            connections_factory=factory,
        )
        assert adapter.connections_factory is factory

    def test_gate_coordinator_defaults_to_machine(self) -> None:
        """Omitted ``gate_coordinator`` falls back to ``machine.gate_coordinator``."""
        machine = _make_machine()
        adapter = _TestAdapter(machine=machine, auth_coordinator=_make_auth())
        assert adapter.gate_coordinator is machine.gate_coordinator

    def test_gate_coordinator_explicit_override(self) -> None:
        """Explicit ``gate_coordinator`` overrides the machine’s coordinator."""
        machine = _make_machine()
        alt = MagicMock(spec=GateCoordinator)
        adapter = _TestAdapter(
            machine=machine,
            auth_coordinator=_make_auth(),
            gate_coordinator=alt,
        )
        assert adapter.gate_coordinator is alt

    def test_routes_starts_empty(self) -> None:
        """``routes`` is empty immediately after construction."""
        adapter = _TestAdapter(machine=_make_machine(), auth_coordinator=_make_auth())
        assert adapter.routes == []


# ═════════════════════════════════════════════════════════════════════════════
# Fluent ``_add_route``
# ═════════════════════════════════════════════════════════════════════════════


class TestAddRoute:
    """``_add_route`` appends records and returns ``self`` for chaining."""

    def test_returns_self(self) -> None:
        """``_add_route`` returns the same adapter instance."""
        adapter = _TestAdapter(machine=_make_machine(), auth_coordinator=_make_auth())
        sentinel = MagicMock()

        result = adapter._add_route(sentinel)

        assert result is adapter

    def test_appends_record(self) -> None:
        """Each ``_add_route`` call appends to ``routes`` in order."""
        adapter = _TestAdapter(machine=_make_machine(), auth_coordinator=_make_auth())
        r1 = MagicMock()
        r2 = MagicMock()

        adapter._add_route(r1)
        adapter._add_route(r2)

        assert len(adapter.routes) == 2
        assert adapter.routes[0] is r1
        assert adapter.routes[1] is r2

    def test_fluent_chain(self) -> None:
        """Multiple ``_add_route`` calls chain fluently."""
        adapter = _TestAdapter(machine=_make_machine(), auth_coordinator=_make_auth())
        r1 = MagicMock()
        r2 = MagicMock()

        result = adapter._add_route(r1)._add_route(r2)

        assert result is adapter
        assert len(adapter.routes) == 2
