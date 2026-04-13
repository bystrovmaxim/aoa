# tests/smoke/test_simple.py
"""
Smoke test for SimpleAction — one regular aspect and a checker.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Exercises a two-aspect pipeline: the regular aspect writes validated_name to state,
result_string checker validates it, the summary aspect builds a greeting from state.

SimpleAction has no dependencies or connections; it is open to all (NoneRole).
If this test fails, the regular → state → summary pipeline or checkers are broken.
"""

import pytest

from action_machine.testing import TestBench
from tests.scenarios.domain_model import SimpleAction


@pytest.mark.asyncio
async def test_simple_action_greeting(bench: TestBench) -> None:
    """
    SimpleAction builds greeting 'Hello, Alice!' from name 'Alice'.

    Full pipeline:
    1. validate_name (regular) → state["validated_name"] = "Alice"
    2. result_string checker validates validated_name (non-empty string).
    3. build_greeting (summary) → Result(greeting="Hello, Alice!")
    """
    # Arrange
    action = SimpleAction()
    params = SimpleAction.Params(name="Alice")

    # Act
    result = await bench.run(action, params, rollup=False)

    # Assert
    assert result.greeting == "Hello, Alice!"


@pytest.mark.asyncio
async def test_simple_action_strips_whitespace(bench: TestBench) -> None:
    """
    SimpleAction strips leading/trailing whitespace from the name.

    validate_name calls params.name.strip(), so '  Bob  ' becomes 'Bob'.
    """
    # Arrange
    action = SimpleAction()
    params = SimpleAction.Params(name="  Bob  ")

    # Act
    result = await bench.run(action, params, rollup=False)

    # Assert
    assert result.greeting == "Hello, Bob!"


@pytest.mark.asyncio
async def test_simple_action_result_type(bench: TestBench) -> None:
    """
    SimpleAction returns an instance of SimpleAction.Result.

    Ensures the result is the concrete Result type, not BaseResult.
    """
    # Arrange
    action = SimpleAction()
    params = SimpleAction.Params(name="Charlie")

    # Act
    result = await bench.run(action, params, rollup=False)

    # Assert
    assert isinstance(result, SimpleAction.Result)
