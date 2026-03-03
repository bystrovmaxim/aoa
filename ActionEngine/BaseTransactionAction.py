# ActionEngine/BaseTransactionAction.py
from abc import abstractmethod
from typing import Any, Dict
from .BaseSimpleAction import BaseSimpleAction
from .Context import Context


class BaseTransactionAction(BaseSimpleAction):
    """
    Базовый класс для действий, работающих в рамках транзакции.
    Позволяет открыть соединение, выполнить несколько операций и закрыть.
    """

    def __init__(self, connection_params: Any):
        """
        :param connection_params: параметры подключения (например, dict с настройками БД)
        """
        super().__init__()
        self._connection_params = connection_params
        self._connection = None

    def openTransaction(self) -> None:
        """Открывает соединение и начинает транзакцию. Не переопределяется."""
        if self._connection is not None:
            raise RuntimeError("Транзакция уже открыта")
        self._connection = self._doOpenTransaction(self._connection_params)

    def closeTransaction(self) -> None:
        """Завершает транзакцию и закрывает соединение. Не переопределяется."""
        if self._connection is None:
            raise RuntimeError("Нет открытой транзакции")
        self._doCloseTransaction(self._connection)
        self._connection = None

    @abstractmethod
    def _doOpenTransaction(self, connection_params: Any):
        """
        Реализует открытие соединения.
        Должно вернуть объект соединения (например, курсор БД).
        """
        pass

    @abstractmethod
    def _doCloseTransaction(self, connection) -> None:
        """
        Закрывает соединение (коммит/откат).
        """
        pass

    @abstractmethod
    def _handleAspect(self, ctx: Context, params: Dict[str, Any], connection) -> None:
        """
        Основная бизнес-логика с использованием открытого соединения.
        """
        pass

    def Exec(self, ctx: Context, params: Dict[str, Any]) -> None:
        """
        Выполняет операцию в рамках открытой транзакции.
        Проверяет наличие соединения, затем вызывает аспекты.
        """
        if self._connection is None:
            raise RuntimeError("Транзакция не открыта. Сначала вызовите openTransaction().")

        # Аспекты без соединения
        self._permissionAuthorizationAspect(ctx, params)
        self._validationAspect(ctx, params)

        # Основной аспект с соединением
        self._handleAspect(ctx, params, self._connection)

        # Пост-аспект без соединения
        self._postHandleAspect(ctx, params)