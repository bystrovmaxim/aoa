# src/action_machine/Core/MockAction.py
"""
Мок-действие для тестирования.
Позволяет подменять поведение реальных действий в тестах.
"""

from collections.abc import Callable

from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.Core.BaseAction import BaseAction
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseResult import BaseResult
from action_machine.Core.BaseState import BaseState
from action_machine.Core.DependencyFactory import DependencyFactory
from action_machine.Logging.action_bound_logger import ActionBoundLogger
from action_machine.ResourceManagers.BaseResourceManager import BaseResourceManager


class MockAction(BaseAction[BaseParams, BaseResult]):
    """
    Мок-действие для использования в тестах.

    Заменяет реальное действие, позволяя задать фиксированный результат
    или функцию side_effect, которая вычисляет результат на основе параметров.
    Также подсчитывает количество вызовов и запоминает последние параметры.
    """

    def __init__(
        self, result: BaseResult | None = None, side_effect: Callable[[BaseParams], BaseResult] | None = None
    ) -> None:
        """
        Инициализирует мок-действие.

        :param result: фиксированный результат, возвращаемый при каждом вызове.
        :param side_effect: функция, вызываемая с параметрами для получения результата.
                            Если задана, используется вместо result.
        """
        self.result = result
        self.side_effect = side_effect
        self.call_count: int = 0
        self.last_params: BaseParams | None = None

    def run(self, params: BaseParams) -> BaseResult:
        """
        Выполняет мок-действие.

        :param params: входные параметры.
        :return: результат (фиксированный или вычисленный через side_effect).
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
        deps: DependencyFactory,
        connections: dict[str, BaseResourceManager],
        log: ActionBoundLogger,
    ) -> BaseResult:
        """
        Заглушка для summary-аспекта.

        Возвращает результат, полученный методом run().
        Этот метод вызывается машиной при выполнении MockAction через полный конвейер.
        """
        # Вызываем run() синхронно, так как run() возвращает BaseResult.
        # В асинхронном контексте нужно убедиться, что run() не блокирует.
        return self.run(params)