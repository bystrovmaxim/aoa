# tests/core/test_base_action.py
"""
Тесты BaseAction — базового класса всех действий.

Проверяем:
- Метод get_full_class_name возвращает полное имя класса (модуль.Класс)
- Результат кешируется после первого вызова
"""

from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.Core.BaseAction import BaseAction
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseResult import BaseResult


class MockParams(BaseParams):
    pass


class MockResult(BaseResult):
    pass


class SampleAction(BaseAction[MockParams, MockResult]):
    """Тестовое действие."""

    @summary_aspect("test summary")
    async def summary(self, params, state, deps, connections, log):
        return MockResult()


class TestBaseAction:
    """Тесты для BaseAction."""

    def test_get_full_class_name_returns_module_and_class(self):
        """Метод возвращает строку вида 'module.ClassName'."""
        action = SampleAction()
        full_name = action.get_full_class_name()

        assert full_name == "tests.core.test_base_action.SampleAction"

    def test_get_full_class_name_caches_result(self):
        """Повторный вызов возвращает закешированное значение."""
        action = SampleAction()
        first = action.get_full_class_name()
        second = action.get_full_class_name()

        assert first is second  # один и тот же объект (строка)
        assert action._full_class_name is first