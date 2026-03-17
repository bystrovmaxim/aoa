# ActionMachine/Context/Context.py
"""
Контекст выполнения действия.

Содержит информацию о пользователе, запросе и окружении.
Передаётся в плагины и используется для проверки ролей.
Наследует ReadableMixin для поддержки dot-path доступа
через метод resolve и dict-подобного доступа через __getitem__.
"""

from typing import Any

from action_machine.Core.ReadableMixin import ReadableMixin

from .EnvironmentInfo import EnvironmentInfo
from .RequestInfo import RequestInfo
from .UserInfo import UserInfo


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
        user: UserInfo | None = None,
        request: RequestInfo | None = None,
        environment: EnvironmentInfo | None = None,
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
        self._extra: dict[str, Any] = {}
