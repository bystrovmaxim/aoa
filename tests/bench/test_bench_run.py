# tests/bench/test_bench_run.py
"""
Tests for ``TestBench.run()`` — full action execution on async and sync machines.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Exercise end-to-end bench runs: dependency-free actions, actions with mocked
dependencies, direct ``MockAction`` bypass, role checks tied to bench user
context, and the requirement to pass ``rollup`` explicitly.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    clean_bench / manager_bench / admin_bench
              |
              v
    run(action, params, rollup=..., connections=...)
              |
              ├── async machine  ----\
              └── sync machine   ----+--> compare_results -> single awaited result

``Params``, ``Result``, and merged state are immutable; assertions use field
equality or ``model_dump()`` where needed.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``MockAction`` must bypass the normal machine pipeline when passed to ``run``.
- Default stub user lacks ``AdminRole``; ``admin_bench`` supplies it.
- ``rollup`` has no default — callers must choose comparison mode explicitly.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    uv run pytest tests/bench/test_bench_run.py -q

Happy path: ``PingAction`` -> ``message == "pong"``.

Edge case: omitting ``rollup`` raises ``TypeError`` (guards accidental misuse).

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- ``manager_bench`` expects notification + payment mocks from shared fixtures.

═══════════════════════════════════════════════════════════════════════════════
"""

from unittest.mock import AsyncMock

import pytest

from action_machine.model.exceptions import AuthorizationError
from action_machine.testing import MockAction, TestBench
from tests.scenarios.domain_model import (
    AdminAction,
    FullAction,
    PingAction,
)


class TestSimpleAction:
    """Runs for actions without external dependencies."""

    @pytest.mark.anyio
    async def test_ping_returns_pong(self, clean_bench: TestBench) -> None:
        """``PingAction`` has no dependencies or regular aspects."""
        action = PingAction()
        params = PingAction.Params()

        result = await clean_bench.run(action, params, rollup=False)

        assert isinstance(result, PingAction.Result)
        assert result.message == "pong"


class TestActionWithDependencies:
    """Runs where aspects resolve mocked domain services."""

    @pytest.mark.anyio
    async def test_full_action_uses_mocks(
        self, manager_bench: TestBench, mock_db: AsyncMock,
    ) -> None:
        """``FullAction`` uses ``box.resolve()`` mocks and aspect state."""
        action = FullAction()
        params = FullAction.Params(user_id="u1", amount=500.0)

        result = await manager_bench.run(
            action, params, rollup=False, connections={"db": mock_db},
        )

        assert result.order_id == "ORD-u1"
        assert result.status == "created"
        assert result.total == 500.0
        assert result.txn_id == "TXN-TEST-001"


class TestMockAction:
    """``MockAction`` shortcuts the pipeline."""

    @pytest.mark.anyio
    async def test_bypasses_pipeline(self, clean_bench: TestBench) -> None:
        """``MockAction`` lacks ``@meta`` / ``@check_roles`` — pipeline would fail."""
        expected = PingAction.Result(message="direct")
        mock = MockAction(result=expected)

        result = await clean_bench.run(mock, PingAction.Params(), rollup=False)

        assert result is expected
        assert mock.call_count == 1


class TestRoleCheck:
    """Role enforcement reads the user from the bench-derived context."""

    @pytest.mark.anyio
    async def test_default_user_rejected_by_admin_action(
        self, clean_bench: TestBench,
    ) -> None:
        """Default ``StubTesterRole`` cannot run ``AdminAction``."""
        action = AdminAction()
        params = AdminAction.Params(target="user_456")

        with pytest.raises(AuthorizationError):
            await clean_bench.run(action, params, rollup=False)

    @pytest.mark.anyio
    async def test_with_user_grants_admin_access(
        self, admin_bench: TestBench,
    ) -> None:
        """``admin_bench`` supplies ``AdminRole`` so the action succeeds."""
        action = AdminAction()
        params = AdminAction.Params(target="user_456")

        result = await admin_bench.run(action, params, rollup=False)

        assert result.success is True
        assert result.target == "user_456"


class TestRollupRequired:
    """``rollup`` must be passed explicitly."""

    @pytest.mark.anyio
    async def test_missing_rollup_raises_type_error(
        self, clean_bench: TestBench,
    ) -> None:
        """A default ``rollup`` would hide which comparison mode a test uses."""
        action = PingAction()
        params = PingAction.Params()

        with pytest.raises(TypeError):
            await clean_bench.run(action, params)  # type: ignore[call-arg]
