# ActionEngine/BaseConnectionManager.py
from abc import ABC, abstractmethod
from typing import Any
from ..Core.Exceptions import ConnectionAlreadyOpenError, ConnectionNotOpenError

class BaseConnectionManager(ABC):
    """
    Абстрактный менеджер соединений/транзакций.
    Предоставляет методы для открытия, фиксации и отката.
    Конкретные наследники реализуют логику для конкретного типа БД/ресурса.
    """

    def __init__(self, connection_params: Any):
        self._connection_params = connection_params
        self._connection = None

    @abstractmethod
    def _doOpenConnection(self, connection_params: Any):
        """Создаёт и возвращает соединение (реализуется в наследнике)."""
        pass

    @abstractmethod
    def _doCommit(self, connection) -> None:
        """Фиксирует транзакцию и закрывает соединение."""
        pass

    @abstractmethod
    def _doRollback(self, connection) -> None:
        """Откатывает транзакцию и закрывает соединение."""
        pass

    def open(self) -> None:
        """Открывает соединение и начинает транзакцию."""
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
    def connection(self):
        """Возвращает текущее соединение (для передачи в действия)."""
        if self._connection is None:
            raise ConnectionNotOpenError("Соединение не открыто")
        return self._connection