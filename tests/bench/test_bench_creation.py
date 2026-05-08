# tests/bench/test_bench_creation.py
"""
Tests for constructing ``TestBench`` — stored parameters and defaults.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Assert default coordinator type, empty ``mocks`` / ``plugins``, and that
``_prepare_mock`` rules apply at construction: plain service objects and
``AsyncMock`` instances are stored as-is (not wrapped in ``MockAction``).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    TestBench(**kwargs)
              |
              v
    built ``NodeGraphCoordinator`` (default) + _prepare_all_mocks(mocks)
              |
              v
    _prepared_mocks  ready for ``box.resolve()`` during runs

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Default bench is immediately usable for simple actions without extra mocks.
- ``unittest.mock.Mock`` / ``AsyncMock`` must not be wrapped solely for being
  callable.

"""

from unittest.mock import AsyncMock

from action_machine.testing import TestBench
from graph.node_graph_coordinator import NodeGraphCoordinator
from tests.scenarios.domain_model.services import PaymentService, PaymentServiceResource


class TestWithoutArguments:
    """``TestBench()`` yields usable defaults."""

    def test_coordinator_is_node_graph_coordinator(self) -> None:
        """Default ``coordinator`` is a built ``NodeGraphCoordinator``."""
        b = TestBench()

        assert isinstance(b.coordinator, NodeGraphCoordinator)

    def test_mocks_empty_by_default(self) -> None:
        """``mocks`` starts empty so dependency-free actions need no setup."""
        b = TestBench()

        assert b.mocks == {}

    def test_plugins_empty_by_default(self) -> None:
        """``plugins`` starts empty; callers attach plugins explicitly."""
        b = TestBench()

        assert b.plugins == []


class TestWithMocks:
    """User-supplied mocks are normalized once at construction."""

    def test_regular_object_stored_as_is(self) -> None:
        """Plain ``PaymentServiceResource`` instance is stored unchanged for direct calls."""
        payment = PaymentServiceResource(PaymentService())

        b = TestBench(mocks={PaymentServiceResource: payment})

        assert b._prepared_mocks[PaymentServiceResource] is payment

    def test_async_mock_stored_as_is(self) -> None:
        """``AsyncMock`` is recognized as ``Mock`` before callable wrapping."""
        mock = AsyncMock(spec=PaymentService)

        b = TestBench(mocks={PaymentServiceResource: mock})

        assert b._prepared_mocks[PaymentServiceResource] is mock
