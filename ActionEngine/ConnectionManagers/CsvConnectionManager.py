# ActionEngine/ConnectionManagers/CsvConnectionManager.py
"""
Конкретный менеджер соединений для работы с CSV-файлами.

Требования:
- Документирование всех классов.
- Документирование всех методов.
- Текст исключений писать на русском.
"""
import os
import csv
from typing import Any, List, Optional
from .BaseConnectionManager import BaseConnectionManager
from ActionEngine.Core.Exceptions import ConnectionAlreadyOpenError, ConnectionNotOpenError, HandleException


class CsvConnectionManager(BaseConnectionManager):
    """
    Менеджер соединений для записи в CSV-файл.
    При открытии создаёт файл (если его нет) и открывает его в режиме дозаписи.
    Предоставляет метод write_rows для добавления строк.
    """

    def __init__(self, filepath: str):
        """
        Параметры:
            filepath: полный путь к CSV-файлу.
        """
        super().__init__(filepath)
        self._filepath = filepath
        self._file = None
        self._writer = None
        self._headers_written = False

    def _doOpenConnection(self, connection_params: str):
        """
        Открывает файл для дозаписи. Если файл не существует, он будет создан.
        Возвращает объект файла.
        """
        # Создаём директорию, если не существует
        dirname = os.path.dirname(connection_params)
        if dirname and not os.path.exists(dirname):
            os.makedirs(dirname, exist_ok=True)
        # Открываем файл в режиме дозаписи (создаст, если нет)
        file = open(connection_params, 'a', newline='', encoding='utf-8')
        self._headers_written = file.tell() != 0  # если файл не пустой, значит заголовки уже были
        return file

    def _doCommit(self, connection) -> None:
        """
        Закрывает файл.
        """
        connection.close()

    def _doRollback(self, connection) -> None:
        """
        Откат для CSV не имеет смысла, просто закрываем файл.
        """
        connection.close()

    def write_rows(self, headers: List[str], rows: List[List[Any]]) -> None:
        """
        Записывает строки в CSV-файл.

        Параметры:
            headers: список названий колонок.
            rows: список строк, каждая строка — список значений в том же порядке, что и headers.

        Исключения:
            ConnectionNotOpenError: если соединение не открыто.
            HandleException: при ошибках записи.
        """
        if self._connection is None:
            raise ConnectionNotOpenError("Соединение не открыто. Вызовите open() перед записью.")

        try:
            writer = csv.writer(self._connection)
            # Записываем заголовки только если они ещё не были записаны
            if not self._headers_written:
                writer.writerow(headers)
                self._headers_written = True
            for row in rows:
                writer.writerow(row)
            self._connection.flush()  # сбрасываем буфер
        except Exception as e:
            raise HandleException(f"Ошибка записи в CSV: {e}")