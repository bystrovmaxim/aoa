from abc import ABC, abstractmethod
from typing import TypeVar, Generic
from ActionMachine.Core.BaseAction import BaseAction
from ActionMachine.Core.BaseParams import BaseParams
from ActionMachine.Core.BaseResult import BaseResult

P = TypeVar('P', bound=BaseParams)
R = TypeVar('R', bound=BaseResult)

class BaseActionMachine(ABC):
    @abstractmethod
    def run(self, action: BaseAction[P, R], params: P) -> R:
        """Запускает действие и возвращает результат."""
        pass