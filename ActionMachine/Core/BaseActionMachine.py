# ActionMachine/Core/BaseActionMachine.py
"""
Абстрактный базовый класс для всех машин действий.
Определяет единственный абстрактный метод run, который должен быть реализован
в наследниках. Метод является асинхронным.
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Optional, Dict, Type, Any

from ActionMachine.Core.BaseAction import BaseAction
from ActionMachine.Core.BaseParams import BaseParams
from ActionMachine.Core.BaseResult import BaseResult

P = TypeVar('P', bound=BaseParams)
R = TypeVar('R', bound=BaseResult)


class BaseActionMachine(ABC):
    """
    Абстрактная машина действий.

    Все реализации (продуктовая, тестовая) наследуют от этого класса
    и реализуют асинхронный метод run.
    """

    @abstractmethod
    async def run(
        self,
        action: BaseAction[P, R],
        params: P,
        resources: Optional[Dict[Type[Any], Any]] = None
    ) -> R:
        """
        Асинхронно запускает действие и возвращает результат.

        Аргументы:
            action: экземпляр действия для выполнения.
            params: входные параметры действия.
            resources: словарь внешних ресурсов (ключ – класс ресурса, значение – экземпляр),
                       которые будут переданы в фабрику зависимостей с приоритетом.

        Возвращает:
            Результат выполнения действия.
        """
        pass
