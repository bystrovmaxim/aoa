# ActionMachine/Context/__init__.py
"""
Компоненты контекста выполнения действия.

Экспортирует классы для представления информации о пользователе,
запросе, окружении и объединяющий их контекст.
"""

from .context import Context
from .environment_info import EnvironmentInfo
from .request_info import RequestInfo
from .user_info import UserInfo

__all__ = [
    "UserInfo",  # информация о пользователе (идентификатор, роли, доп. данные)
    "RequestInfo",  # метаданные запроса (trace_id, IP, метод, путь и т.д.)
    "EnvironmentInfo",  # информация об окружении (хост, версия сервиса, среда)
    "Context",  # контекст выполнения, объединяющий user, request, environment
]
