# ActionMachine/Plugins/Decorators.py
"""
Модуль содержит декоратор @on для подписки методов плагинов на события.

Декоратор @on позволяет пометить метод плагина так, чтобы он вызывался
при наступлении событий, соответствующих заданным регулярным выражениям.
"""

import re
from collections.abc import Callable
from typing import Any


def _add_hook(
    method: Callable[..., Any],
    event_regex: str | re.Pattern[str],
    class_regex: str | re.Pattern[str],
    ignore_exceptions: bool,
) -> Callable[..., Any]:
    """
    Внутренняя функция для добавления информации о подписке к методу.

    Аргументы:
        method: метод, к которому прикрепляется подписка.
        event_regex: регулярное выражение для имени события (строка или скомпилированный Pattern).
        class_regex: регулярное выражение для полного имени класса действия (строка или Pattern).
        ignore_exceptions: флаг, указывающий, нужно ли игнорировать исключения в обработчике.

    Возвращает:
        Тот же метод с добавленным атрибутом _plugin_hooks и _on_subscriptions.

    Примечание:
        Атрибут _plugin_hooks представляет собой список кортежей
        (event_regex, class_regex, ignore_exceptions), каждый из которых
        соответствует одной подписке. Если метод уже имел подписки,
        новая добавляется в список.

        Атрибут _on_subscriptions используется для сбора подписок в OnGateHost.
    """
    if not hasattr(method, "_plugin_hooks"):
        method._plugin_hooks = []  # type: ignore[attr-defined]

    # Преобразуем строки в регулярные выражения для единообразия
    compiled_event: re.Pattern[str] = re.compile(event_regex) if isinstance(event_regex, str) else event_regex
    compiled_class: re.Pattern[str] = re.compile(class_regex) if isinstance(class_regex, str) else class_regex

    method._plugin_hooks.append((compiled_event, compiled_class, ignore_exceptions))  # type: ignore[attr-defined]

    # Новый механизм для шлюза
    if not hasattr(method, "_on_subscriptions"):
        method._on_subscriptions = []  # type: ignore[attr-defined]
    method._on_subscriptions.append((event_regex, class_regex, ignore_exceptions))  # type: ignore[attr-defined]

    return method


def on(
    event_regex: str | re.Pattern[str],
    class_regex: str | re.Pattern[str],
    ignore_exceptions: bool,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Декоратор для подписки метода плагина на события.

    Позволяет пометить метод плагина так, чтобы он вызывался при наступлении событий,
    соответствующих заданным регулярным выражениям, и для классов действий,
    соответствующих регулярному выражению class_regex.

    Аргументы:
        event_regex: регулярное выражение, которому должно соответствовать имя события.
            Может быть строкой или скомпилированным объектом Pattern.
            Примеры: 'global_start', 'before:.*', '.*'.
        class_regex: регулярное выражение для полного имени класса действия (включая модуль).
            Может быть строкой или Pattern.
            Примеры: 'myapp.actions.OrderAction', '.*OrderAction', 'myapp\\..*'.
        ignore_exceptions: если True, исключения, возникшие в обработчике, игнорируются
            (логируются, но не прерывают выполнение действия).
            Если False, любое исключение прерывает выполнение действия.

    Возвращает:
        Декоратор, который добавляет к методу информацию о подписке.

    Пример использования::

        class MyPlugin(Plugin):
            @on('global_start', '.*', ignore_exceptions=True)
            async def on_start(self, state_plugin, event):
                print("Action started")
                return state_plugin
    """

    def decorator(method: Callable[..., Any]) -> Callable[..., Any]:
        return _add_hook(method, event_regex, class_regex, ignore_exceptions)

    return decorator