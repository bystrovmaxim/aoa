# tests/core/test_mock_action.py
"""
Tests for MockAction — mock action for testing.

Checks:
- Calling with fixed result
- Calling with side_effect
- Call counting and saving last parameters
- Error when result and side_effect are missing

Изменения (этап 1):
- Метод _mock_summary в MockAction обновлён: теперь принимает box: ToolsBox вместо deps и log.
- В тестах это не требует изменений, так как тесты не вызывают аспект напрямую.
- Обновлены комментарии.
"""

import pytest

from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.mock_action import MockAction


class MockParams(BaseParams):
    pass


class MockResult(BaseResult):
    pass


class TestMockAction:
    """Tests for MockAction."""

    def test_run_with_result_returns_fixed_result(self):
        """MockAction with result returns that result on each call."""
        expected = MockResult()
        action = MockAction(result=expected)
        params = MockParams()

        result1 = action.run(params)
        result2 = action.run(params)

        assert result1 is expected
        assert result2 is expected

    def test_run_with_side_effect_calls_function(self):
        """MockAction with side_effect calls the function with parameters."""

        def side_effect(p):
            assert isinstance(p, MockParams)
            return MockResult()

        action = MockAction(side_effect=side_effect)
        params = MockParams()

        result = action.run(params)
        assert isinstance(result, MockResult)

    def test_side_effect_overrides_result(self):
        """If side_effect is given, result is ignored."""
        result_obj = MockResult()

        def side_effect(p):
            return MockResult()

        action = MockAction(result=result_obj, side_effect=side_effect)
        params = MockParams()

        result = action.run(params)
        assert result is not result_obj
        assert isinstance(result, MockResult)

    def test_call_count_increments(self):
        """call_count increments on each call."""
        action = MockAction(result=MockResult())
        params = MockParams()

        assert action.call_count == 0
        action.run(params)
        assert action.call_count == 1
        action.run(params)
        assert action.call_count == 2

    def test_last_params_stores_last_call_params(self):
        """last_params stores the parameters of the last call."""
        action = MockAction(result=MockResult())
        params1 = MockParams()
        params2 = MockParams()

        action.run(params1)
        assert action.last_params is params1

        action.run(params2)
        assert action.last_params is params2

    def test_no_result_no_side_effect_raises_value_error(self):
        """If neither result nor side_effect is given, run raises ValueError."""
        action = MockAction()
        params = MockParams()

        with pytest.raises(ValueError, match="neither result nor side_effect provided"):
            action.run(params)
