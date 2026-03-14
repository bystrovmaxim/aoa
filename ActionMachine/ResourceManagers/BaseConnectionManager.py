# ActionMachine/ResourceManagers/BaseConnectionManager.py
"""
Базовый менеджер соединений с поддержкой транзакций.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
from ActionMachine.Core.Exceptions import ConnectionAlreadyOpenError, ConnectionNotOpenError


class BaseConnectionManager(ABC):
    """
    Абстрактный менеджер соединений с поддержкой транзакций.

    Предоставляет базовую логику открытия, фиксации и отката соединения.
    Конкретные реализации должны переопределить методы _doOpenConnection,
    _doCommit и _doRollback.
    """

    def __init__(self, connection_params: Any) -> None:
        """
        Инициализирует менеджер соединения.

        :param connection_params: параметры подключения (зависят от конкретной реализации).
        """
        self._connection_params = connection_params
        self._connection: Optional[Any] = None

    @abstractmethod
    def _doOpenConnection(self, connection_params: Any) -> Any:
        """
        Реализация открытия соединения (должна быть переопределена).

        :param connection_params: параметры подключения.
        :return: объект соединения.
        """
        pass

    @abstractmethod
    def _doCommit(self, connection: Any) -> None:
        """
        Реализация фиксации транзакции (должна быть переопределена).

        :param connection: объект соединения.
        """
        pass

    @abstractmethod
    def _doRollback(self, connection: Any) -> None:
        """
        Реализация отката транзакции (должна быть переопределена).

        :param connection: объект соединения.
        """
        pass

    def open(self) -> None:
        """Открывает соединение, если оно ещё не открыто."""
        if self._connection is not None:
            raise ConnectionAlreadyOpenError("Соединение уже открыто")
        self._connection = self._doOpenConnection(self._connection_params)

    def commit(self) -> None:
        """Фиксирует транзакцию и закрывает соединение."""
        if self._connection is None:
            raise ConnectionNotOpenError("Соединение не открыто")
        self._doCommit(self._connection)
        self._connection = None

    def rollback(self) -> None:
        """Откатывает транзакцию и закрывает соединение."""
        if self._connection is None:
            raise ConnectionNotOpenError("Соединение не открыто")
        self._doRollback(self._connection)
        self._connection = None

    @property
    def connection(self) -> Any:
        """Возвращает текущее открытое соединение."""
        if self._connection is None:
            raise ConnectionNotOpenError("Соединение не открыто")
        return self._connection
