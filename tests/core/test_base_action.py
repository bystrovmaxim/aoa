# tests/core/test_base_action.py
"""
Тесты для BaseAction — базового класса для всех действий.

Проверяем:
- get_full_class_name возвращает полное имя класса (module.Class).
- Результат кешируется после первого вызова.
- BaseAction наследует ActionMetaGateHost, что делает @meta обязательным
  для классов с аспектами.
"""

from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.meta_decorator import meta
from action_machine.core.meta_gate_hosts import ActionMetaGateHost
from action_machine.core.tools_box import ToolsBox


class MockParams(BaseParams):
    pass


class MockResult(BaseResult):
    pass


@meta(description="Тестовое действие для проверки get_full_class_name")
class SampleAction(BaseAction[MockParams, MockResult]):
    """Тестовое действие."""

    @summary_aspect("test summary")
    async def summary(
        self,
        params: MockParams,
        state: dict,
        box: ToolsBox,
        connections: dict,
    ) -> MockResult:
        return MockResult()


class TestBaseAction:
    """Тесты для BaseAction."""

    def test_get_full_class_name_returns_module_and_class(self):
        """Метод возвращает строку вида 'module.ClassName'."""
        action = SampleAction()
        full_name = action.get_full_class_name()

        assert full_name == "tests.core.test_base_action.SampleAction"

    def test_get_full_class_name_caches_result(self):
        """Повторный вызов возвращает кешированное значение."""
        action = SampleAction()
        first = action.get_full_class_name()
        second = action.get_full_class_name()

        assert first is second  # тот же объект (строка)
        assert action._full_class_name is first

    def test_base_action_inherits_action_meta_gate_host(self):
        """BaseAction наследует ActionMetaGateHost."""
        assert issubclass(BaseAction, ActionMetaGateHost)
        assert issubclass(SampleAction, ActionMetaGateHost)
