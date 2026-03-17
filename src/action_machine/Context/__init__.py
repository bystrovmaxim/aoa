# ActionMachine/Context/__init__.py
"""
Компоненты контекста выполнения действия.

Экспортирует классы для представления информации о пользователе,
запросе, окружении и объединяющий их контекст.
"""

from .context import context
from .environment_info import environment_info
from .request_info import request_info
from .user_info import user_info

__all__ = [
    "user_info",  # информация о пользователе (идентификатор, роли, доп. данные)
    "request_info",  # метаданные запроса (trace_id, IP, метод, путь и т.д.)
    "environment_info",  # информация об окружении (хост, версия сервиса, среда)
    "context",  # контекст выполнения, объединяющий user, request, environment
]
