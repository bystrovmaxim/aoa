# src/action_machine/Core/MockAction.py
"""
Mock action for testing.
Allows replacing real actions in tests.

Изменения (этап 1):
- Метод _mock_summary теперь принимает box: ToolsBox вместо deps и log.
- Обновлены комментарии.
"""

from collections.abc import Callable

from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.Core.BaseAction import BaseAction
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseResult import BaseResult
from action_machine.Core.BaseState import BaseState
from action_machine.Core.ToolsBox import ToolsBox
from action_machine.ResourceManagers.BaseResourceManager import BaseResourceManager


class MockAction(BaseAction[BaseParams, BaseResult]):
    """
    Mock action for use in tests.

    Replaces a real action, allowing a fixed result or a side_effect function
    that computes the result based on parameters. Also counts calls and remembers
    the last parameters.
    """

    def __init__(
        self, result: BaseResult | None = None, side_effect: Callable[[BaseParams], BaseResult] | None = None
    ) -> None:
        """
        Initializes the mock action.

        :param result: fixed result returned on each call.
        :param side_effect: function called with parameters to obtain the result.
                            If set, it is used instead of result.
        """
        self.result = result
        self.side_effect = side_effect
        self.call_count: int = 0
        self.last_params: BaseParams | None = None

    def run(self, params: BaseParams) -> BaseResult:
        """
        Executes the mock action.

        :param params: input parameters.
        :return: result (fixed or computed via side_effect).
        """
        self.call_count += 1
        self.last_params = params
        if self.side_effect:
            return self.side_effect(params)
        if self.result is None:
            raise ValueError("MockAction: neither result nor side_effect provided")
        return self.result

    @summary_aspect("mock summary")
    async def _mock_summary(
        self,
        params: BaseParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> BaseResult:
        """
        Stub for the summary aspect.

        Returns the result obtained by the run() method.
        This method is called by the machine when executing MockAction through
        the full pipeline.
        """
        return self.run(params)