# tests/core/test_base_action.py
"""
Tests for BaseAction — the base class for all actions.

Checks:
- get_full_class_name returns full class name (module.Class)
- Result is cached after first call

Изменения (этап 1):
- Нет изменений в логике BaseAction, так как аспекты не входят в этот файл.
- Обновлены комментарии.
"""

from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.Core.BaseAction import BaseAction
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseResult import BaseResult
from action_machine.Core.ToolsBox import ToolsBox


class MockParams(BaseParams):
    pass


class MockResult(BaseResult):
    pass


class SampleAction(BaseAction[MockParams, MockResult]):
    """Test action."""

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
    """Tests for BaseAction."""

    def test_get_full_class_name_returns_module_and_class(self):
        """Method returns string like 'module.ClassName'."""
        action = SampleAction()
        full_name = action.get_full_class_name()

        assert full_name == "tests.core.test_base_action.SampleAction"

    def test_get_full_class_name_caches_result(self):
        """Subsequent call returns cached value."""
        action = SampleAction()
        first = action.get_full_class_name()
        second = action.get_full_class_name()

        assert first is second  # same object (string)
        assert action._full_class_name is first