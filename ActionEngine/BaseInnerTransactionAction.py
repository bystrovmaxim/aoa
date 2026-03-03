# Файл: ActionEngine/BaseInnerTransactionAction.py
"""
Базовый класс для действий, выполняемых внутри уже открытой транзакции.

Требования:
- Документирование всех методов.
- Текст исколючений писать на русском.
"""
from typing import Any, Dict
from .BaseSimpleAction import BaseSimpleAction
from .TransactionContext import TransactionContext

class BaseInnerTransactionAction(BaseSimpleAction):
    """
    Базовый класс для действий, которые выполняются внутри уже открытой транзакции.

    Такое действие НЕ управляет транзакцией (не открывает и не закрывает соединение).
    Оно принимает готовое соединение в конструкторе, а в методе run() создаёт
    расширенный контекст с этим соединением и вызывает родительский run.
    """

    def __init__(self, connection):
        """
        Параметры:
            connection: открытое соединение (например, курсор БД, сессия).
        """
        super().__init__()
        if connection is None:
            raise ValueError("Соединение не может быть None")
        self._connection = connection

    def run(self, ctx: TransactionContext, params: Dict[str, Any]) -> Any:
        """
        Создаёт расширенный контекст с сохранённым соединением и вызывает родительский run.
        """
        tx_ctx = TransactionContext(
            user_id=ctx.user_id,
            roles=ctx.roles,
            connection=self._connection
        )
        return super().run(tx_ctx, params)