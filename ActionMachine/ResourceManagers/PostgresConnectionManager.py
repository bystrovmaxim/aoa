# ActionMachine/ResourceManagers/PostgresConnectionManager.py
import asyncpg
from typing import Any, Dict, Optional, Tuple, Type
from .IConnectionManager import IConnectionManager
from .WrapperConnectionManager import WrapperConnectionManager
from ActionMachine.Core.Exceptions import HandleException

class PostgresConnectionManager(IConnectionManager):
    """
    Реальный менеджер соединения для PostgreSQL.
    Выполняет непосредственную работу с asyncpg, не содержит проверок состояния.
    Проверки (например, что соединение открыто) выполняются в прокси-обёртке BaseConnectionManager.
    """

    def __init__(self, connection_params: Dict[str, Any]):
        """
        :param connection_params: словарь параметров для asyncpg.connect.
        """
        self._connection_params = connection_params
        self._conn: Optional[asyncpg.Connection] = None

    async def open(self) -> None:
        """Реально открывает соединение с PostgreSQL."""
        try:
            self._conn = await asyncpg.connect(**self._connection_params)
        except Exception as e:
            raise HandleException(f"Ошибка подключения к PostgreSQL: {e}") from e

    async def commit(self) -> None:
        """Фиксирует транзакцию."""
        if self._conn is None:
            # Эта ситуация не должна возникать при использовании через прокси,
            # но оставим защиту на случай прямого вызова.
            raise HandleException("Соединение не открыто")
        try:
            await self._conn.commit()
        except Exception as e:
            raise HandleException(f"Ошибка при commit: {e}") from e

    async def rollback(self) -> None:
        """Откатывает транзакцию."""
        if self._conn is None:
            raise HandleException("Соединение не открыто")
        try:
            await self._conn.rollback()
        except Exception as e:
            raise HandleException(f"Ошибка при rollback: {e}") from e

    async def execute(self, query: str, params: Optional[Tuple[Any, ...]] = None) -> Any:
        """Выполняет SQL-запрос."""
        if self._conn is None:
            raise HandleException("Соединение не открыто")
        try:
            return await self._conn.execute(query, *params if params else ())
        except Exception as e:
            raise HandleException(f"Ошибка выполнения SQL: {e}") from e

    def get_wrapper_class(self) -> Optional[Type[IConnectionManager]]:
        """
        Возвращает класс прокси-обёртки, которая будет использоваться при передаче
        этого ресурса в дочерние действия.
        """
        return WrapperConnectionManager