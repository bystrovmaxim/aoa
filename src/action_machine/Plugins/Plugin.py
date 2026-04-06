# src/action_machine/plugins/plugin.py
"""
Plugin — абстрактный базовый класс для всех плагинов ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Plugin — абстрактный базовый класс, от которого наследуются все плагины
системы. Плагины расширяют поведение машины без изменения ядра: подсчёт
вызовов, сбор метрик, аудит, логирование побочных эффектов и т.д.

Каждый плагин определяет обработчики событий с помощью декоратора @on.
Обработчики реагируют на события жизненного цикла действия, представленные
типизированными классами из иерархии BasePluginEvent: GlobalStartEvent,
GlobalFinishEvent, BeforeRegularAspectEvent, AfterRegularAspectEvent и т.д.

═══════════════════════════════════════════════════════════════════════════════
СОСТОЯНИЕ ПЛАГИНА
═══════════════════════════════════════════════════════════════════════════════

Плагины НЕ хранят per-request состояние в атрибутах экземпляра.
Состояние per-request управляется машиной через PluginRunContext:

1. В начале каждого run() машина вызывает get_initial_state() для
   каждого плагина и сохраняет результат в PluginRunContext.
2. При каждом событии обработчик получает текущее состояние через
   параметр state и возвращает обновлённое.
3. По завершении run() контекст уничтожается вместе с состояниями.

Если плагину нужно накапливать данные между запросами (метрики, счётчики),
он использует внешнее хранилище, переданное через конструктор плагина.

═══════════════════════════════════════════════════════════════════════════════
СИГНАТУРА ОБРАБОТЧИКОВ
═══════════════════════════════════════════════════════════════════════════════

Все обработчики плагинов обязаны иметь сигнатуру с 4 параметрами:

    async def handler(self, state, event: EventClass, log) -> state

    - self   — экземпляр плагина.
    - state  — текущее per-request состояние плагина.
    - event  — объект события из иерархии BasePluginEvent.
               Аннотация типа может быть конкретным классом
               (GlobalFinishEvent), групповым (AspectEvent) или
               базовым (BasePluginEvent). MetadataBuilder проверяет
               совместимость: event_class из @on должен быть подклассом
               аннотации event.
    - log    — ScopedLogger, привязанный к scope плагина.

Обработчик обязан вернуть обновлённое состояние.

═══════════════════════════════════════════════════════════════════════════════
ПОДПИСКА ЧЕРЕЗ ИЕРАРХИЮ СОБЫТИЙ
═══════════════════════════════════════════════════════════════════════════════

Декоратор @on принимает класс события как первый аргумент. Подписка
срабатывает для указанного класса и всех его наследников через
isinstance-проверку:

    @on(BasePluginEvent)              — все события системы
    @on(GlobalLifecycleEvent)         — global_start + global_finish
    @on(GlobalFinishEvent)            — только global_finish
    @on(AspectEvent)                  — все before/after всех аспектов
    @on(AfterRegularAspectEvent)      — только after regular-аспектов

Дополнительные фильтры (action_class, action_name_pattern,
aspect_name_pattern, nest_level, domain, predicate) сужают выборку
с AND-логикой внутри одного @on.

═══════════════════════════════════════════════════════════════════════════════
ПОИСК ОБРАБОТЧИКОВ
═══════════════════════════════════════════════════════════════════════════════

Метод get_handlers() сканирует MRO класса плагина, находит методы
с атрибутом _on_subscriptions и возвращает список подписок
(SubscriptionInfo) с привязанными методами. PluginRunContext вызывает
get_handlers() при каждом emit_event() и проверяет каждую подписку
через цепочку фильтров SubscriptionInfo.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ПЛАГИНА
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.plugins.events import (
        GlobalFinishEvent,
        AfterRegularAspectEvent,
        UnhandledErrorEvent,
    )

    class MetricsPlugin(Plugin):
        async def get_initial_state(self) -> dict:
            return {"total": 0, "slow": 0, "errors": []}

        @on(GlobalFinishEvent)
        async def on_track_total(self, state, event: GlobalFinishEvent, log):
            state["total"] += 1
            if event.duration_ms > 1000:
                state["slow"] += 1
            return state

        @on(AfterRegularAspectEvent, aspect_name_pattern=r"validate_.*")
        async def on_validation_done(self, state, event: AfterRegularAspectEvent, log):
            await log.debug("Валидация завершена: {%var.name}", name=event.aspect_name)
            return state

        @on(UnhandledErrorEvent)
        async def on_unhandled_error(self, state, event: UnhandledErrorEvent, log):
            state["errors"].append(str(event.error))
            return state
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from action_machine.plugins.events import BasePluginEvent
from action_machine.plugins.on_gate_host import OnGateHost
from action_machine.plugins.subscription_info import SubscriptionInfo


class Plugin(OnGateHost, ABC):
    """
    Абстрактный базовый класс для всех плагинов ActionMachine.

    Каждый плагин реализует:
    - get_initial_state() — возвращает начальное per-request состояние.
    - Один или несколько @on-обработчиков событий с сигнатурой
      (self, state, event: EventClass, log).

    Метод get_handlers() возвращает все подписки плагина, подходящие
    для указанного события. PluginRunContext использует этот метод
    для маршрутизации событий.

    Плагин не хранит per-request состояния — оно управляется
    PluginRunContext. Атрибуты экземпляра используются только
    для конфигурации (внешнее хранилище, параметры и т.д.).
    """

    @abstractmethod
    async def get_initial_state(self) -> object:
        """
        Возвращает начальное состояние плагина для одного вызова run().

        Вызывается машиной (через PluginCoordinator.create_run_context())
        перед первым событием каждого run(). Возвращённый объект
        передаётся в обработчики через параметр state.

        Тип состояния определяется плагином: dict, dataclass, любой объект.
        Единственное требование — обработчик должен вернуть обновлённое
        состояние того же типа.

        Возвращает:
            Начальное per-request состояние.
        """

    def get_handlers(
        self,
        event: BasePluginEvent,
    ) -> list[tuple[Callable[..., Any], SubscriptionInfo]]:
        """
        Возвращает список обработчиков, чьи подписки совпали с событием.

        Сканирует MRO класса плагина, находит методы с атрибутом
        _on_subscriptions. Для каждой подписки (SubscriptionInfo) проверяет
        совпадение event_class через isinstance. Остальные фильтры
        (action_class, action_name_pattern и т.д.) проверяются вызывающим
        кодом (PluginRunContext) через методы SubscriptionInfo.

        Здесь выполняется ТОЛЬКО проверка event_class — самая дешёвая,
        отсекающая ~90% подписок. Это разделение ответственности:
        Plugin.get_handlers() находит кандидатов по типу события,
        PluginRunContext проверяет остальные фильтры.

        Аргументы:
            event: объект события из иерархии BasePluginEvent.

        Возвращает:
            Список кортежей (handler, subscription):
            - handler: unbound-метод (требует передачи self при вызове).
            - subscription: SubscriptionInfo с полной конфигурацией фильтров.
        """
        handlers: list[tuple[Callable[..., Any], SubscriptionInfo]] = []

        for klass in type(self).__mro__:
            if klass is object:
                continue

            for _, attr_value in vars(klass).items():
                subs = getattr(attr_value, "_on_subscriptions", None)
                if subs is None:
                    continue

                for sub in subs:
                    if not isinstance(sub, SubscriptionInfo):
                        continue

                    # Шаг 1: проверка event_class через isinstance
                    if not sub.matches_event_class(event):
                        continue

                    handlers.append((attr_value, sub))

        return handlers
