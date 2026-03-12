# ActionMachine/Core/BaseActionMachine.py
"""
Абстрактный базовый класс для всех машин действий.

Определяет единственный абстрактный метод run, который должен быть реализован
в наследниках. Метод является синхронным; асинхронно выполняются только
обработчики плагинов.
"""

from abc import ABC, abstractmethod
from typing import TypeVar

from ActionMachine.Core.BaseAction import BaseAction
from ActionMachine.Core.BaseParams import BaseParams
from ActionMachine.Core.BaseResult import BaseResult

P = TypeVar('P', bound=BaseParams)
R = TypeVar('R', bound=BaseResult)


class BaseActionMachine(ABC):
    """
    Абстрактная машина действий.

    Все реализации (продуктовая, тестовая) наследуют от этого класса
    и реализуют синхронный метод run.
    """

    @abstractmethod
    def run(self, action: BaseAction[P, R], params: P) -> R:
        """
        Запускает действие и возвращает результат.

        Аргументы:
            action: экземпляр действия для выполнения.
            params: входные параметры действия.

        Возвращает:
            Результат выполнения действия.
        """
        pass