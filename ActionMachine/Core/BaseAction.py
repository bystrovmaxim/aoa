from abc import ABC
from typing import Generic, TypeVar, Any, Dict, List
from ActionMachine.Core.BaseParams import BaseParams
from ActionMachine.Core.BaseResult import BaseResult

P = TypeVar('P', bound=BaseParams)
R = TypeVar('R', bound=BaseResult)

class BaseAction(Generic[P, R], ABC):
    """
    Базовый класс для всех действий.
    Наследники определяют свои аспекты с помощью декораторов.
    Действия не имеют состояния – все данные передаются через params и data.
    """
    _dependencies: List[Dict[str, Any]] = []