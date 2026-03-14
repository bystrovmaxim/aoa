# ActionMachine/Core/MockAction.py
"""
Мок-действие для тестирования.
Позволяет подменять поведение реальных действий в тестах.
"""

from typing import Optional, Callable
from ActionMachine.Core.BaseParams import BaseParams
from ActionMachine.Core.BaseResult import BaseResult
from ActionMachine.Core.BaseAction import BaseAction


class MockAction(BaseAction[BaseParams, BaseResult]):
    """
    Мок-действие для использования в тестах.

    Заменяет реальное действие, позволяя задать фиксированный результат
    или функцию side_effect, которая вычисляет результат на основе параметров.
    Также подсчитывает количество вызовов и запоминает последние параметры.
    """

    def __init__(
        self,
        result: Optional[BaseResult] = None,
        side_effect: Optional[Callable[[BaseParams], BaseResult]] = None
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
        self.last_params: Optional[BaseParams] = None

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
