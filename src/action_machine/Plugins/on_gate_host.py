# src/action_machine/plugins/on_gate_host.py
"""
Модуль: OnGateHost — маркерный миксин для декоратора @on.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

OnGateHost — миксин-маркер, который обозначает, что класс поддерживает
декоратор @on для подписки методов на типизированные события ActionMachine.
Используется в классе Plugin и его наследниках.

Наличие OnGateHost в MRO класса документирует контракт:
«этот класс может содержать методы-обработчики событий (@on)».

MetadataBuilder при сборке метаданных проверяет: если класс содержит
методы с _on_subscriptions (подписки через @on), класс обязан
наследовать OnGateHost. Без него — TypeError.

═══════════════════════════════════════════════════════════════════════════════
ТИПОБЕЗОПАСНАЯ ПОДПИСКА
═══════════════════════════════════════════════════════════════════════════════

Декоратор @on принимает класс события из иерархии BasePluginEvent как
первый аргумент. Подписка срабатывает для указанного класса и всех
его наследников через isinstance-проверку в PluginRunContext.

Дополнительные фильтры (action_class, action_name_pattern,
aspect_name_pattern, nest_level, domain, predicate) сужают выборку
с AND-логикой внутри одного @on. OR-логика реализуется между
несколькими @on на одном методе.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА
═══════════════════════════════════════════════════════════════════════════════

    class Plugin(OnGateHost):           ← маркер: разрешает @on на методах
        async def get_initial_state(self) -> Any:
            ...

    class CounterPlugin(Plugin):

        async def get_initial_state(self) -> dict:
            return {}

        @on(GlobalFinishEvent, ignore_exceptions=False)
        async def on_count_call(self, state, event: GlobalFinishEvent, log):
            state[event.action_name] = state.get(event.action_name, 0) + 1
            return state

    # Декоратор @on записывает в метод:
    #   method._on_subscriptions = [SubscriptionInfo(
    #       event_class=GlobalFinishEvent,
    #       method_name="on_count_call",
    #       ignore_exceptions=False,
    #   )]

    # MetadataBuilder / SubscriptionGateHostInspector собирают subscriptions (валидация);
    #   снимок подписок — GateCoordinator.get_subscriptions().

    # MetadataBuilder → require_*_gate_host_marker + validate_subscriptions
    #   Проверяет: есть подписки → issubclass(cls, OnGateHost) → OK.

    # PluginRunContext.emit_event(event):
    #   plugin.get_handlers(event) → находит обработчики по isinstance
    #   _matches_all_filters(event, sub) → проверяет шаги 2–7
    #   handler(plugin, state, event, log) → вызов

═══════════════════════════════════════════════════════════════════════════════
ЕДИНООБРАЗИЕ С ДРУГИМИ ГЕЙТ-МИКСИНАМИ
═══════════════════════════════════════════════════════════════════════════════

Все гейт-миксины ActionMachine следуют одному паттерну: пустой класс
без логики, служащий проверочным маркером для issubclass(). OnGateHost
находится в ряду с RoleGateHost, AspectGateHost, CheckerGateHost,
ActionMetaGateHost, ConnectionGateHost, OnErrorGateHost,
ContextRequiresGateHost и DescribedFieldsGateHost.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    # Plugin уже наследует OnGateHost — любой плагин поддерживает @on:

    class MetricsPlugin(Plugin):
        async def get_initial_state(self) -> dict:
            return {"total": 0, "errors": 0}

        @on(GlobalFinishEvent)
        async def on_track_total(self, state, event: GlobalFinishEvent, log):
            state["total"] += 1
            return state

        @on(UnhandledErrorEvent)
        async def on_track_errors(self, state, event: UnhandledErrorEvent, log):
            state["errors"] += 1
            return state

        @on(AfterRegularAspectEvent, aspect_name_pattern=r"validate_.*")
        async def on_validation_done(self, state, event: AfterRegularAspectEvent, log):
            await log.info("Валидация завершена: {%var.name}", name=event.aspect_name)
            return state
"""

