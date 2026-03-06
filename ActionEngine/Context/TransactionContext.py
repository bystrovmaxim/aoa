# ActionEngine/Context/TransactionContext.py
"""
Расширенный контекст для действий, выполняемых внутри транзакции.
Добавляет поле connection, содержащее открытое соединение с базой данных.
"""

from typing import Optional
from .Context import Context
from .UserInfo import UserInfo
from .RequestInfo import RequestInfo
from .EnvironmentInfo import EnvironmentInfo


class TransactionContext(Context):
    """
    Контекст для транзакционных действий.

    Наследует все поля обычного контекста и добавляет поле `connection`,
    которое содержит открытое соединение с базой данных (например, с PostgreSQL).
    Используется в действиях, наследующих BaseTransactionAction.

    Атрибуты:
        connection: Объект соединения (зависит от используемого менеджера соединений,
                    например, psycopg2 connection).

    Пример:
        >>> base_ctx = Context(user=user_info)
        >>> tx_ctx = TransactionContext(
        ...     user=base_ctx.user,
        ...     request=base_ctx.request,
        ...     environment=base_ctx.environment,
        ...     connection=db_connection
        ... )
        >>> # теперь в действии доступно ctx.connection
    """

    def __init__(
        self,
        user: Optional[UserInfo] = None,
        request: Optional[RequestInfo] = None,
        environment: Optional[EnvironmentInfo] = None,
        connection=None
    ):
        """
        Инициализирует транзакционный контекст.

        :param user: информация о пользователе
        :param request: метаданные запроса
        :param environment: информация об окружении
        :param connection: открытое соединение с базой данных
        """
        super().__init__(user, request, environment)
        self.connection = connection