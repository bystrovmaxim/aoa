# src/action_machine/plugins/plugin.py
"""
Базовый класс для всех плагинов ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Плагины определяют обработчики событий с помощью декоратора @on.
Каждый плагин должен реализовать асинхронный метод get_initial_state,
который возвращает начальное состояние для одного запуска действия.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА ИНТЕГРАЦИИ
═══════════════════════════════════════════════════════════════════════════════

    class CounterPlugin(Plugin):
        async def get_initial_state(self) -> dict:
            return {"count": 0}

        @on("global_finish", ".*")
        async def count_call(self, state, event):
            state["count"] += 1
            return state

    # Декоратор @on записывает SubscriptionInfo в method._on_subscriptions.
    # MetadataBuilder собирает подписки в ClassMetadata.subscriptions.
    # PluginCoordinator маршрутизирует события к подписанным методам.

═══════════════════════════════════════════════════════════════════════════════
ПРАВИЛА
═══════════════════════════════════════════════════════════════════════════════

- Плагины НЕ хранят состояние в атрибутах экземпляра. Состояние
  управляется машиной и передаётся через параметр state каждому обработчику.
- Все методы-обработчики должны быть асинхронными (async def).
- get_initial_state вызывается машиной перед первым событием.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    class MetricsPlugin(Plugin):
        async def get_initial_state(self) -> dict:
            return {"total": 0, "errors": 0}

        @on("global_finish")
        async def track_total(self, state, event):
            state["total"] += 1
            return state

        @on("global_finish")
        async def track_errors(self, state, event):
            if event.error is not None:
                state["errors"] += 1
            return state
"""

import re
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any


class Plugin(ABC):
    """
    Абстрактный базовый класс для всех плагинов.

    Каждый плагин должен реализовать асинхронный метод get_initial_state,
    который возвращает начальное состояние для одного запуска действия.
    Состояние будет передано всем обработчикам плагина, и каждый обработчик
    должен вернуть обновлённое состояние.

    Плагины не должны хранить состояние в атрибутах экземпляра,
    поскольку оно должно быть изолировано для каждого вызова run.

    Методы-обработчики помечаются декоратором @on из модуля decorators.
    Они должны быть асинхронными (определены с async def), даже если
    не содержат await, потому что машина вызывает их с await.
    """

    @abstractmethod
    async def get_initial_state(self) -> object:
        """
        Возвращает начальное состояние плагина для одного выполнения действия.

        Этот метод вызывается машиной перед первым выполнением любого обработчика
        данного плагина в рамках текущего вызова run. Возвращаемое значение
        может быть любого типа (обычно словарь или пользовательский объект).
        Оно будет передано всем обработчикам как первый аргумент state,
        и каждый обработчик должен вернуть новое состояние.

        Возвращает:
            Начальное состояние для этого запуска.
        """

    def get_handlers(
        self, event_name: str, class_name: str,
    ) -> list[tuple[Callable[..., Any], bool]]:
        """
        Возвращает список подходящих обработчиков для указанного события
        и класса действия.

        Сканирует методы экземпляра плагина, ищет атрибут _on_subscriptions,
        и для каждой подписки проверяет совпадение event_type и action_filter.

        Аргументы:
            event_name: имя события (например, 'global_finish',
                        'before:validate').
            class_name: полное имя класса действия (включая модуль).

        Возвращает:
            Список кортежей (метод-обработчик, ignore_exceptions)
            для всех подходящих подписок.
        """
        handlers: list[tuple[Callable[..., Any], bool]] = []

        # Обходим MRO класса плагина и ищем методы с _on_subscriptions
        for klass in type(self).__mro__:
            if klass is object:
                continue
            for _, attr_value in vars(klass).items():
                subs = getattr(attr_value, "_on_subscriptions", None)
                if subs is None:
                    continue
                for sub in subs:
                    if sub.event_type != event_name:
                        continue
                    if not re.search(sub.action_filter, class_name):
                        continue
                    # attr_value — unbound method из cls.__dict__,
                    # вызывающий код должен передать self (plugin instance)
                    handlers.append((attr_value, sub.ignore_exceptions))

        return handlers
