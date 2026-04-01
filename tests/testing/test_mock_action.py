# tests/testing/test_mock_action.py
"""
Тесты для MockAction — мок-действия для тестирования.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

- Вызов с фиксированным результатом (result).
- Вызов с вычисляемым результатом (side_effect).
- side_effect имеет приоритет над result.
- Счётчик вызовов (call_count) инкрементируется.
- Сохранение параметров последнего вызова (last_params).
- Ошибка при отсутствии result и side_effect.
"""

import pytest

from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.testing import MockAction


class MockParams(BaseParams):
    """Пустые параметры для тестов."""
    pass


class MockResult(BaseResult):
    """Пустой результат для тестов."""
    pass


class TestMockAction:

    def test_returns_fixed_result(self):
        """
        Проверяет, что MockAction с фиксированным результатом возвращает его без изменений:

        1. Результат run() — тот же объект, что передан в конструктор — гарантирует,
           что мок не копирует и не модифицирует результат.

        2. Повторный вызов возвращает тот же объект — результат стабилен между вызовами.

        Это позволяет тестам подставить конкретный объект и проверять его по ссылке (is).
        """
        expected = MockResult()
        action = MockAction(result=expected)
        assert action.run(MockParams()) is expected
        assert action.run(MockParams()) is expected

    def test_side_effect_delegates_to_function(self):
        """
        Проверяет, что MockAction с side_effect делегирует вызов переданной функции:

        1. Параметры run() передаются в side_effect — входные данные не теряются,
           функция получает ровно то, что передано.

        2. Результат run() равен результату side_effect — мок возвращает значение
           от функции без изменений.

        Это позволяет MockAction вести себя как прозрачная обёртка над функцией.
        """
        received = []
        from_side_effect = MockResult()

        def side_effect(p):
            received.append(p)
            return from_side_effect

        action = MockAction(side_effect=side_effect)
        params = MockParams()
        result = action.run(params)

        assert received == [params]
        assert result is from_side_effect

    def test_side_effect_priority_over_result(self):
        """MockAction должен использовать side_effect и игнорировать result, если заданы оба."""
        ignored = MockResult()
        from_side_effect = MockResult()
        action = MockAction(result=ignored, side_effect=lambda p: from_side_effect)
        result = action.run(MockParams())
        assert result is from_side_effect
        assert result is not ignored

    def test_tracks_calls(self):
        """
        Проверяет, что MockAction отслеживает историю вызовов:

        1. call_count равен 0 до первого вызова — чистое начальное состояние.

        2. call_count увеличивается на 1 при каждом run() — позволяет проверить,
           сколько раз действие было вызвано.

        3. last_params указывает на параметры последнего вызова — позволяет проверить,
           с какими данными действие было вызвано в последний раз.

        Это необходимо для тестирования взаимодействий: сколько раз аспект вызвал
        дочернее действие и с какими параметрами.
        """
        action = MockAction(result=MockResult())
        p1 = MockParams()
        p2 = MockParams()

        assert action.call_count == 0
        assert action.last_params is None

        action.run(p1)
        assert action.call_count == 1
        assert action.last_params is p1

        action.run(p2)
        assert action.call_count == 2
        assert action.last_params is p2

    def test_raises_without_result_and_side_effect(self):
        """MockAction без result и side_effect должен бросить ValueError — нечего возвращать."""
        action = MockAction()
        with pytest.raises(ValueError, match="neither result nor side_effect"):
            action.run(MockParams())
