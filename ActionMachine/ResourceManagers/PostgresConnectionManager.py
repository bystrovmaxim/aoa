import psycopg2
from typing import Any, Dict, Optional, Tuple
from .BaseConnectionManager import BaseConnectionManager
from ActionMachine.Core.Exceptions import ConnectionNotOpenError, HandleException

class PostgresConnectionManager(BaseConnectionManager):
    def __init__(self, connection_params: Dict[str, Any]) -> None:
        super().__init__(connection_params)
        self._connection: Optional[psycopg2.extensions.connection] = None

    def _doOpenConnection(self, connection_params: Dict[str, Any]) -> psycopg2.extensions.connection:
        try:
            conn = psycopg2.connect(**connection_params)
            conn.autocommit = False
            return conn
        except Exception as e:
            raise HandleException(f"Ошибка подключения к PostgreSQL: {e}")

    def _doCommit(self, connection: psycopg2.extensions.connection) -> None:
        try:
            connection.commit()
        except Exception as e:
            raise HandleException(f"Ошибка при commit: {e}")
        finally:
            connection.close()

    def _doRollback(self, connection: psycopg2.extensions.connection) -> None:
        try:
            connection.rollback()
        except Exception as e:
            raise HandleException(f"Ошибка при rollback: {e}")
        finally:
            connection.close()

    def execute(self, query: str, params: Optional[Tuple[Any, ...]] = None) -> None:
        if self._connection is None:
            raise ConnectionNotOpenError("Соединение не открыто")
        try:
            with self._connection.cursor() as cur:
                cur.execute(query, params)
        except Exception as e:
            raise HandleException(f"Ошибка выполнения SQL: {e}")