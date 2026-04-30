# tests/bench/test_bench_run.py
"""
Tests for ``TestBench.run()`` — pipeline bypass and explicit ``rollup``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Covers ``MockAction`` short-circuit and the requirement to pass ``rollup``
explicitly.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    clean_bench
              |
              v
    run(action, params, rollup=...)

"""

import pytest

from action_machine.testing import MockAction, TestBench
from tests.scenarios.domain_model import PingAction


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
