# tests/core/test_mock_action.py
"""
Тесты MockAction — мок-действия для тестирования.

Проверяем:
- Вызов с фиксированным result
- Вызов с side_effect
- Подсчёт вызовов и сохранение последних параметров
- Ошибку при отсутствии result и side_effect
"""

import pytest

from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseResult import BaseResult
from action_machine.Core.MockAction import MockAction


class MockParams(BaseParams):
    pass


class MockResult(BaseResult):
    pass


class TestMockAction:
    """Тесты для MockAction."""

    def test_run_with_result_returns_fixed_result(self):
        """MockAction с result возвращает этот результат при каждом вызове."""
        expected = MockResult()
        action = MockAction(result=expected)
        params = MockParams()

        result1 = action.run(params)
        result2 = action.run(params)

        assert result1 is expected
        assert result2 is expected

    def test_run_with_side_effect_calls_function(self):
        """MockAction с side_effect вызывает функцию с параметрами."""

        def side_effect(p):
            assert isinstance(p, MockParams)
            return MockResult()

        action = MockAction(side_effect=side_effect)
        params = MockParams()

        result = action.run(params)
        assert isinstance(result, MockResult)

    def test_side_effect_overrides_result(self):
        """Если задан side_effect, result игнорируется."""
        result_obj = MockResult()

        def side_effect(p):
            return MockResult()

        action = MockAction(result=result_obj, side_effect=side_effect)
        params = MockParams()

        result = action.run(params)
        assert result is not result_obj
        assert isinstance(result, MockResult)

    def test_call_count_increments(self):
        """call_count увеличивается при каждом вызове."""
        action = MockAction(result=MockResult())
        params = MockParams()

        assert action.call_count == 0
        action.run(params)
        assert action.call_count == 1
        action.run(params)
        assert action.call_count == 2

    def test_last_params_stores_last_call_params(self):
        """last_params сохраняет параметры последнего вызова."""
        action = MockAction(result=MockResult())
        params1 = MockParams()
        params2 = MockParams()

        action.run(params1)
        assert action.last_params is params1

        action.run(params2)
        assert action.last_params is params2

    def test_no_result_no_side_effect_raises_value_error(self):
        """Если не заданы ни result, ни side_effect, run кидает ValueError."""
        action = MockAction()
        params = MockParams()

        with pytest.raises(ValueError, match="neither result nor side_effect provided"):
            action.run(params)