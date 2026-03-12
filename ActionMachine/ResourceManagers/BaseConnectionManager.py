from abc import ABC, abstractmethod
from typing import Any, Optional
from ActionMachine.Core.Exceptions import ConnectionAlreadyOpenError, ConnectionNotOpenError

class BaseConnectionManager(ABC):
    def __init__(self, connection_params: Any) -> None:
        self._connection_params = connection_params
        self._connection: Optional[Any] = None

    @abstractmethod
    def _doOpenConnection(self, connection_params: Any) -> Any:
        pass

    @abstractmethod
    def _doCommit(self, connection: Any) -> None:
        pass

    @abstractmethod
    def _doRollback(self, connection: Any) -> None:
        pass

    def open(self) -> None:
        if self._connection is not None:
            raise ConnectionAlreadyOpenError("Соединение уже открыто")
        self._connection = self._doOpenConnection(self._connection_params)

    def commit(self) -> None:
        if self._connection is None:
            raise ConnectionNotOpenError("Соединение не открыто")
        self._doCommit(self._connection)
        self._connection = None

    def rollback(self) -> None:
        if self._connection is None:
            raise ConnectionNotOpenError("Соединение не открыто")
        self._doRollback(self._connection)
        self._connection = None

    @property
    def connection(self) -> Any:
        if self._connection is None:
            raise ConnectionNotOpenError("Соединение не открыто")
        return self._connection