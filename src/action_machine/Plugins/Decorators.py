# src/action_machine/plugins/decorators.py
"""
Декоратор @on — подписка метода плагина на событие машины.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Декоратор @on — часть грамматики намерений ActionMachine для плагинов.
Он объявляет, что метод плагина должен вызываться при наступлении
определённого события. Машина (ActionProductMachine) через PluginCoordinator
эмитирует события (global_start, global_finish, before:{aspect}, after:{aspect}
и др.), а плагины реагируют на них через методы, помеченные @on.

═══════════════════════════════════════════════════════════════════════════════
СИГНАТУРА ОБРАБОТЧИКА
═══════════════════════════════════════════════════════════════════════════════

Все обработчики обязаны иметь сигнатуру с 4 параметрами:

    async def handler(self, state, event, log) → state

    - self   — экземпляр плагина.
    - state  — текущее per-request состояние плагина.
    - event  — объект PluginEvent с данными о событии.
    - log    — ScopedLogger, привязанный к scope плагина. Scope содержит
               поля: machine, mode, plugin, action, event, nest_level.
               Все поля доступны в шаблонах через {%scope.*}.

Обработчик обязан вернуть обновлённое состояние.

═══════════════════════════════════════════════════════════════════════════════
ОГРАНИЧЕНИЯ (ИНВАРИАНТЫ)
═══════════════════════════════════════════════════════════════════════════════

- Применяется только к методам (callable), не к классам или свойствам.
- Метод должен быть асинхронным (async def).
- Сигнатура метода: ровно 4 параметра (self, state, event, log).
- event_type должен быть непустой строкой.
- action_filter должен быть строкой (регулярное выражение).

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА ИНТЕГРАЦИИ
═══════════════════════════════════════════════════════════════════════════════

    @on("global_finish", ".*", ignore_exceptions=False)
        │
        ▼  Декоратор записывает в method._on_subscriptions
    SubscriptionInfo(event_type="global_finish", action_filter=".*", ...)
        │
        ▼  MetadataBuilder._collect_subscriptions(cls)
    ClassMetadata.subscriptions = (SubscriptionInfo(...), ...)
        │
        ▼  PluginRunContext.emit_event(...)
    Находит подписанные методы → создаёт ScopedLogger → вызывает handler

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    class MetricsPlugin(Plugin):
        async def get_initial_state(self) -> dict:
            return {"count": 0}

        @on("global_finish", ".*", ignore_exceptions=False)
        async def count_calls(self, state: dict, event: PluginEvent, log) -> dict:
            state["count"] += 1
            await log.info(
                "[{%scope.plugin}] Действие {%scope.action} завершено "
                "за {%var.duration}с",
                duration=event.duration,
            )
            return state

        @on("before:validate", "CreateOrder.*")
        async def log_order_start(self, state: dict, event: PluginEvent, log) -> dict:
            await log.debug(
                "[{%scope.plugin}] Валидация заказа начата "
                "на уровне {%scope.nest_level}"
            )
            return state

═══════════════════════════════════════════════════════════════════════════════
ОШИБКИ
═══════════════════════════════════════════════════════════════════════════════

    TypeError — метод не callable; метод не асинхронный; неверное число
               параметров (не 4); event_type не строка;
               action_filter не строка.
    ValueError — event_type пустая строка.
"""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

# Ожидаемое число параметров для @on: self, state, event, log
_EXPECTED_PARAM_COUNT = 4

# Имена параметров для сообщения об ошибке
_EXPECTED_PARAM_NAMES = "self, state, event, log"


@dataclass(frozen=True)
class SubscriptionInfo:
    """
    Неизменяемая запись об одной подписке метода плагина на событие.

    Создаётся декоратором @on и сохраняется в method._on_subscriptions.
    MetadataBuilder собирает подписки в ClassMetadata.subscriptions.
    PluginCoordinator/PluginRunContext использует их для маршрутизации событий.

    Атрибуты:
        event_type: тип события (например, "global_finish", "before:validate").
        action_filter: регулярное выражение для фильтрации по имени действия.
                       По умолчанию ".*" — все действия.
        ignore_exceptions: если True, ошибка обработчика подавляется
                           и не прерывает выполнение действия.
                           По умолчанию True.
    """
    event_type: str
    action_filter: str = ".*"
    ignore_exceptions: bool = True


def on(
    event_type: str,
    action_filter: str = ".*",
    *,
    ignore_exceptions: bool = True,
) -> Callable[[Any], Any]:
    """
    Декоратор уровня метода. Подписывает метод плагина на событие машины.

    Записывает SubscriptionInfo в атрибут method._on_subscriptions.
    Один метод может быть подписан на несколько событий (несколько @on).

    Все обработчики обязаны иметь сигнатуру:
        async def handler(self, state, event, log) → state

    Аргументы:
        event_type: тип события. Непустая строка.
                    Примеры: "global_start", "global_finish",
                    "before:validate", "after:process_payment".
        action_filter: регулярное выражение для фильтрации по имени действия.
                       По умолчанию ".*" — все действия.
        ignore_exceptions: если True, ошибка обработчика подавляется.
                           По умолчанию True.

    Возвращает:
        Декоратор, который прикрепляет SubscriptionInfo к методу
        и возвращает метод без изменений.

    Исключения:
        TypeError:
            - event_type не строка.
            - action_filter не строка.
            - Декорируемый объект не callable.
            - Метод не асинхронный.
            - Неверное число параметров (не 4).
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
        """
        Внутренний декоратор, применяемый к методу плагина.

        Проверяет:
        1. func — callable.
        2. func — async def.
        3. Число параметров == 4 (self, state, event, log).

        Затем добавляет SubscriptionInfo в func._on_subscriptions.
        """
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

        # ── Проверка: число параметров == 4 ──
        sig = inspect.signature(func)
        param_count = len(sig.parameters)
        if param_count != _EXPECTED_PARAM_COUNT:
            raise TypeError(
                f"@on(\"{event_type}\"): метод {func.__name__} "
                f"должен принимать {_EXPECTED_PARAM_COUNT} параметра "
                f"({_EXPECTED_PARAM_NAMES}), получено {param_count}."
            )

        # ── Прикрепление подписки ──
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
