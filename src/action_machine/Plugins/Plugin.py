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
он использует внешнее хранилище, переданное через конструктор:

    class MetricsPlugin(Plugin):
        def __init__(self, storage: MetricsStorage):
            self._storage = storage  # внешнее хранилище

═══════════════════════════════════════════════════════════════════════════════
СИГНАТУРА ОБРАБОТЧИКОВ
═══════════════════════════════════════════════════════════════════════════════

Все обработчики плагинов обязаны иметь сигнатуру с 4 параметрами:

    async def handler(self, state, event, log) → state

    - self   — экземпляр плагина.
    - state  — текущее per-request состояние плагина (из get_initial_state()
               или обновлённое предыдущим обработчиком).
    - event  — объект PluginEvent с данными о событии (имя действия,
               параметры, результат, длительность и т.д.).
    - log    — ScopedLogger, привязанный к scope плагина. Scope содержит
               поля: machine, mode, plugin, action, event, nest_level.
               Все поля доступны в шаблонах через {%scope.*}.

Обработчик обязан вернуть обновлённое состояние.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА ИНТЕГРАЦИИ
═══════════════════════════════════════════════════════════════════════════════

    class CounterPlugin(Plugin):
        async def get_initial_state(self) -> dict:
            return {"count": 0}

        @on("global_finish", ".*")
        async def count_call(self, state, event, log):
            state["count"] += 1
            await log.info("Вызовов: {%var.count}", count=state["count"])
            return state

    # Декоратор @on записывает SubscriptionInfo в method._on_subscriptions.
    # MetadataBuilder собирает подписки в ClassMetadata.subscriptions.
    # PluginRunContext маршрутизирует события к подписанным методам,
    # создаёт ScopedLogger и передаёт его как параметр log.

═══════════════════════════════════════════════════════════════════════════════
МЕТОД get_handlers()
═══════════════════════════════════════════════════════════════════════════════

Метод get_handlers(event_name, class_name) сканирует MRO класса плагина,
ищет методы с атрибутом _on_subscriptions и для каждой подписки проверяет:
- Совпадает ли event_type с event_name.
- Совпадает ли action_filter (regex) с class_name.

Возвращает список кортежей (handler, ignore_exceptions), где handler —
unbound-метод из cls.__dict__. Вызывающий код передаёт self (экземпляр
плагина) при вызове.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    # Простой плагин-счётчик
    class SimpleCounter(Plugin):
        async def get_initial_state(self) -> dict:
            return {"total": 0}

        @on("global_finish", ".*")
        async def track(self, state, event, log):
            state["total"] += 1
            await log.info("Всего вызовов: {%var.total}", total=state["total"])
            return state

    # Плагин аудита
    class AuditPlugin(Plugin):
        async def get_initial_state(self) -> dict:
            return {"actions": []}

        @on("global_start", ".*")
        async def on_start(self, state, event, log):
            await log.info(
                "[{%scope.plugin}] Действие {%scope.action} начато "
                "на уровне {%scope.nest_level}"
            )
            return state

        @on("global_finish", ".*")
        async def on_finish(self, state, event, log):
            state["actions"].append(event.action_name)
            await log.info(
                "[{%scope.plugin}] Действие {%scope.action} завершено "
                "за {%var.duration}с",
                duration=event.duration,
            )
            return state

    # Плагин с фильтром по имени действия
    class OrderMetrics(Plugin):
        async def get_initial_state(self) -> dict:
            return {}

        @on("global_finish", ".*CreateOrder.*")
        async def track_orders(self, state, event, log):
            await log.info("Заказ создан: {%scope.action}")
            return state

    # Регистрация плагинов в машине
    machine = ActionProductMachine(
        mode="production",
        plugins=[SimpleCounter(), AuditPlugin(), OrderMetrics()],
    )
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

    Плагины не хранят per-request состояние в атрибутах экземпляра.
    Всё состояние управляется через PluginRunContext.
    """

    @abstractmethod
    async def get_initial_state(self) -> object:
        """
        Возвращает начальное состояние плагина для одного вызова run().

        Вызывается машиной (через PluginCoordinator.create_run_context())
        перед первым событием каждого run(). Возвращаемое значение
        может быть любого типа (обычно dict или пользовательский объект).

        Состояние передаётся обработчикам как первый аргумент state,
        и каждый обработчик обязан вернуть обновлённое состояние.

        Возвращает:
            Начальное состояние для текущего запуска. Тип определяется
            конкретным плагином.
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
              Сигнатура: (self, state, event, log).
            - ignore_exceptions: флаг из @on — если True, ошибка
              обработчика подавляется; если False — пробрасывается.
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
