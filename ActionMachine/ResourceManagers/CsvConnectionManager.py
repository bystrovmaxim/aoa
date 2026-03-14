# ActionMachine/ResourceManagers/CsvConnectionManager.py
"""
Менеджер соединения для работы с CSV-файлами.
Реализует запись строк в CSV-файл с автоматическим созданием директорий.
"""

import os
import csv
from typing import Any, List
from .BaseConnectionManager import BaseConnectionManager
from ActionMachine.Core.Exceptions import ConnectionNotOpenError, HandleException


class CsvConnectionManager(BaseConnectionManager):
    """
    Менеджер соединения для CSV-файлов.

    Позволяет открывать файл для добавления записей, писать строки
    и закрывать файл. Поддерживает автоматическое создание заголовков.
    """

    def __init__(self, filepath: str) -> None:
        """
        Инициализирует менеджер с указанием пути к файлу.

        :param filepath: путь к CSV-файлу.
        """
        super().__init__(filepath)
        self._filepath = filepath
        self._file = None
        self._writer = None
        self._headers_written: bool = False

    def _doOpenConnection(self, connection_params: str) -> Any:
        """
        Открывает файл для добавления (append), создавая директории при необходимости.

        :param connection_params: путь к файлу.
        :return: открытый файловый объект.
        """
        dirname = os.path.dirname(connection_params)
        if dirname and not os.path.exists(dirname):
            os.makedirs(dirname, exist_ok=True)
        file = open(connection_params, 'a', newline='', encoding='utf-8')
        self._headers_written = file.tell() != 0
        return file

    def _doCommit(self, connection: Any) -> None:
        """
        Закрывает файл (commit).

        :param connection: файловый объект.
        """
        connection.close()

    def _doRollback(self, connection: Any) -> None:
        """
        Закрывает файл без сохранения изменений (rollback) – для CSV это просто закрытие.

        :param connection: файловый объект.
        """
        connection.close()

    def write_rows(self, headers: List[str], rows: List[List[Any]]) -> None:
        """
        Записывает строки в CSV-файл. Если заголовки ещё не записаны, записывает их сначала.

        :param headers: список заголовков.
        :param rows: список строк (каждая строка — список значений).
        :raises ConnectionNotOpenError: если соединение не открыто.
        :raises HandleException: при ошибке записи.
        """
        if self._connection is None:
            raise ConnectionNotOpenError("Соединение не открыто. Вызовите open() перед записью.")
        try:
            writer = csv.writer(self._connection)
            if not self._headers_written:
                writer.writerow(headers)
                self._headers_written = True
            for row in rows:
                writer.writerow(row)
            self._connection.flush()
        except Exception as e:
            raise HandleException(f"Ошибка записи в CSV: {e}")
