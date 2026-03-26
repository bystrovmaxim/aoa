# src/action_machine/Plugins/Decorators.py
"""
Декоратор @on — подписка метода плагина на событие машины.

Назначение:
    Декоратор @on — часть грамматики намерений ActionMachine для плагинов.
    Он объявляет, что метод плагина должен вызываться при наступлении
    определённого события. Машина (ActionProductMachine) через PluginCoordinator
    эмитирует события (global_start, global_finish, aspect_before, aspect_after
    и др.), а плагины реагируют на них через методы, помеченные @on.

    Каждый обработчик получает текущее состояние плагина (state) и объект
    события (PluginEvent), возвращает обновлённое состояние.

Ограничения (инварианты):
    - Применяется только к методам (callable), не к классам или свойствам.
    - Метод должен быть асинхронным (async def).
    - Сигнатура метода: ровно 3 параметра (self, state, event).
    - Метод должен быть обычным методом экземпляра — не staticmethod, не classmethod.
      Проверка staticmethod/classmethod выполняется позже в __init_subclass__
      хоста (OnGateHost), так как на этапе декорирования Python ещё не обернул метод.
    - event_type должен быть непустой строкой.
    - action_filter должен быть строкой (регулярное выражение).

Что делает декоратор:
    Прикрепляет к методу атрибут _on_subscriptions — список подписок.
    Один метод может быть подписан на несколько событий (несколько @on).
    Этот атрибут позже считывается в OnGateHost.__init_subclass__.

Пример:
    class MetricsPlugin(Plugin):
        async def get_initial_state(self) -> dict:
            return {"count": 0}

        @on("global_finish", ".*", ignore_exceptions=False)
        async def count_calls(self, state: dict, event: PluginEvent) -> dict:
            state["count"] += 1
            return state

        @on("aspect_before", "CreateOrder.*")
        async def log_order_start(self, state: dict, event: PluginEvent) -> dict:
            print(f"Starting: {event.action_name}")
            return state

Ошибки:
    TypeError — метод не callable; метод не асинхронный; неверное число параметров;
               event_type не строка; action_filter не строка.
    ValueError — event_type пустая строка.
"""

from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass
from typing import Any

# Ожидаемое число параметров для @on: self, state, event
_EXPECTED_PARAM_COUNT = 3

# Имена параметров для сообщения об ошибке
_EXPECTED_PARAM_NAMES = "self, state, event"


@dataclass(frozen=True)
class SubscriptionInfo:
    """
    Неизменяемая запись об одной подписке метода плагина на событие.

    Атрибуты:
        event_type: тип события (например, "global_finish", "aspect_before").
        action_filter: регулярное выражение для фильтрации по имени действия.
                       По умолчанию ".*" — все действия.
        ignore_exceptions: если True, обработчик вызывается даже при ошибке
                           в действии. По умолчанию True.
    """
    event_type: str
    action_filter: str = ".*"
    ignore_exceptions: bool = True


def on(event_type: str, action_filter: str = ".*", *, ignore_exceptions: bool = True):
    """
    Декоратор уровня метода. Подписывает метод плагина на событие машины.

    Аргументы:
        event_type: тип события. Непустая строка.
        action_filter: регулярное выражение для фильтрации по имени действия.
                       По умолчанию ".*" — все действия.
        ignore_exceptions: если True, обработчик вызывается даже при ошибке
                           в действии.

    Возвращает:
        Декоратор, который прикрепляет SubscriptionInfo к методу.

    Исключения:
        TypeError:
            - event_type не строка.
            - action_filter не строка.
        ValueError:
            - event_type пустая строка.
    """
    # ── Проверка аргументов декоратора ──

    if not isinstance(event_type, str):
        raise TypeError(
            f"@on: event_type должен быть строкой, "
            f"получен {type(event_type).__name__}: {event_type!r}."
        )

    if not event_type.strip():
        raise ValueError(
            "@on: event_type не может быть пустой строкой. "
            "Укажите тип события, например 'global_finish'."
        )

    if not isinstance(action_filter, str):
        raise TypeError(
            f"@on: action_filter должен быть строкой, "
            f"получен {type(action_filter).__name__}: {action_filter!r}."
        )

    def decorator(func: Any) -> Any:
        # ── Проверка: цель — вызываемый объект ──
        if not callable(func):
            raise TypeError(
                f"@on можно применять только к методам. "
                f"Получен объект типа {type(func).__name__}: {func!r}."
            )

        # ── Проверка: метод асинхронный ──
        if not asyncio.iscoroutinefunction(func):
            raise TypeError(
                f"@on(\"{event_type}\"): метод {func.__name__} "
                f"должен быть асинхронным (async def). "
                f"Синхронные обработчики не поддерживаются."
            )

        # ── Проверка: число параметров ──
        sig = inspect.signature(func)
        param_count = len(sig.parameters)
        if param_count != _EXPECTED_PARAM_COUNT:
            raise TypeError(
                f"@on(\"{event_type}\"): метод {func.__name__} "
                f"должен принимать {_EXPECTED_PARAM_COUNT} параметра "
                f"({_EXPECTED_PARAM_NAMES}), получено {param_count}."
            )

        # ── Прикрепление подписки ──
        # Один метод может иметь несколько @on — список дополняется
        if not hasattr(func, '_on_subscriptions'):
            func._on_subscriptions = []

        func._on_subscriptions.append(
            SubscriptionInfo(
                event_type=event_type,
                action_filter=action_filter,
                ignore_exceptions=ignore_exceptions,
            )
        )

        return func

    return decorator
