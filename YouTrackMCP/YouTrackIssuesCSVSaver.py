# Файл: YouTrackMCP/YouTrackIssuesCSVSaver.py
"""
Сохранятель для задач YouTrack в CSV с использованием двух стратегий.
"""
from typing import Any, Dict, List

from ActionEngine.TransactionContext import TransactionContext
from ActionEngine.Exceptions import HandleException
from .BaseYouTrackIssuesSaver import BaseYouTrackIssuesSaver


class YouTrackIssuesCSVSaver(BaseYouTrackIssuesSaver):
    """
    Сохранятель, который записывает задачи YouTrack в CSV-файл.
    Использует стратегии из базового класса для извлечения данных.
    Для работы требует, чтобы в контексте было открытое соединение типа CsvConnectionManager.
    """

    def __init__(self, strategy: List[str] = None):
        """
        Параметры:
            strategy: список типов карточек, которые должен обрабатывать этот сейвер.
                      Если не указан, будет пустой список (ничего не сохранится).
        """
        super().__init__()
        self._strategy = strategy or []

    def _handleAspect(
        self,
        ctx: TransactionContext,
        params: Dict[str, Any],
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Записывает подготовленные строки в CSV через соединение.
        """
        if ctx.connection is None:
            raise ValueError("В контексте отсутствует открытое соединение")

        headers = result.get('headers')
        rows = result.get('rows')
        if headers is None or rows is None:
            raise ValueError("Результат _preHandleAspect должен содержать 'headers' и 'rows'")

        first_page = params.get('first_page', False)

        try:
            ctx.connection.write_rows(headers, rows, first_page)
        except Exception as e:
            raise HandleException(f"Ошибка при записи в CSV: {e}")

        return {"written_rows": len(rows)}