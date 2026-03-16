from typing import Optional, Dict, Any
from .UserInfo import UserInfo
from .RequestInfo import RequestInfo
from .EnvironmentInfo import EnvironmentInfo


class Context:
    """
    Контекст выполнения действия.

    Содержит информацию о пользователе, запросе и окружении.
    Передаётся в плагины и используется для проверки ролей.
    """

    def __init__(
        self,
        user: Optional[UserInfo] = None,
        request: Optional[RequestInfo] = None,
        environment: Optional[EnvironmentInfo] = None
    ) -> None:
        """
        Инициализирует контекст.

        :param user: информация о пользователе.
        :param request: информация о запросе.
        :param environment: информация об окружении.
        """
        self.user = user or UserInfo()
        self.request = request or RequestInfo()
        self.environment = environment or EnvironmentInfo()
        self._extra: Dict[str, Any] = {}

    