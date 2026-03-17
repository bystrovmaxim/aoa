# ActionMachine/Context/__init__.py
"""
Компоненты контекста выполнения действия.

Экспортирует классы для представления информации о пользователе,
запросе, окружении и объединяющий их контекст.
"""

from .Context import Context
from .EnvironmentInfo import environment_info
from .RequestInfo import request_info
from .UserInfo import user_info

__all__ = [
    "user_info",  # информация о пользователе (идентификатор, роли, доп. данные)
    "request_info",  # метаданные запроса (trace_id, IP, метод, путь и т.д.)
    "environment_info",  # информация об окружении (хост, версия сервиса, среда)
    "Context",  # контекст выполнения, объединяющий user, request, environment
]
