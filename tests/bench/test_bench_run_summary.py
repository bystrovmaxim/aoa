# tests/bench/test_bench_run_summary.py
"""
Tests for ``TestBench.run_summary()`` — execute only the summary aspect.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Validate pre-flight state checks and summary execution: full state succeeds;
incomplete or wrongly typed state fails before summary; actions without regular
aspects accept empty state; ``rollup`` remains a required keyword argument.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    manager_bench / clean_bench (fixtures)
              |
              v
    run_summary(action, params, state=..., rollup=..., connections=...)
              |
              v
    State validator  ->  GateCoordinator checker metadata
              |
              v
    Summary ``build_result`` reads ``txn_id``, ``total`` from state (FullAction)

``FullAction`` regular aspects (for validation only here):

- ``process_payment_aspect`` -> ``txn_id`` (``str``, required)
- ``calc_total_aspect`` -> ``total`` (``float``, required, ``min_value=0.0``)

``Params``, ``Result``, and merged ``State`` are immutable; state is passed as a
plain ``dict``.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Summary validation requires every field produced by preceding regular-aspect
  checkers unless the action has no regular aspects.
- ``rollup`` must always be passed explicitly (no default) so tests choose mode
  deliberately.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    uv run pytest tests/bench/test_bench_run_summary.py -q

Happy path: ``state`` includes ``txn_id`` and ``total`` -> ``FullAction.Result``.

Edge case: ``PingAction`` with ``state={}`` still returns ``message=="pong"``.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Assertions match ``StateValidationError`` substrings and fixture wiring
  (``manager_bench``, ``mock_db``).

═══════════════════════════════════════════════════════════════════════════════
"""

from unittest.mock import AsyncMock

import pytest

from action_machine.testing import TestBench
from action_machine.testing.state_validator import StateValidationError
from tests.scenarios.domain_model import FullAction, PingAction


class TestCompleteState:
    """Summary runs when state satisfies all regular-aspect checkers."""

    @pytest.mark.anyio
    async def test_returns_result_from_state(
        self, manager_bench: TestBench, mock_db: AsyncMock,
    ) -> None:
        """``build_result`` reads ``txn_id`` and ``total`` and returns ``FullAction.Result``."""
        action = FullAction()
        params = FullAction.Params(user_id="u1", amount=300.0)
        state = {
            "txn_id": "TXN-300",
            "total": 300.0,
        }

        result = await manager_bench.run_summary(
            action, params, state=state,
            rollup=False, connections={"db": mock_db},
        )

        assert result.order_id == "ORD-u1"
        assert result.txn_id == "TXN-300"
        assert result.total == 300.0
        assert result.status == "created"


class TestIncompleteState:
    """Incomplete state is rejected before the summary runs."""

    @pytest.mark.anyio
    async def test_missing_second_aspect_fields(
        self, manager_bench: TestBench, mock_db: AsyncMock,
    ) -> None:
        """Only ``txn_id`` present — missing ``total`` from ``calc_total_aspect``."""
        action = FullAction()
        params = FullAction.Params(user_id="u1", amount=100.0)

        with pytest.raises(StateValidationError, match="from aspect 'calc_total_aspect'"):
            await manager_bench.run_summary(
                action, params,
                state={"txn_id": "TXN-1"},
                rollup=False, connections={"db": mock_db},
            )

    @pytest.mark.anyio
    async def test_missing_first_aspect_fields(
        self, manager_bench: TestBench, mock_db: AsyncMock,
    ) -> None:
        """``txn_id`` from ``process_payment_aspect`` missing — error names field."""
        action = FullAction()
        params = FullAction.Params(user_id="u1", amount=100.0)

        with pytest.raises(StateValidationError, match="txn_id"):
            await manager_bench.run_summary(
                action, params,
                state={"total": 100.0},
                rollup=False, connections={"db": mock_db},
            )


class TestWrongTypeInState:
    """Wrong field types fail checker validation before summary."""

    @pytest.mark.anyio
    async def test_total_wrong_type(
        self, manager_bench: TestBench, mock_db: AsyncMock,
    ) -> None:
        """``total`` must be float; a string fails ``ResultFloatChecker``."""
        action = FullAction()
        params = FullAction.Params(user_id="u1", amount=100.0)

        with pytest.raises(StateValidationError, match="total"):
            await manager_bench.run_summary(
                action, params,
                state={"txn_id": "TXN-1", "total": "not-a-number"},
                rollup=False, connections={"db": mock_db},
            )


class TestSummaryOnlyAction:
    """Actions without regular aspects accept an empty state dict."""

    @pytest.mark.anyio
    async def test_ping_accepts_empty_state(
        self, clean_bench: TestBench,
    ) -> None:
        """``PingAction`` has no regular aspects — nothing to validate."""
        action = PingAction()
        params = PingAction.Params()

        result = await clean_bench.run_summary(
            action, params, state={}, rollup=False,
        )

        assert result.message == "pong"


class TestRollupRequired:
    """``rollup`` is a mandatory parameter."""

    @pytest.mark.anyio
    async def test_missing_rollup_raises_type_error(
        self, clean_bench: TestBench,
    ) -> None:
        """Omitting ``rollup`` raises ``TypeError``."""
        action = PingAction()
        params = PingAction.Params()

        with pytest.raises(TypeError):
            await clean_bench.run_summary(  # type: ignore[call-arg]
                action, params, state={},
            )
