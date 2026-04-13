# tests/bench/test_mock_action.py
"""
Tests for ``MockAction`` — lightweight stand-in actions for tests.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Cover fixed ``result``, callable ``side_effect`` (with precedence over
``result``), call tracking (``call_count``, ``last_params``), and the error when
neither outcome source is configured.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    MockAction(result=...) or MockAction(side_effect=fn)
              |
              v
    run(params)  ->  BaseResult (or raises if misconfigured)
              |
              v
    Updates call_count / last_params

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``side_effect`` wins when both ``result`` and ``side_effect`` are set.
- Each ``run`` increments ``call_count`` exactly once.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    uv run pytest tests/bench/test_mock_action.py -q

Edge case: ``MockAction()`` with no configuration raises ``ValueError``.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Synchronous ``run`` only; async bench paths wrap this separately.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Unit tests for the ``MockAction`` test double.
CONTRACT: Deterministic return or delegated computation; call telemetry.
INVARIANTS: Uses ``PingAction`` result/params types from scenarios.
═══════════════════════════════════════════════════════════════════════════════
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

import pytest

from action_machine.model.base_params import BaseParams
from action_machine.testing import MockAction
from tests.scenarios.domain_model import PingAction


class TestFixedResult:
    """``MockAction`` with a fixed ``result`` object."""

    def test_returns_same_object(self) -> None:
        """``run`` returns the exact ``result`` instance from the constructor."""
        expected = PingAction.Result(message="fixed")
        action = MockAction(result=expected)

        result = action.run(PingAction.Params())

        assert result is expected

    def test_stable_across_calls(self) -> None:
        """Repeated ``run`` calls reuse the same result object."""
        expected = PingAction.Result(message="stable")
        action = MockAction(result=expected)

        result1 = action.run(PingAction.Params())
        result2 = action.run(PingAction.Params())

        assert result1 is expected
        assert result2 is expected


class TestSideEffect:
    """``MockAction`` with a ``side_effect`` callable."""

    def test_delegates_to_function(self) -> None:
        """``side_effect`` receives params and its return value is propagated."""
        received = []
        from_side_effect = PingAction.Result(message="computed")

        def effect(p: BaseParams) -> PingAction.Result:
            received.append(p)
            return from_side_effect

        action = MockAction(side_effect=effect)
        params = PingAction.Params()

        result = action.run(params)

        assert received == [params]
        assert result is from_side_effect

    def test_priority_over_result(self) -> None:
        """When both are set, ``side_effect`` is used and ``result`` is ignored."""
        ignored = PingAction.Result(message="ignored")
        from_effect = PingAction.Result(message="from_effect")
        action = MockAction(result=ignored, side_effect=lambda p: from_effect)

        result = action.run(PingAction.Params())

        assert result is from_effect
        assert result is not ignored


class TestCallTracking:
    """``MockAction`` records invocation history."""

    def test_initial_state(self) -> None:
        """Before the first ``run``: ``call_count == 0``, ``last_params is None``."""
        action = MockAction(result=PingAction.Result(message="x"))

        assert action.call_count == 0
        assert action.last_params is None

    def test_increments_on_each_call(self) -> None:
        """Each ``run`` bumps ``call_count`` and refreshes ``last_params``."""
        action = MockAction(result=PingAction.Result(message="x"))
        p1 = PingAction.Params()
        p2 = PingAction.Params()

        action.run(p1)
        action.run(p2)

        assert action.call_count == 2
        assert action.last_params is p2


class TestNoResultOrSideEffect:
    """Misconfigured ``MockAction`` raises."""

    def test_raises_value_error(self) -> None:
        """Neither ``result`` nor ``side_effect`` -> ``ValueError``."""
        action = MockAction()

        with pytest.raises(ValueError, match="neither result nor side_effect"):
            action.run(PingAction.Params())
