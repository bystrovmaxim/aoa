# tests/bench/test_bench_run_aspect.py
"""
Tests for ``TestBench.run_aspect()`` — run a single regular aspect.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Cover isolated aspect execution with manual state: first aspect tolerates empty
state; second aspect needs outputs from the first; invalid or mistyped state
fails before the aspect body runs; unknown aspect names yield
``StateValidationError``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    manager_bench + connections (e.g. mock DB)
              |
              v
    run_aspect(action, aspect_name, params, state={}, rollup=...)
              |
              v
    validate_state_for_aspect  ->  machine runs one aspect
              |
              v
    dict patch merged into frozen ``BaseState`` (implementation detail)

All cases use ``FullAction`` from ``tests.scenarios.domain_model`` with two
regular aspects: ``process_payment_aspect`` (``txn_id``) and ``calc_total_aspect``
(``total``). State is a ``dict``; aspect handlers return ``dict`` fragments.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Checkers for aspect *N* only see state produced by aspects *< N*; the first
  aspect has no preceding checkers.
- Core types (``Params``, ``Result``, merged state) remain immutable in the
  runtime; tests assert on returned dict slices or machine outputs.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    uv run pytest tests/bench/test_bench_run_aspect.py -q

Happy path: ``process_payment_aspect`` with ``state={}`` yields ``txn_id``.

Edge case: ``calc_total_aspect`` with ``txn_id`` wrong type -> validation error.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Depends on coordinator-discovered aspect/checker metadata matching
  ``FullAction`` definitions.

═══════════════════════════════════════════════════════════════════════════════
"""

from unittest.mock import AsyncMock

import pytest

from action_machine.testing import TestBench
from action_machine.testing.state_validator import StateValidationError
from tests.scenarios.domain_model import FullAction


class TestFirstAspect:
    """First regular aspect accepts an empty prerequisite state."""

    @pytest.mark.anyio
    async def test_empty_state_accepted(
        self, manager_bench: TestBench, mock_db: AsyncMock,
    ) -> None:
        """No preceding aspects -> no checkers -> empty ``state`` is valid."""
        action = FullAction()
        params = FullAction.Params(user_id="u1", amount=100.0)

        result = await manager_bench.run_aspect(
            action, "process_payment_aspect", params,
            state={},
            rollup=False,
            connections={"db": mock_db},
        )

        assert "txn_id" in result
        assert result["txn_id"] == "TXN-TEST-001"


class TestSecondAspect:
    """Second aspect consumes state produced by the first."""

    @pytest.mark.anyio
    async def test_valid_state_from_first_aspect(
        self, manager_bench: TestBench, mock_db: AsyncMock,
    ) -> None:
        """``calc_total_aspect`` requires ``txn_id`` from ``process_payment_aspect``."""
        action = FullAction()
        params = FullAction.Params(user_id="u1", amount=250.0)

        result = await manager_bench.run_aspect(
            action, "calc_total_aspect", params,
            state={"txn_id": "TXN-001"},
            rollup=False,
            connections={"db": mock_db},
        )

        assert result["total"] == 250.0


class TestInvalidState:
    """Invalid state is rejected before the aspect executes."""

    @pytest.mark.anyio
    async def test_missing_required_field(
        self, manager_bench: TestBench, mock_db: AsyncMock,
    ) -> None:
        """Empty state before ``calc_total_aspect`` -> missing ``txn_id``."""
        action = FullAction()
        params = FullAction.Params(user_id="u1", amount=100.0)

        with pytest.raises(StateValidationError, match="txn_id"):
            await manager_bench.run_aspect(
                action, "calc_total_aspect", params,
                state={},
                rollup=False,
                connections={"db": mock_db},
            )

    @pytest.mark.anyio
    async def test_wrong_type_in_state(
        self, manager_bench: TestBench, mock_db: AsyncMock,
    ) -> None:
        """``txn_id`` must be a string; ``int`` fails ``FieldStringChecker``."""
        action = FullAction()
        params = FullAction.Params(user_id="u1", amount=100.0)

        with pytest.raises(StateValidationError, match="must be a string"):
            await manager_bench.run_aspect(
                action, "calc_total_aspect", params,
                state={"txn_id": 123},
                rollup=False,
                connections={"db": mock_db},
            )


class TestNonexistentAspect:
    """Unknown aspect names produce a clear ``StateValidationError``."""

    @pytest.mark.anyio
    async def test_raises_state_validation_error(
        self, manager_bench: TestBench, mock_db: AsyncMock,
    ) -> None:
        """``nonexistent`` is not registered on ``FullAction``."""
        action = FullAction()
        params = FullAction.Params(user_id="u1", amount=100.0)

        with pytest.raises(StateValidationError, match="was not found"):
            await manager_bench.run_aspect(
                action, "nonexistent", params,
                state={},
                rollup=False,
                connections={"db": mock_db},
            )
