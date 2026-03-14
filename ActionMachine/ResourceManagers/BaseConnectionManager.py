# ActionMachine/ResourceManagers/BaseConnectionManager.py
"""
Асинхронный базовый менеджер соединений с поддержкой транзакций.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
from ActionMachine.Core.Exceptions import ConnectionAlreadyOpenError, ConnectionNotOpenError


class BaseConnectionManager(ABC):
    """
    Асинхронный абстрактный менеджер соединений с поддержкой транзакций.

    Предоставляет базовую логику открытия, фиксации и отката соединения.
    Конкретные реализации должны переопределить асинхронные методы
    _doOpenConnection, _doCommit и _doRollback.
    """

    def __init__(self, connection_params: Any) -> None:
        """
        Инициализирует менеджер соединения.

        :param connection_params: параметры подключения (зависят от конкретной реализации).
        """
        self._connection_params = connection_params
        self._connection: Optional[Any] = None

    @abstractmethod
    async def _doOpenConnection(self, connection_params: Any) -> Any:
        """
        Асинхронная реализация открытия соединения (должна быть переопределена).

        :param connection_params: параметры подключения.
        :return: объект соединения.
        """
        pass

    @abstractmethod
    async def _doCommit(self, connection: Any) -> None:
        """
        Асинхронная реализация фиксации транзакции (должна быть переопределена).

        :param connection: объект соединения.
        """
        pass

    @abstractmethod
    async def _doRollback(self, connection: Any) -> None:
        """
        Асинхронная реализация отката транзакции (должна быть переопределена).

        :param connection: объект соединения.
        """
        pass

    async def open(self) -> None:
        """Асинхронно открывает соединение, если оно ещё не открыто."""
        if self._connection is not None:
            raise ConnectionAlreadyOpenError("Соединение уже открыто")
        self._connection = await self._doOpenConnection(self._connection_params)

    async def commit(self) -> None:
        """Асинхронно фиксирует транзакцию и закрывает соединение."""
        if self._connection is None:
            raise ConnectionNotOpenError("Соединение не открыто")
        await self._doCommit(self._connection)
        self._connection = None

    async def rollback(self) -> None:
        """Асинхронно откатывает транзакцию и закрывает соединение."""
        if self._connection is None:
            raise ConnectionNotOpenError("Соединение не открыто")
        await self._doRollback(self._connection)
        self._connection = None

    @property
    def connection(self) -> Any:
        """Возвращает текущее открытое соединение (синхронно, так как это просто геттер)."""
        if self._connection is None:
            raise ConnectionNotOpenError("Соединение не открыто")
        return self._connection