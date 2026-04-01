# tests/bench/test_mock_action.py
"""
Тесты MockAction — мок-действие для подстановки в тестах.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

- Фиксированный результат (result) — каждый вызов возвращает один объект.
- Вычисляемый результат (side_effect) — функция вызывается с params.
- side_effect имеет приоритет над result.
- Счётчик вызовов (call_count) инкрементируется при каждом run().
- Последние параметры (last_params) сохраняются для проверки.
- Ошибка при отсутствии result и side_effect.
"""

import pytest

from action_machine.core.base_params import BaseParams
from action_machine.testing import MockAction
from tests.domain import PingAction


class TestFixedResult:
    """MockAction с фиксированным результатом."""

    def test_returns_same_object(self) -> None:
        """
        Результат run() — тот же объект, что передан в конструктор.
        Мок не копирует и не модифицирует результат.
        """
        # Arrange
        expected = PingAction.Result(message="fixed")
        action = MockAction(result=expected)

        # Act
        result = action.run(PingAction.Params())

        # Assert — проверка по ссылке
        assert result is expected

    def test_stable_across_calls(self) -> None:
        """
        Повторный вызов возвращает тот же объект — результат стабилен.
        """
        # Arrange
        expected = PingAction.Result(message="stable")
        action = MockAction(result=expected)

        # Act
        result1 = action.run(PingAction.Params())
        result2 = action.run(PingAction.Params())

        # Assert
        assert result1 is expected
        assert result2 is expected


class TestSideEffect:
    """MockAction с вычисляемым результатом."""

    def test_delegates_to_function(self) -> None:
        """
        Параметры run() передаются в side_effect. Результат run()
        равен результату side_effect — мок как прозрачная обёртка.
        """
        # Arrange
        received = []
        from_side_effect = PingAction.Result(message="computed")

        def effect(p: BaseParams) -> PingAction.Result:
            received.append(p)
            return from_side_effect

        action = MockAction(side_effect=effect)
        params = PingAction.Params()

        # Act
        result = action.run(params)

        # Assert
        assert received == [params]
        assert result is from_side_effect

    def test_priority_over_result(self) -> None:
        """
        Если заданы и result, и side_effect — side_effect имеет приоритет.
        result игнорируется.
        """
        # Arrange
        ignored = PingAction.Result(message="ignored")
        from_effect = PingAction.Result(message="from_effect")
        action = MockAction(result=ignored, side_effect=lambda p: from_effect)

        # Act
        result = action.run(PingAction.Params())

        # Assert
        assert result is from_effect
        assert result is not ignored


class TestCallTracking:
    """MockAction отслеживает историю вызовов."""

    def test_initial_state(self) -> None:
        """
        До первого вызова: call_count=0, last_params=None.
        """
        # Arrange & Act
        action = MockAction(result=PingAction.Result(message="x"))

        # Assert
        assert action.call_count == 0
        assert action.last_params is None

    def test_increments_on_each_call(self) -> None:
        """
        call_count увеличивается на 1 при каждом run().
        last_params указывает на параметры последнего вызова.
        """
        # Arrange
        action = MockAction(result=PingAction.Result(message="x"))
        p1 = PingAction.Params()
        p2 = PingAction.Params()

        # Act
        action.run(p1)
        action.run(p2)

        # Assert
        assert action.call_count == 2
        assert action.last_params is p2


class TestNoResultOrSideEffect:
    """MockAction без result и side_effect — ошибка."""

    def test_raises_value_error(self) -> None:
        """
        Нечего возвращать — ValueError с понятным сообщением.
        """
        # Arrange
        action = MockAction()

        # Act & Assert
        with pytest.raises(ValueError, match="neither result nor side_effect"):
            action.run(PingAction.Params())
