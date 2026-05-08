# tests/intents/compensate/test_saga_rollback.py
"""Compensation stack unwinding tests (Saga) in ActionProductMachine.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Checks that the compensator return value is ignored when unwinding.

═══════════════════════════════════════════════════════════════════════════════
STRUCTURE
═══════════════════════════════════════════════════════════════════════════════

TestCompensatorReturnValueIgnored — return value does not replace the aspect error.
"""

from __future__ import annotations

import pytest

from tests.action_machine.scenarios.domain_model.compensate_actions import (
    CompensatedOrderAction,
    CompensateTestParams,
)


class TestCompensatorReturnValueIgnored:
    """Checks that the compensator's return value is ignored."""

    @pytest.mark.anyio
    async def test_compensator_return_value_ignored(self, compensate_bench) -> None:
        """Even if the compensator returns a dict, it does not affect the result −
        the aspect error is thrown out."""
        params = CompensateTestParams(
            user_id="user_123",
            amount=100.0,
            should_fail=True,
        )

        with pytest.raises(ValueError):
            await compensate_bench.run(
                CompensatedOrderAction(),
                params,
                rollup=False,
            )
