# ActionEngine/Core/BaseTransactionAction.py
"""
Базовый класс для действий, выполняемых внутри открытой транзакции.

Требования:
- Документирование всех классов.
- Документирование всех методов.
- Текст исключений писать на русском.
"""
from typing import Any, Dict

from ActionEngine.Core.BaseSimpleAction import BaseSimpleAction
from ActionEngine.Context.TransactionContext import TransactionContext


class BaseTransactionAction(BaseSimpleAction):
    """
    Базовый класс для действий, выполняемых внутри открытой транзакции.

    Действие ожидает, что переданный в run контекст является экземпляром TransactionContext
    и содержит открытое соединение (атрибут connection). Если класс декорирован
    декоратором @requires_connection_type, дополнительно проверяется, что тип соединения
    соответствует указанному классу (или его подклассу). Проверка выполняется в защищённом
    методе _validate_connection, который можно переопределить в наследнике для расширенной логики.

    После успешной проверки вызывается родительский run, который выполнит все аспекты
    с переданным контекстом (содержащим соединение). Результат возвращается как обычно.
    """

    def _validate_connection(self, connection) -> None:
        """
        Проверяет, что тип соединения соответствует требованиям, заданным декоратором
        @requires_connection_type. Если требования не заданы, проверка пропускается.
        Может быть переопределён в наследнике для дополнительных проверок (например,
        проверка состояния соединения, прав и т.д.).
        """
        required_class = getattr(self.__class__, '_required_connection_class', None)
        if required_class and not isinstance(connection, required_class):
            raise TypeError(
                f"Действие {self.__class__.__name__} требует соединение типа {required_class.__name__}, "
                f"получен {type(connection).__name__}"
            )

    def run(self, ctx: TransactionContext, params: Dict[str, Any]) -> Any:
        """
        Запускает выполнение действия.

        Параметры:
            ctx: должен быть экземпляром TransactionContext и содержать открытое соединение.
            params: словарь с параметрами действия.

        Возвращает результат, возвращённый родительским run.
        """
        if not isinstance(ctx, TransactionContext):
            raise TypeError(f"Ожидался TransactionContext, получен {type(ctx).__name__}")
        if not hasattr(ctx, 'connection') or ctx.connection is None:
            raise ValueError("Контекст должен содержать открытое соединение (атрибут connection)")

        self._validate_connection(ctx.connection)

        return super().run(ctx, params)