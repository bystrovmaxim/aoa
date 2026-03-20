# src/action_machine/aspects/regular_aspect.py
"""
    Декоратор для обычных (regular) аспектов.
"""

from collections.abc import Callable
from typing import Any, TypeVar

F = TypeVar('F', bound=Callable[..., Any])


def regular_aspect(description: str) -> Callable[[F], F]:
    """
    Декоратор для обычных (regular) аспектов.

    Не регистрирует аспект напрямую, а лишь добавляет временный атрибут
    `_new_aspect_meta` к методу. Регистрация выполняется позже классом
    `AspectGateHost` при создании класса действия.

    Аргументы:
        description: описание аспекта (используется в логах и документации).

    Возвращает:
        Декорированный метод с добавленным атрибутом.
    """
    def decorator(method: F) -> F:
        method._new_aspect_meta = {  # type: ignore[attr-defined]
            'description': description,
            'type': 'regular'
        }
        return method
    return decorator