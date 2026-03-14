# ActionMachine/ResourceManagers/PostgresConnectionManager.py
"""
Асинхронный менеджер соединения для PostgreSQL с поддержкой транзакций.
Использует asyncpg.
"""

import asyncio
import asyncpg
from typing import Any, Dict, Optional, Tuple
from .BaseConnectionManager import BaseConnectionManager
from ActionMachine.Core.Exceptions import ConnectionNotOpenError, HandleException


class PostgresConnectionManager(BaseConnectionManager):
    """
    Асинхронный менеджер соединения для PostgreSQL.

    Реализует асинхронное открытие соединения, выполнение SQL-запросов,
    фиксацию и откат транзакций.
    """

    def __init__(self, connection_params: Dict[str, Any]) -> None:
        """
        Инициализирует менеджер с параметрами подключения.

        :param connection_params: словарь параметров для asyncpg.connect.
        """
        super().__init__(connection_params)
        self._connection: Optional[asyncpg.Connection] = None

    async def _doOpenConnection(self, connection_params: Dict[str, Any]) -> asyncpg.Connection:
        """
        Асинхронно открывает соединение с PostgreSQL.

        :param connection_params: параметры подключения.
        :return: объект соединения asyncpg.
        :raises HandleException: при ошибке подключения.
        """
        try:
            conn = await asyncpg.connect(**connection_params)
            return conn  # type: ignore[no-any-return]
        except Exception as e:
            raise HandleException(f"Ошибка подключения к PostgreSQL: {e}")

    async def _doCommit(self, connection: asyncpg.Connection) -> None:
        """
        Асинхронно фиксирует транзакцию и закрывает соединение.

        :param connection: объект соединения.
        :raises HandleException: при ошибке commit.
        """
        try:
            await connection.commit()  # type: ignore[attr-defined]
        except Exception as e:
            raise HandleException(f"Ошибка при commit: {e}")
        finally:
            await asyncio.shield(connection.close())

    async def _doRollback(self, connection: asyncpg.Connection) -> None:
        """
        Асинхронно откатывает транзакцию и закрывает соединение.

        :param connection: объект соединения.
        :raises HandleException: при ошибке rollback.
        """
        try:
            await connection.rollback()  # type: ignore[attr-defined]
        except Exception as e:
            raise HandleException(f"Ошибка при rollback: {e}")
        finally:
            await asyncio.shield(connection.close())

    async def execute(self, query: str, params: Optional[Tuple[Any, ...]] = None) -> Any:
        """
        Асинхронно выполняет SQL-запрос в открытом соединении.

        :param query: строка SQL-запроса.
        :param params: параметры запроса (кортеж).
        :return: результат выполнения (например, для SELECT строки).
        :raises ConnectionNotOpenError: если соединение не открыто.
        :raises HandleException: при ошибке выполнения запроса.
        """
        if self._connection is None:
            raise ConnectionNotOpenError("Соединение не открыто")
        try:
            return await self._connection.execute(query, *params if params else ())
        except Exception as e:
            raise HandleException(f"Ошибка выполнения SQL: {e}")