# tests/smoke/test_ping.py
"""
Smoke test for PingAction — minimal action.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Exercises the basic ActionMachine pipeline on the simplest action: the coordinator
collects metadata, the machine runs a single summary aspect, TestBench runs on async
and sync machines and compares results.

PingAction has no params, dependencies, connections, or role constraints (NoneRole).
If this test fails, something fundamental is broken.
"""

import pytest

from action_machine.testing import TestBench
from tests.scenarios.domain_model import PingAction


@pytest.mark.asyncio
async def test_ping_returns_pong(bench: TestBench) -> None:
    """
    PingAction returns Result with message='pong'.

    Covers the full path: metadata → role check (NoneRole) → summary aspect → Result.
    TestBench runs on async and sync machines and compares.
    """
    # Arrange
    action = PingAction()
    params = PingAction.Params()

    # Act
    result = await bench.run(action, params, rollup=False)

    # Assert
    assert result.message == "pong"


@pytest.mark.asyncio
async def test_ping_result_type(bench: TestBench) -> None:
    """
    PingAction returns an instance of PingAction.Result.

    Ensures the result is the concrete Result type, not an arbitrary BaseResult or dict.
    """
    # Arrange
    action = PingAction()
    params = PingAction.Params()

    # Act
    result = await bench.run(action, params, rollup=False)

    # Assert
    assert isinstance(result, PingAction.Result)
