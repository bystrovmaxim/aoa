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

from .EnvironmentInfo import environment_info
from .RequestInfo import request_info
from .UserInfo import user_info


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
        user: user_info | None = None,
        request: request_info | None = None,
        environment: environment_info | None = None,
    ) -> None:
        """
        Инициализирует контекст.

        Аргументы:
            user: информация о пользователе.
            request: информация о запросе.
            environment: информация об окружении.
        """
        self.user = user or user_info()
        self.request = request or request_info()
        self.environment = environment or environment_info()
        self._extra: dict[str, Any] = {}
