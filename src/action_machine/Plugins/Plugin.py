# src/action_machine/Plugins/Plugin.py
"""
Базовый класс для всех плагинов ActionMachine.

Плагины определяют обработчики событий с помощью декоратора @on.
Каждый плагин должен реализовать асинхронный метод get_initial_state,
который возвращает начальное состояние для одного запуска действия.

Обработчики помечаются декоратором @on и записывают SubscriptionInfo
в method._on_subscriptions. MetadataBuilder собирает эти подписки
в ClassMetadata.subscriptions при первом обращении через GateCoordinator.

PluginCoordinator отвечает за маршрутизацию событий к подписанным методам.

Плагины не должны хранить состояние в атрибутах экземпляра,
поскольку оно должно быть изолировано для каждого вызова run.
Вместо этого состояние управляется машиной и передаётся через
параметр state каждому обработчику.

Все методы-обработчики должны быть асинхронными (определены с async def),
даже если они не содержат await, потому что машина вызывает их с await.
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

    Методы-обработчики помечаются декоратором @on из модуля Decorators.
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
        ...

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
            for attr_name, attr_value in vars(klass).items():
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
