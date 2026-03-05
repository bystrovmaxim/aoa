# ActionEngine/Context/TransactionContext.py
from typing import Optional
from .Context import Context
from .UserInfo import UserInfo
from .RequestInfo import RequestInfo
from .EnvironmentInfo import EnvironmentInfo

class TransactionContext(Context):
    """
    Расширенный контекст для транзакционных действий.
    Добавляет поле connection (открытое соединение с БД).
    """

    def __init__(
        self,
        user: Optional[UserInfo] = None,
        request: Optional[RequestInfo] = None,
        environment: Optional[EnvironmentInfo] = None,
        connection=None
    ):
        super().__init__(user, request, environment)
        self.connection = connection