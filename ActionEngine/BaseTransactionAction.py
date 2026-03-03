# Файл: ActionEngine/BaseTransactionAction.py
"""
Базовый класс для действий, управляющих транзакцией.

Требования:
- Документирование всех методов.
- Текст исколючений писать на русском.
"""
from abc import abstractmethod
from typing import Any, Dict
from .BaseSimpleAction import BaseSimpleAction
from .Context import Context
from .TransactionContext import TransactionContext

class BaseTransactionAction(BaseSimpleAction):
    """
    Базовый класс для действий, управляющих транзакцией.

    Отвечает за открытие соединения, выполнение бизнес-логики внутри транзакции,
    фиксацию или откат. Бизнес-логика вынесена в абстрактный метод _doInTransaction,
    который получает расширенный контекст с соединением и параметры, и должен вернуть результат.

    После выполнения _doInTransaction автоматически вызывается commit(),
    а в случае исключения — rollback().
    """

    def __init__(self, connection_params: Any):
        """
        Параметры:
            connection_params: параметры подключения (например, dict с настройками БД).
        """
        super().__init__()
        self._connection_params = connection_params
        self._connection = None

    # ---------- Публичные методы управления транзакцией ----------

    def openTransaction(self) -> None:
        """
        Открывает соединение и начинает транзакцию.
        Если соединение уже открыто, выбрасывает исключение.
        """
        if self._connection is not None:
            raise RuntimeError("Транзакция уже открыта")
        self._connection = self._doOpenConnection(self._connection_params)

    def commit(self) -> None:
        """
        Фиксирует транзакцию и закрывает соединение.
        Если транзакция не открыта, выбрасывает исключение.
        """
        if self._connection is None:
            raise RuntimeError("Нет открытой транзакции")
        self._doCommit(self._connection)
        self._connection = None

    def rollback(self) -> None:
        """
        Откатывает транзакцию и закрывает соединение.
        Если транзакция не открыта, выбрасывает исключение.
        """
        if self._connection is None:
            raise RuntimeError("Нет открытой транзакции")
        self._doRollback(self._connection)
        self._connection = None

    # ---------- Абстрактные методы для реализации ----------

    @abstractmethod
    def _doOpenConnection(self, connection_params: Any):
        """
        Абстрактный метод, **обязательный к переопределению**.
        Должен создать и вернуть объект соединения на основе переданных параметров.
        Может также начинать транзакцию, если это необходимо.
        """
        pass

    @abstractmethod
    def _doCommit(self, connection) -> None:
        """
        Абстрактный метод, **обязательный к переопределению**.
        Должен зафиксировать транзакцию и закрыть соединение.
        """
        pass

    @abstractmethod
    def _doRollback(self, connection) -> None:
        """
        Абстрактный метод, **обязательный к переопределению**.
        Должен откатить транзакцию и закрыть соединение.
        """
        pass

    @abstractmethod
    def _doInTransaction(self, ctx: TransactionContext, params: Dict[str, Any], result: Any) -> Any:
        """
        Абстрактный метод, **обязательный к переопределению**.
        Выполняет бизнес-логику внутри открытой транзакции.
        Принимает расширенный контекст (с соединением), параметры и текущий result.
        Должна вернуть новый результат.
        """
        pass

    # ---------- Основной метод run ----------

    def run(self, ctx: Context, params: Dict[str, Any]) -> Any:
        """
        Запускает выполнение действия с автоматическим управлением транзакцией.
        Открывает транзакцию, создаёт расширенный контекст, вызывает _doInTransaction,
        затем фиксирует или откатывает.
        """
        self.openTransaction()
        tx_ctx = TransactionContext(
            user_id=ctx.user_id,
            roles=ctx.roles,
            connection=self._connection
        )
        try:
            result = self._doInTransaction(tx_ctx, params, None)
            self.commit()
        except Exception:
            self.rollback()
            raise
        return result