# src/action_machine/Context/context.py
"""
Контекст выполнения действия.

Содержит информацию о пользователе, запросе и окружении.
Передаётся в плагины и используется для проверки ролей.
Наследует ReadableMixin для поддержки dot-path доступа
через метод resolve и dict-подобного доступа через __getitem__.
"""

from typing import Any

from action_machine.core.readable_mixin import ReadableMixin

from .request_info import RequestInfo
from .runtime_info import RuntimeInfo
from .user_info import UserInfo


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
        runtime: RuntimeInfo | None = None,
    ) -> None:
        """
        Инициализирует контекст.

        Аргументы:
            user: информация о пользователе.
            request: информация о запросе.
            runtime: информация о среде выполнения (хост, версия, окружение).
        """
        self.user = user or UserInfo()
        self.request = request or RequestInfo()
        self.runtime = runtime or RuntimeInfo()
        self._extra: dict[str, Any] = {}
