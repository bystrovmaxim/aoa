# ActionMachine/Logging/sensitive_decorator.py
"""
Декоратор для маркировки чувствительных данных в логах AOA.

Предоставляет декоратор @sensitive, который помечает геттер свойства
как содержащий чувствительные данные. При обращении к такому свойству
в шаблоне лога его значение будет замаскировано в соответствии
с параметрами, переданными декоратору.

Логика маскировки реализована в VariableSubstitutor; данный декоратор
только добавляет метаданные к функции.

Пример:
    >>> class UserInfo:
    ...     def __init__(self, email):
    ...         self._email = email
    ...
    ...     @property
    ...     @sensitive(True, max_chars=3, char='*', max_percent=50)
    ...     def email(self):
    ...         return self._email
"""

from collections.abc import Callable
from typing import Any, TypeVar

F = TypeVar('F', bound=Callable[..., Any])


def sensitive(
    enabled: bool,
    max_chars: int = 3,
    char: str = '*',
    max_percent: int = 50,
) -> Callable[[F], F]:
    """
    Декоратор, помечающий геттер свойства как чувствительный.

    Аргументы:
        enabled: если True, значение будет маскироваться; если False — нет.
        max_chars: максимальное количество символов в начале строки, которые показать.
        char: символ, используемый для замены скрытых символов.
        max_percent: максимальный процент длины строки, который показать.

    Возвращает:
        Декоратор, добавляющий атрибут _sensitive_config к функции.
    """

    def decorator(func: F) -> F:
        func._sensitive_config = {  # type: ignore[attr-defined]
            'enabled': enabled,
            'max_chars': max_chars,
            'char': char,
            'max_percent': max_percent,
        }
        return func

    return decorator