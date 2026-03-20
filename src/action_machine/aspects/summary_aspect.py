# src/action_machine/aspects/summary_aspect.py
"""
    Декоратор для summary-аспекта.
"""

from collections.abc import Callable
from typing import Any, TypeVar

F = TypeVar('F', bound=Callable[..., Any])


def summary_aspect(description: str) -> Callable[[F], F]:
    """
    Декоратор для summary-аспекта.

    Не регистрирует аспект напрямую, а лишь добавляет временный атрибут
    `_new_aspect_meta` к методу. Регистрация выполняется позже классом
    `AspectGateHost` при создании класса действия.

    Аргументы:
        description: описание аспекта.

    Возвращает:
        Декорированный метод с добавленным атрибутом.
    """
    def decorator(method: F) -> F:
        method._new_aspect_meta = {  # type: ignore[attr-defined]
            'description': description,
            'type': 'summary'
        }
        return method
    return decorator