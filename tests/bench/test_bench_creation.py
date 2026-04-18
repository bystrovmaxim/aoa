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
    GraphCoordinator (default) + _prepare_all_mocks(mocks)
              |
              v
    _prepared_mocks  ready for ``box.resolve()`` during runs

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Default bench is immediately usable for simple actions without extra mocks.
- ``unittest.mock.Mock`` / ``AsyncMock`` must not be wrapped solely for being
  callable.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    uv run pytest tests/bench/test_bench_creation.py -q

Edge case: ``AsyncMock(spec=PaymentService)`` stays a raw mock in
``_prepared_mocks``.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Inspects private ``_prepared_mocks`` to verify preparation without running the
  full machine.

═══════════════════════════════════════════════════════════════════════════════
"""

from unittest.mock import AsyncMock

from action_machine.graph.graph_coordinator import GraphCoordinator
from action_machine.testing import TestBench
from tests.scenarios.domain_model import PaymentService


class TestWithoutArguments:
    """``TestBench()`` yields usable defaults."""

    def test_coordinator_is_graph_coordinator(self) -> None:
        """Default ``coordinator`` is a built ``GraphCoordinator``."""
        b = TestBench()

        assert isinstance(b.coordinator, GraphCoordinator)

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
        """Plain ``PaymentService`` instance is stored unchanged for direct calls."""
        payment = PaymentService()

        b = TestBench(mocks={PaymentService: payment})

        assert b._prepared_mocks[PaymentService] is payment

    def test_async_mock_stored_as_is(self) -> None:
        """``AsyncMock`` is recognized as ``Mock`` before callable wrapping."""
        mock = AsyncMock(spec=PaymentService)

        b = TestBench(mocks={PaymentService: mock})

        assert b._prepared_mocks[PaymentService] is mock
