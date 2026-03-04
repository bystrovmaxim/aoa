from typing import Any, Dict

from ActionEngine.BaseTransactionAction import BaseTransactionAction
from ActionEngine.TransactionContext import TransactionContext
from ActionEngine.Exceptions import HandleException
from .IYouTrackIssuesSaver import IYouTrackIssuesSaver


class YouTrackIssuesCSVSaver(BaseTransactionAction, IYouTrackIssuesSaver):
    """
    Сохранятель для записи данных в CSV-файл.
    Ожидает, что в контексте есть открытое соединение CsvConnectionManager.
    Параметры должны содержать 'headers' и 'rows'.
    """

    def __init__(self):
        super().__init__()

    def _handleAspect(
        self,
        ctx: TransactionContext,
        params: Dict[str, Any],
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        if ctx.connection is None:
            raise ValueError("В контексте отсутствует открытое соединение")

        headers = params.get("headers")
        rows = params.get("rows")
        if headers is None or rows is None:
            raise ValueError("Параметры должны содержать 'headers' и 'rows'")

        first_page = params.get("first_page", False)

        try:
            ctx.connection.write_rows(headers, rows, first_page)
        except Exception as e:
            raise HandleException(f"Ошибка при записи в CSV: {e}")

        return {"written_rows": len(rows)}