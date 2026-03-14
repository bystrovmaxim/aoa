################################################################################
# Файл: ActionMachine/ResourceManagers/PostgresConnectionManager.py
################################################################################

# ActionMachine/ResourceManagers/PostgresConnectionManager.py
"""
Реальный менеджер соединения для PostgreSQL.
Выполняет непосредственную работу с asyncpg, не содержит проверок состояния.
Проверки (например, что соединение открыто) выполняются в прокси-обёртке WrapperConnectionManager.
"""

import asyncpg
from typing import Any, Dict, Optional, Tuple, Type
from .IConnectionManager import IConnectionManager
from .WrapperConnectionManager import WrapperConnectionManager
from ActionMachine.Core.Exceptions import HandleException


class PostgresConnectionManager(IConnectionManager):
    """
    Реальный менеджер соединения для PostgreSQL.

    Использует asyncpg для подключения к базе данных.
    Методы commit и rollback реализованы через execute('COMMIT')
    и execute('ROLLBACK'), так как asyncpg.Connection не предоставляет
    методов commit()/rollback() напрямую — управление транзакциями
    осуществляется через SQL-команды или connection.transaction().
    """

    def __init__(self, connection_params: Dict[str, Any]):
        """
        :param connection_params: словарь параметров для asyncpg.connect
                                  (host, port, user, password, database и т.д.)
        """
        self._connection_params = connection_params
        self._conn: Optional[asyncpg.Connection[asyncpg.Record]] = None

    async def open(self) -> None:
        """Реально открывает соединение с PostgreSQL."""
        try:
            self._conn = await asyncpg.connect(**self._connection_params)
        except Exception as e:
            raise HandleException(f"Ошибка подключения к PostgreSQL: {e}") from e

    async def commit(self) -> None:
        """
        Фиксирует транзакцию.

        asyncpg не имеет метода connection.commit() — вместо этого
        отправляем SQL-команду COMMIT напрямую.
        """
        if self._conn is None:
            # Эта ситуация не должна возникать при использовании через прокси,
            # но оставим защиту на случай прямого вызова.
            raise HandleException("Соединение не открыто")
        try:
            await self._conn.execute("COMMIT")
        except Exception as e:
            raise HandleException(f"Ошибка при commit: {e}") from e

    async def rollback(self) -> None:
        """
        Откатывает транзакцию.

        asyncpg не имеет метода connection.rollback() — вместо этого
        отправляем SQL-команду ROLLBACK напрямую.
        """
        if self._conn is None:
            raise HandleException("Соединение не открыто")
        try:
            await self._conn.execute("ROLLBACK")
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

################################################################################