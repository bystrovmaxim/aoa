# ActionMachine/ResourceManagers/IBaseConnectionManager.py
"""
Интерфейс менеджера соединений с базами данных.
"""
from abc import abstractmethod
from typing import Any

from .base_resource_manager import BaseResourceManager


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
    async def execute(self, query: str, params: tuple[Any, ...] | None = None) -> Any:
        """Выполнить запрос."""
        pass
