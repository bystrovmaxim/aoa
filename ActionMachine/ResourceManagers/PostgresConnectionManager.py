# ActionMachine/ResourceManagers/PostgresConnectionManager.py
"""
Менеджер соединения для PostgreSQL с поддержкой транзакций.
"""

import psycopg2
from typing import Any, Dict, Optional, Tuple
from .BaseConnectionManager import BaseConnectionManager
from ActionMachine.Core.Exceptions import ConnectionNotOpenError, HandleException


class PostgresConnectionManager(BaseConnectionManager):
    """
    Менеджер соединения для PostgreSQL.

    Реализует открытие соединения, выполнение SQL-запросов,
    фиксацию и откат транзакций.
    """

    def __init__(self, connection_params: Dict[str, Any]) -> None:
        """
        Инициализирует менеджер с параметрами подключения.

        :param connection_params: словарь параметров для psycopg2.connect.
        """
        super().__init__(connection_params)
        self._connection: Optional[psycopg2.extensions.connection] = None

    def _doOpenConnection(self, connection_params: Dict[str, Any]) -> psycopg2.extensions.connection:
        """
        Открывает соединение с PostgreSQL.

        :param connection_params: параметры подключения.
        :return: объект соединения psycopg2.
        :raises HandleException: при ошибке подключения.
        """
        try:
            conn = psycopg2.connect(**connection_params)
            conn.autocommit = False
            return conn
        except Exception as e:
            raise HandleException(f"Ошибка подключения к PostgreSQL: {e}")

    def _doCommit(self, connection: psycopg2.extensions.connection) -> None:
        """
        Фиксирует транзакцию и закрывает соединение.

        :param connection: объект соединения.
        :raises HandleException: при ошибке commit.
        """
        try:
            connection.commit()
        except Exception as e:
            raise HandleException(f"Ошибка при commit: {e}")
        finally:
            connection.close()

    def _doRollback(self, connection: psycopg2.extensions.connection) -> None:
        """
        Откатывает транзакцию и закрывает соединение.

        :param connection: объект соединения.
        :raises HandleException: при ошибке rollback.
        """
        try:
            connection.rollback()
        except Exception as e:
            raise HandleException(f"Ошибка при rollback: {e}")
        finally:
            connection.close()

    def execute(self, query: str, params: Optional[Tuple[Any, ...]] = None) -> None:
        """
        Выполняет SQL-запрос в открытом соединении.

        :param query: строка SQL-запроса.
        :param params: параметры запроса (кортеж).
        :raises ConnectionNotOpenError: если соединение не открыто.
        :raises HandleException: при ошибке выполнения запроса.
        """
        if self._connection is None:
            raise ConnectionNotOpenError("Соединение не открыто")
        try:
            with self._connection.cursor() as cur:
                cur.execute(query, params)
        except Exception as e:
            raise HandleException(f"Ошибка выполнения SQL: {e}")