from __future__ import annotations

import inspect
from typing import Any

from action_machine.plugins.events import BasePluginEvent
from action_machine.plugins.subscription_info import SubscriptionInfo


class OnGateHost:
    """
    Маркерный миксин, обозначающий поддержку декоратора @on.

    Класс, наследующий OnGateHost, может содержать методы, декорированные
    @on для подписки на типизированные события ActionMachine из иерархии
    BasePluginEvent (GlobalStartEvent, GlobalFinishEvent,
    AfterRegularAspectEvent, UnhandledErrorEvent и т.д.).

    MetadataBuilder валидирует подписки из method._on_subscriptions;
    снимок — ``GateCoordinator.get_subscriptions()``. PluginRunContext
    маршрутизирует события через цепочку фильтров.

    Миксин не содержит логики, полей или методов. Его функция —
    документировать контракт и обеспечивать единообразие с другими
    гейт-миксинами.

    Атрибуты уровня класса (создаются динамически декоратором на методах):
        method._on_subscriptions : list[SubscriptionInfo]
            Список объектов SubscriptionInfo, записываемый декоратором @on
            в метод. Каждый объект содержит:
            - event_class: type[BasePluginEvent] — тип события
            - action_class: tuple[type, ...] | None — фильтр по типу действия
            - action_name_pattern: str | None — regex по имени действия
            - aspect_name_pattern: str | None — regex по имени аспекта
            - nest_level: tuple[int, ...] | None — фильтр по вложенности
            - domain: type | None — фильтр по домену
            - predicate: Callable | None — произвольный фильтр
            - ignore_exceptions: bool — подавление ошибок обработчика
            - method_name: str — имя метода-обработчика
            Читается collect_subscriptions при сборке (валидация).
    """

    pass


def require_on_gate_host_marker(cls: type, subscriptions: list[Any]) -> None:
    """Есть подписки @on → класс должен наследовать OnGateHost."""
    if subscriptions and not issubclass(cls, OnGateHost):
        event_classes = ", ".join(
            s.event_class.__name__ if isinstance(s, SubscriptionInfo) else str(s)
            for s in subscriptions
        )
        raise TypeError(
            f"Класс {cls.__name__} содержит подписки на события ({event_classes}), "
            f"но не наследует OnGateHost. Декоратор @on разрешён только "
            f"на классах, наследующих OnGateHost. Используйте Plugin "
            f"или добавьте OnGateHost в цепочку наследования."
        )


def _extract_event_annotation(cls: type, method_name: str) -> type | None:
    func = None
    for klass in cls.__mro__:
        if method_name in vars(klass):
            func = vars(klass)[method_name]
            break

    if func is None:
        return None

    try:
        sig = inspect.signature(func)
    except (ValueError, TypeError):
        return None

    params_list = list(sig.parameters.values())

    if len(params_list) < 3:
        return None

    event_param = params_list[2]
    annotation = event_param.annotation
    if annotation is inspect.Parameter.empty:
        return None

    if isinstance(annotation, type) and issubclass(annotation, BasePluginEvent):
        return annotation

    return None


def validate_subscriptions(
    cls: type,
    subscriptions: list[SubscriptionInfo],
) -> None:
    """Совместимость event_class из @on с аннотацией параметра event."""
    for sub in subscriptions:
        if not isinstance(sub, SubscriptionInfo):
            continue

        annotation = _extract_event_annotation(cls, sub.method_name)
        if annotation is None:
            continue

        if not issubclass(sub.event_class, annotation):
            raise TypeError(
                f"Класс {cls.__name__}: метод '{sub.method_name}' подписан "
                f"на {sub.event_class.__name__} через @on, но параметр event "
                f"аннотирован как {annotation.__name__}. Тип "
                f"{sub.event_class.__name__} не является подклассом "
                f"{annotation.__name__}, поэтому обработчик может получить "
                f"событие без ожидаемых полей. Измените аннотацию на "
                f"{sub.event_class.__name__} или более общий тип "
                f"(например, BasePluginEvent)."
            )
