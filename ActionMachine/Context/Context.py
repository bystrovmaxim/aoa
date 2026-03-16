# ActionMachine/Context/Context.py
"""
Контекст выполнения действия.

Содержит информацию о пользователе, запросе и окружении.
Передаётся в плагины и используется для проверки ролей.
Наследует ReadableMixin для поддержки dot-path доступа
через метод resolve и dict-подобного доступа через __getitem__.
"""

from typing import Optional, Dict, Any
from .UserInfo import UserInfo
from .RequestInfo import RequestInfo
from .EnvironmentInfo import EnvironmentInfo
from ActionMachine.Core.ReadableMixin import ReadableMixin


class Context(ReadableMixin):
    """
    Контекст выполнения действия.

    Содержит информацию о пользователе, запросе и окружении.
    Передаётся в плагины и используется для проверки ролей.

    Наследует ReadableMixin, что обеспечивает:
    - dict-подобный доступ: ctx["user"], ctx.get("request")
    - dot-path разрешение: ctx.resolve("user.user_id")
    """

    def __init__(
        self,
        user: Optional[UserInfo] = None,
        request: Optional[RequestInfo] = None,
        environment: Optional[EnvironmentInfo] = None
    ) -> None:
        """
        Инициализирует контекст.

        Аргументы:
            user: информация о пользователе.
            request: информация о запросе.
            environment: информация об окружении.
        """
        self.user = user or UserInfo()
        self.request = request or RequestInfo()
        self.environment = environment or EnvironmentInfo()
        self._extra: Dict[str, Any] = {}