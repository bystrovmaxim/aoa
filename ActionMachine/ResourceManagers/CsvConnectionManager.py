import os
import csv
from typing import Any, List, Optional
from .BaseConnectionManager import BaseConnectionManager
from ActionMachine.Core.Exceptions import ConnectionNotOpenError, HandleException

class CsvConnectionManager(BaseConnectionManager):
    def __init__(self, filepath: str) -> None:
        super().__init__(filepath)
        self._filepath = filepath
        self._file = None
        self._writer = None
        self._headers_written: bool = False

    def _doOpenConnection(self, connection_params: str) -> Any:
        dirname = os.path.dirname(connection_params)
        if dirname and not os.path.exists(dirname):
            os.makedirs(dirname, exist_ok=True)
        file = open(connection_params, 'a', newline='', encoding='utf-8')
        self._headers_written = file.tell() != 0
        return file

    def _doCommit(self, connection: Any) -> None:
        connection.close()

    def _doRollback(self, connection: Any) -> None:
        connection.close()

    def write_rows(self, headers: List[str], rows: List[List[Any]]) -> None:
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