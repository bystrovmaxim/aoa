################################################################################
# Файл: ActionMachine/ResourceManagers/PostgresConnectionManager.py
################################################################################

# ActionMachine/ResourceManagers/PostgresConnectionManager.py
"""
Реальный менеджер соединения для PostgreSQL.
Выполняет непосредственную работу с asyncpg, не содержит проверок состояния.
Проверки (например, что соединение открыто) выполняются в прокси-обёртке WrapperConnectionManager.
"""

from typing import Any

import asyncpg

from action_machine.core.exceptions import HandleError

from .iconnection_manager import IConnectionManager
from .wrapper_connection_manager import WrapperConnectionManager


class PostgresConnectionManager(IConnectionManager):
    """
    Реальный менеджер соединения для PostgreSQL.

    Использует asyncpg для подключения к базе данных.
    Методы commit и rollback реализованы через execute('COMMIT')
    и execute('ROLLBACK'), так как asyncpg.Connection не предоставляет
    методов commit()/rollback() напрямую — управление транзакциями
    осуществляется через SQL-команды или connection.transaction().
    """

    def __init__(self, connection_params: dict[str, Any]):
        """
        :param connection_params: словарь параметров для asyncpg.connect
                                  (host, port, user, password, database и т.д.)
        """
        self._connection_params = connection_params
        self._conn: asyncpg.Connection[asyncpg.Record] | None = None

    async def open(self) -> None:
        """Реально открывает соединение с PostgreSQL."""
        try:
            self._conn = await asyncpg.connect(**self._connection_params)
        except Exception as e:
            raise HandleError(f"Ошибка подключения к PostgreSQL: {e}") from e

    async def commit(self) -> None:
        """
        Фиксирует транзакцию.

        asyncpg не имеет метода connection.commit() — вместо этого
        отправляем SQL-команду COMMIT напрямую.
        """
        if self._conn is None:
            # Эта ситуация не должна возникать при использовании через прокси,
            # но оставим защиту на случай прямого вызова.
            raise HandleError("Соединение не открыто")
        try:
            await self._conn.execute("COMMIT")
        except Exception as e:
            raise HandleError(f"Ошибка при commit: {e}") from e

    async def rollback(self) -> None:
        """
        Откатывает транзакцию.

        asyncpg не имеет метода connection.rollback() — вместо этого
        отправляем SQL-команду ROLLBACK напрямую.
        """
        if self._conn is None:
            raise HandleError("Соединение не открыто")
        try:
            await self._conn.execute("ROLLBACK")
        except Exception as e:
            raise HandleError(f"Ошибка при rollback: {e}") from e

    async def execute(self, query: str, params: tuple[Any, ...] | None = None) -> Any:
        """Выполняет SQL-запрос."""
        if self._conn is None:
            raise HandleError("Соединение не открыто")
        try:
            return await self._conn.execute(query, *params if params else ())
        except Exception as e:
            raise HandleError(f"Ошибка выполнения SQL: {e}") from e

    def get_wrapper_class(self) -> type[IConnectionManager] | None:
        """
        Возвращает класс прокси-обёртки, которая будет использоваться при передаче
        этого ресурса в дочерние действия.
        """
        return WrapperConnectionManager


################################################################################
