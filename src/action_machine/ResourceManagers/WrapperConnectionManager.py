# ActionMachine/ResourceManagers/BaseConnectionManager.py
from typing import Any

from action_machine.Core.Exceptions import HandleException, TransactionProhibitedError

from .IConnectionManager import IConnectionManager


class WrapperConnectionManager(IConnectionManager):
    """
    Прокси-обёртка для менеджера соединений, запрещающая управление транзакциями
    на вложенных уровнях, но разрешающая выполнение запросов.
    """

    def __init__(self, connection_manager: IConnectionManager):
        """
        :param connection_manager: реальный менеджер соединения (созданный выше по иерархии)
        """
        self._connection_manager = connection_manager

    async def _do_open_connection(self, connection_params: Any) -> Any:
        raise TransactionProhibitedError(
            "Открытие соединения разрешено только в том действии, где ресурс был создан. "
            "Текущее действие получило ресурс через прокси, поэтому open недоступен."
        )

    async def _do_commit(self, connection: Any) -> None:
        raise TransactionProhibitedError(
            "Фиксация транзакции разрешена только в том действии, где ресурс был создан. "
            "Текущее действие получило ресурс через прокси, поэтому commit недоступен."
        )

    async def _do_rollback(self, connection: Any) -> None:
        raise TransactionProhibitedError(
            "Откат транзакции разрешён только в том действии, где ресурс был создан. "
            "Текущее действие получило ресурс через прокси, поэтому rollback недоступен."
        )

    async def open(self) -> None:
        await self._do_open_connection(None)

    async def commit(self) -> None:
        await self._do_commit(None)

    async def rollback(self) -> None:
        await self._do_rollback(None)

    async def execute(self, query: str, params: tuple[Any, ...] | None = None) -> Any:
        try:
            return await self._connection_manager.execute(query, params)
        except Exception as e:
            raise HandleException(f"Ошибка выполнения SQL: {e}") from e
