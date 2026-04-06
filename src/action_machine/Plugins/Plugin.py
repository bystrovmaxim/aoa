# src/action_machine/plugins/plugin.py
"""
Базовый класс для всех плагинов ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Plugin — абстрактный базовый класс, от которого наследуются все плагины
системы. Плагины расширяют поведение машины без изменения ядра: подсчёт
вызовов, сбор метрик, аудит, логирование побочных эффектов и т.д.

Каждый плагин определяет обработчики событий с помощью декоратора @on.
Обработчики реагируют на события жизненного цикла действия: global_start,
global_finish, before:{aspect}, after:{aspect}.

═══════════════════════════════════════════════════════════════════════════════
СОСТОЯНИЕ ПЛАГИНА
═══════════════════════════════════════════════════════════════════════════════

Плагины НЕ хранят состояние в атрибутах экземпляра. Состояние per-request
управляется машиной через PluginRunContext:

1. В начале каждого run() машина вызывает get_initial_state() для
   каждого плагина и сохраняет результат в PluginRunContext.
2. При каждом событии обработчик получает текущее состояние через
   параметр state и возвращает обновлённое.
3. По завершении run() контекст уничтожается вместе с состояниями.

Если плагину нужно накапливать данные между запросами (метрики, счётчики),
он использует внешнее хранилище, переданное через конструктор.

═══════════════════════════════════════════════════════════════════════════════
СИГНАТУРА ОБРАБОТЧИКОВ
═══════════════════════════════════════════════════════════════════════════════

Все обработчики плагинов обязаны иметь сигнатуру с 4 параметрами:

    async def handler(self, state, event, log) → state

    - self   — экземпляр плагина.
    - state  — текущее per-request состояние плагина.
    - event  — объект PluginEvent с данными о событии.
    - log    — ScopedLogger, привязанный к scope плагина.

Обработчик обязан вернуть обновлённое состояние.
"""

import re
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any


class Plugin(ABC):
    """
    Абстрактный базовый класс для всех плагинов ActionMachine.

    Каждый плагин реализует:
    - get_initial_state() — возвращает начальное per-request состояние.
    - Один или несколько @on-обработчиков событий с сигнатурой
      (self, state, event, log).
    """

    @abstractmethod
    async def get_initial_state(self) -> object:
        """
        Возвращает начальное состояние плагина для одного вызова run().

        Вызывается машиной (через PluginCoordinator.create_run_context())
        перед первым событием каждого run().
        """

    def get_handlers(
        self, event_name: str, class_name: str,
    ) -> list[tuple[Callable[..., Any], bool]]:
        """
        Возвращает список подходящих обработчиков для события и действия.

        Сканирует MRO класса плагина, ищет методы с атрибутом
        _on_subscriptions, и для каждой подписки проверяет:
        - event_type совпадает с event_name.
        - action_filter (regex) совпадает с class_name.

        Аргументы:
            event_name: имя события (например, 'global_finish',
                        'before:validate', 'after:process_payment').
            class_name: полное имя класса действия (включая модуль).

        Возвращает:
            Список кортежей (handler, ignore_exceptions):
            - handler: unbound-метод (требует передачи self при вызове).
            - ignore_exceptions: флаг из @on.
        """
        handlers: list[tuple[Callable[..., Any], bool]] = []

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
                    handlers.append((attr_value, sub.ignore_exceptions))

        return handlers