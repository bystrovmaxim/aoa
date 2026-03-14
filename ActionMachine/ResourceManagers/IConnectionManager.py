# ActionMachine/ResourceManagers/IBaseConnectionManager.py
from abc import abstractmethod
from typing import Any, Optional, Tuple
from .BaseResourceManager import BaseResourceManager

class IConnectionManager(BaseResourceManager):
    """
    Интерфейс для всех менеджеров соединений с базами данных.
    """

    @abstractmethod
    async def open(self) -> None:
        """Открыть соединение."""
        pass

    @abstractmethod
    async def commit(self) -> None:
        """Зафиксировать транзакцию."""
        pass

    @abstractmethod
    async def rollback(self) -> None:
        """Откатить транзакцию."""
        pass

    @abstractmethod
    async def execute(self, query: str, params: Optional[Tuple[Any, ...]] = None) -> Any:
        """Выполнить запрос."""
        pass