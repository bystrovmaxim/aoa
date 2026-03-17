# ActionMachine/Core/MockAction.py
"""
Мок-действие для тестирования.
Позволяет подменять поведение реальных действий в тестах.
"""

from collections.abc import Callable

from action_machine.Core.BaseAction import BaseAction
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseResult import BaseResult


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
