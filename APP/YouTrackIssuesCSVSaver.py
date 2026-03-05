from typing import Any, Dict

from ActionEngine import (
    BaseTransactionAction,
    requires_connection_type,
    TransactionContext,
    InstanceOfChecker,
    IntFieldChecker,
    HandleException)

from .IYouTrackIssuesSaver import IYouTrackIssuesSaver


@InstanceOfChecker("headers", expected_class=list, required=True, desc="Входной параметр: заголовки CSV (список)")
@InstanceOfChecker("rows", expected_class=list, required=True, desc="Входной параметр: строки данных (список списков)")
class YouTrackIssuesCSVSaver(BaseTransactionAction, IYouTrackIssuesSaver):
    """
    Сохранятель для записи данных в CSV-файл.
    Ожидает, что в контексте есть открытое соединение CsvConnectionManager.
    Параметры должны содержать 'headers' и 'rows'.
    """

    def __init__(self):
        super().__init__()

    @IntFieldChecker("written_rows", min_value=0, desc="Результат _handleAspect: количество фактически записанных строк")
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

        try:
            ctx.connection.write_rows(headers, rows)
        except Exception as e:
            raise HandleException(f"Ошибка при записи в CSV: {e}")

        return {"written_rows": len(rows)}