# Файл: YouTrackMCP/CsvIssuesSaverBase.py
"""
Абстрактный базовый класс для сохранятелей задач в CSV.

Требования:
- Документирование всех классов.
- Документирование всех методов.
- Текст исключений писать на русском.
"""
from abc import abstractmethod
from typing import Any, Dict, List, Tuple

from ActionEngine.BaseTransactionAction import BaseTransactionAction
from ActionEngine.TransactionContext import TransactionContext
from ActionEngine.Exceptions import HandleException


class BaseIssuesCSVSaver(BaseTransactionAction):
    """
    Абстрактный базовый класс для сохранятелей, которые получают список задач
    в формате JSON, преобразуют его в таблицу строк и записывают в CSV через соединение.

    Дочерние классы должны реализовать метод _preHandleAspect, который выполняет
    фильтрацию и преобразование данных и возвращает кортеж (headers, rows).
    """

    def __init__(self):
        """
        Конструктор без параметров, так как все необходимые данные (параметры подключения)
        будут переданы в run через params.
        """
        super().__init__()  
        pass

    @abstractmethod
    def _preHandleAspect(self, ctx: TransactionContext, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Аспект предварительной обработки.
        Должен быть переопределён в наследнике.
        Получает через params['issues'] список задач (список словарей) и, возможно, другие параметры.
        Должен вернуть результат в виде словаря с ключами:
            'headers' (List[str]) – названия колонок,
            'rows' (List[List[Any]]) – список строк для записи.
        Этот результат будет передан в _handleAspect.
        """
        pass

    def _handleAspect(self, ctx: TransactionContext, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Основной аспект, который записывает подготовленные строки в CSV через соединение из контекста.
        Ожидает, что в result (пришедшем от _preHandleAspect) есть ключи 'headers' и 'rows'.
        Также ожидает, что в params есть ключ 'first_page' (булево).
        """
        if not isinstance(ctx, TransactionContext):
            raise TypeError(f"Ожидался TransactionContext, получен {type(ctx).__name__}")
        if ctx.connection is None:
            raise ValueError("В контексте отсутствует открытое соединение (connection)")

        headers = result.get('headers')
        rows = result.get('rows')
        first_page = params.get('first_page', False)

        if headers is None or rows is None:
            raise ValueError("Результат _preHandleAspect должен содержать 'headers' и 'rows'")

        # Получаем менеджер соединения (это должен быть CsvConnectionManager)
        conn_mgr = ctx.connection
        try:
            conn_mgr.write_rows(headers, rows, first_page)
        except Exception as e:
            raise HandleException(f"Ошибка при записи в CSV: {e}")

        # Возвращаем результат (может быть пустым или содержать статистику)
        return {}