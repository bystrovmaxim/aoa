# ActionEngine/PostgresConnectionManager.py
import psycopg2
from typing import Any, Dict
from .BaseConnectionManager import BaseConnectionManager
from .Exceptions import ConnectionNotOpenError, HandleException

class PostgresConnectionManager(BaseConnectionManager):
    """
    Менеджер соединений для PostgreSQL.
    connection_params: словарь с ключами host, port, dbname, user, password.
    Транзакция начинается автоматически при первом запросе (autocommit=False).
    """

    def __init__(self, connection_params: Dict[str, Any]):
        super().__init__(connection_params)
        self._connection = None

    def _doOpenConnection(self, connection_params: Dict[str, Any]):
        """Открывает соединение и отключает autocommit для ручного управления транзакциями."""
        try:
            conn = psycopg2.connect(**connection_params)
            conn.autocommit = False
            return conn
        except Exception as e:
            raise HandleException(f"Ошибка подключения к PostgreSQL: {e}")

    def _doCommit(self, connection):
        """Фиксирует транзакцию, затем закрывает соединение."""
        try:
            connection.commit()
        except Exception as e:
            raise HandleException(f"Ошибка при commit: {e}")
        finally:
            connection.close()

    def _doRollback(self, connection):
        """Откатывает транзакцию, затем закрывает соединение."""
        try:
            connection.rollback()
        except Exception as e:
            raise HandleException(f"Ошибка при rollback: {e}")
        finally:
            connection.close()

    def execute(self, query: str, params: tuple = None):
        """
        Вспомогательный метод для выполнения SQL-запросов без возврата данных.
        Транзакция не фиксируется автоматически.
        """
        if self._connection is None:
            raise ConnectionNotOpenError("Соединение не открыто")
        try:
            with self._connection.cursor() as cur:
                cur.execute(query, params)
        except Exception as e:
            raise HandleException(f"Ошибка выполнения SQL: {e}")