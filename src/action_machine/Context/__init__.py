# ActionMachine/Context/__init__.py
"""
Компоненты контекста выполнения действия.

Экспортирует классы для представления информации о пользователе,
запросе, окружении и объединяющий их контекст.
"""

from .context import Context
from .request_info import RequestInfo
from .runtime_info import RuntimeInfo
from .user_info import UserInfo

__all__ = [
    "UserInfo",  # информация о пользователе (идентификатор, роли, доп. данные)
    "RequestInfo",  # метаданные запроса (trace_id, IP, метод, путь и т.д.)
    "RuntimeInfo",  # информация об окружении (хост, версия сервиса, среда)
    "Context",  # контекст выполнения, объединяющий user, request, environment
]
