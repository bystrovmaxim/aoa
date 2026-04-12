# src/action_machine/plugins/__init__.py
"""
Пакет плагинов ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Содержит полную подсистему плагинов для ActionMachine. Плагины позволяют
расширять поведение машины без изменения ядра: подсчёт вызовов, метрики,
аудит, логирование побочных эффектов, мониторинг компенсации (Saga) и т.д.

═══════════════════════════════════════════════════════════════════════════════
ТИПОБЕЗОПАСНАЯ ПОДПИСКА ЧЕРЕЗ КЛАССЫ СОБЫТИЙ
═══════════════════════════════════════════════════════════════════════════════

Плагины подписываются на события через декоратор @on, принимающий класс
события из иерархии BasePluginEvent как первый аргумент:

    @on(GlobalFinishEvent)                — только global_finish
    @on(GlobalLifecycleEvent)             — global_start + global_finish
    @on(AspectEvent)                      — все before/after всех аспектов
    @on(AfterRegularAspectEvent)          — только after regular-аспектов
    @on(CompensateFailedEvent)            — только сбои компенсаторов
    @on(SagaRollbackCompletedEvent)       — только конец размотки стека
    @on(UnhandledErrorEvent)              — ошибки без @on_error обработчика

Опечатка в имени класса → ImportError при импорте модуля, а не молчаливый
баг в рантайме. IDE автодополняет имена классов и проверяет поля событий.

═══════════════════════════════════════════════════════════════════════════════
ИЕРАРХИЯ КЛАССОВ СОБЫТИЙ
═══════════════════════════════════════════════════════════════════════════════

    BasePluginEvent                              — корень, общие поля
    ├── GlobalLifecycleEvent                     — группа: start + finish
    │   ├── GlobalStartEvent                     — старт конвейера
    │   └── GlobalFinishEvent                    — финиш (+ result, duration_ms)
    ├── AspectEvent                              — группа: все аспектные события
    │   ├── RegularAspectEvent                   — группа: regular-аспекты
    │   │   ├── BeforeRegularAspectEvent         — перед regular
    │   │   └── AfterRegularAspectEvent          — после regular (+ aspect_result)
    │   ├── SummaryAspectEvent                   — группа: summary-аспекты
    │   │   ├── BeforeSummaryAspectEvent         — перед summary
    │   │   └── AfterSummaryAspectEvent          — после summary (+ result)
    │   ├── OnErrorAspectEvent                   — группа: on_error обработчики
    │   │   ├── BeforeOnErrorAspectEvent         — перед on_error (+ error)
    │   │   └── AfterOnErrorAspectEvent          — после on_error (+ handler_result)
    │   └── CompensateAspectEvent                — группа: события отдельных компенсаторов
    │       ├── BeforeCompensateAspectEvent      — перед компенсатором (+ error, states)
    │       ├── AfterCompensateAspectEvent       — после успешного компенсатора (+ duration_ms)
    │       └── CompensateFailedEvent            — сбой компенсатора (+ compensator_error)
    ├── SagaEvent                                — группа: события размотки стека Saga
    │   ├── SagaRollbackStartedEvent             — начало размотки стека
    │   └── SagaRollbackCompletedEvent           — конец размотки (+ итоги)
    ├── ErrorEvent                               — группа: ошибки конвейера
    │   └── UnhandledErrorEvent                  — ошибка без @on_error обработчика
    └── (будущие группы расширяются наследованием)

Каждый класс содержит РОВНО те поля, которые имеют смысл для данного типа
события. GlobalStartEvent не имеет result, AfterRegularAspectEvent содержит
aspect_result и duration_ms. Групповые классы (GlobalLifecycleEvent,
AspectEvent, SagaEvent) не создаются машиной напрямую — они существуют
только для групповой подписки через isinstance.

═══════════════════════════════════════════════════════════════════════════════
СОБЫТИЯ КОМПЕНСАЦИИ (SAGA)
═══════════════════════════════════════════════════════════════════════════════

События компенсации делятся на два уровня:

1. УРОВЕНЬ ВСЕЙ РАЗМОТКИ (SagaEvent):
   SagaRollbackStartedEvent   — эмитируется один раз перед началом размотки.
   SagaRollbackCompletedEvent — эмитируется один раз после завершения размотки.
   Содержит итоги: succeeded, failed, skipped, duration_ms, failed_aspects.

2. УРОВЕНЬ ОДНОГО КОМПЕНСАТОРА (CompensateAspectEvent):
   BeforeCompensateAspectEvent — перед каждым компенсатором.
   AfterCompensateAspectEvent  — после успешного компенсатора.
   CompensateFailedEvent       — при сбое компенсатора.

CompensateFailedEvent — отдельный тип (а не поле в AfterCompensateAspectEvent),
потому что сбой компенсатора — аварийная ситуация, требующая отдельной
реакции плагина мониторинга. Отдельный тип позволяет подписаться точечно:
@on(CompensateFailedEvent) — только сбои, без потока успешных откатов.

Ошибки компенсаторов полностью подавляются внутри _rollback_saga().
Информация о сбоях доступна ТОЛЬКО через CompensateFailedEvent.

═══════════════════════════════════════════════════════════════════════════════
ФИЛЬТРЫ В ДЕКОРАТОРЕ @on
═══════════════════════════════════════════════════════════════════════════════

Помимо event_class, декоратор @on принимает опциональные фильтры:

    @on(
        GlobalFinishEvent,
        action_class=OrderAction,              # фильтр по типу действия
        action_name_pattern=r"orders\\..*",    # regex по имени действия
        aspect_name_pattern=r"validate_.*",    # regex по имени аспекта
        nest_level=0,                          # фильтр по вложенности
        domain=OrdersDomain,                   # фильтр по домену
        predicate=lambda e: e.duration_ms > 1000,  # произвольный фильтр
        ignore_exceptions=True,                # подавление ошибок
    )

Внутри одного @on фильтры проверяются с AND-логикой: все указанные
должны пройти одновременно. Неуказанные (None) пропускаются.

OR-логика реализуется между несколькими @on на одном методе:

    @on(GlobalStartEvent)               # ИЛИ start
    @on(GlobalFinishEvent)              # ИЛИ finish
    async def on_lifecycle(self, state, event: GlobalLifecycleEvent, log):
        ...

═══════════════════════════════════════════════════════════════════════════════
КОМПОНЕНТЫ
═══════════════════════════════════════════════════════════════════════════════

Классы событий (events.py):
- BasePluginEvent — корневой класс всех событий. Содержит action_class,
  action_name, nest_level, context, params.
- GlobalLifecycleEvent, GlobalStartEvent, GlobalFinishEvent — события
  жизненного цикла действия.
- AspectEvent — групповой класс аспектных событий. Добавляет aspect_name,
  state_snapshot.
- RegularAspectEvent, BeforeRegularAspectEvent, AfterRegularAspectEvent —
  события regular-аспектов.
- SummaryAspectEvent, BeforeSummaryAspectEvent, AfterSummaryAspectEvent —
  события summary-аспектов.
- OnErrorAspectEvent, BeforeOnErrorAspectEvent, AfterOnErrorAspectEvent —
  события обработчиков @on_error.
- CompensateAspectEvent, BeforeCompensateAspectEvent,
  AfterCompensateAspectEvent, CompensateFailedEvent — события отдельных
  компенсаторов (Saga). Эмитируются из _rollback_saga() при размотке
  стека в обратном порядке.
- SagaEvent, SagaRollbackStartedEvent, SagaRollbackCompletedEvent —
  события уровня всей размотки стека. Содержат итоги: succeeded, failed,
  skipped, duration_ms.
- ErrorEvent, UnhandledErrorEvent — ошибки конвейера.

Подписка и конфигурация:
- SubscriptionInfo — frozen-датакласс конфигурации одной подписки. Содержит
  event_class, все фильтры, ignore_exceptions и method_name.
  Компилирует regex при создании. Предоставляет методы matches_*()
  для проверки каждого фильтра.
- on — декоратор для подписки async-метода плагина на событие.
  Принимает event_class и опциональные фильтры. Создаёт SubscriptionInfo
  и добавляет в method._on_subscriptions.

Инфраструктура:
- OnIntent — маркерный миксин, обозначающий поддержку @on.
  Наследуется Plugin. MetadataBuilder проверяет наличие при сборке.
- Plugin — абстрактный базовый класс плагинов. Каждый плагин реализует
  get_initial_state() и определяет @on-обработчики. Метод get_handlers()
  находит подписки, совпавшие с событием по event_class (шаг 1 фильтрации).
- PluginCoordinator — stateless-координатор. Хранит список Plugin,
  создаёт изолированный PluginRunContext для каждого вызова run().
- PluginRunContext — изолированный контекст для одного run(). Хранит
  per-request состояния плагинов. Метод emit_event() принимает объект
  события, проверяет полную цепочку фильтров (7 шагов) и доставляет
  событие обработчикам.

═══════════════════════════════════════════════════════════════════════════════
СИГНАТУРА ОБРАБОТЧИКОВ
═══════════════════════════════════════════════════════════════════════════════

Все обработчики плагинов обязаны иметь сигнатуру с 4 параметрами:

    async def handler(self, state, event: EventClass, log) -> state

    - self   — экземпляр плагина.
    - state  — текущее per-request состояние плагина.
    - event  — объект события из иерархии BasePluginEvent. Аннотация типа
               может быть конкретным классом (GlobalFinishEvent), групповым
               (AspectEvent) или базовым (BasePluginEvent). MetadataBuilder
               проверяет совместимость: event_class из @on должен быть
               подклассом аннотации event.
    - log    — ScopedLogger, привязанный к scope плагина.

═══════════════════════════════════════════════════════════════════════════════
ЖИЗНЕННЫЙ ЦИКЛ ПЛАГИНОВ В РАМКАХ ОДНОГО ЗАПРОСА
═══════════════════════════════════════════════════════════════════════════════

    1. ActionProductMachine._run_internal() вызывает
       plugin_coordinator.create_run_context().
    2. create_run_context() вызывает get_initial_state() для каждого
       плагина и создаёт PluginRunContext с начальными состояниями.
    3. Машина создаёт типизированные события (GlobalStartEvent,
       BeforeRegularAspectEvent, SagaRollbackStartedEvent и т.д.)
       в ключевых точках конвейера.
    4. Каждое событие передаётся в plugin_ctx.emit_event(event, ...).
    5. PluginRunContext проверяет цепочку фильтров (7 шагов) для каждой
       подписки каждого плагина.
    6. Прошедшие обработчики получают ScopedLogger и вызываются.
    7. Каждый обработчик получает текущее состояние и возвращает новое.
    8. По завершении run() контекст уничтожается.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР: ПЛАГИН МЕТРИК С МОНИТОРИНГОМ КОМПЕНСАЦИИ
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.logging.channel import Channel
    from action_machine.plugins import Plugin, on
    from action_machine.plugins.events import (
        GlobalFinishEvent,
        UnhandledErrorEvent,
        CompensateFailedEvent,
        SagaRollbackCompletedEvent,
    )

    class MetricsPlugin(Plugin):

        async def get_initial_state(self) -> dict:
            return {"total": 0, "slow": 0, "saga_failures": 0}

        @on(GlobalFinishEvent)
        async def on_track(self, state, event: GlobalFinishEvent, log):
            state["total"] += 1
            if event.duration_ms > 1000:
                state["slow"] += 1
                await log.warning(
                    Channel.business,
                    "Медленное действие: {%var.name} за {%var.ms}мс",
                    name=event.action_name,
                    ms=event.duration_ms,
                )
            return state

        @on(UnhandledErrorEvent)
        async def on_error(self, state, event: UnhandledErrorEvent, log):
            await log.critical(
                Channel.error,
                "Необработанная ошибка: {%var.err}",
                err=str(event.error),
            )
            return state

        @on(CompensateFailedEvent)
        async def on_compensate_failed(self, state, event: CompensateFailedEvent, log):
            await log.critical(
                Channel.error,
                "Сбой компенсатора {%var.comp} для {%var.aspect}: {%var.err}",
                comp=event.compensator_name,
                aspect=event.failed_for_aspect,
                err=str(event.compensator_error),
            )
            state["saga_failures"] += 1
            return state

        @on(SagaRollbackCompletedEvent)
        async def on_saga_done(self, state, event: SagaRollbackCompletedEvent, log):
            await log.warning(
                Channel.business,
                "Размотка: {%var.ok} ок, {%var.fail} сбоев за {%var.ms}мс",
                ok=event.succeeded,
                fail=event.failed,
                ms=event.duration_ms,
            )
            return state
"""

from .events import (
    AfterCompensateAspectEvent,
    AfterOnErrorAspectEvent,
    AfterRegularAspectEvent,
    AfterSummaryAspectEvent,
    AspectEvent,
    BasePluginEvent,
    BeforeCompensateAspectEvent,
    BeforeOnErrorAspectEvent,
    BeforeRegularAspectEvent,
    BeforeSummaryAspectEvent,
    CompensateAspectEvent,
    CompensateFailedEvent,
    ErrorEvent,
    GlobalFinishEvent,
    GlobalLifecycleEvent,
    GlobalStartEvent,
    OnErrorAspectEvent,
    RegularAspectEvent,
    SagaEvent,
    SagaRollbackCompletedEvent,
    SagaRollbackStartedEvent,
    SummaryAspectEvent,
    UnhandledErrorEvent,
)
from .on_decorator import on
from .on_intent import OnIntent
from .plugin import Plugin
from .plugin_coordinator import PluginCoordinator
from .plugin_run_context import PluginRunContext
from .subscription_info import SubscriptionInfo

__all__ = [
    "AfterCompensateAspectEvent",
    "AfterOnErrorAspectEvent",
    "AfterRegularAspectEvent",
    "AfterSummaryAspectEvent",
    "AspectEvent",
    # Классы событий — корневые и групповые
    "BasePluginEvent",
    "BeforeCompensateAspectEvent",
    "BeforeOnErrorAspectEvent",
    "BeforeRegularAspectEvent",
    "BeforeSummaryAspectEvent",
    "CompensateAspectEvent",
    "CompensateFailedEvent",
    "ErrorEvent",
    "GlobalFinishEvent",
    "GlobalLifecycleEvent",
    # Классы событий — конкретные (leaf)
    "GlobalStartEvent",
    "OnErrorAspectEvent",
    # Инфраструктура
    "OnIntent",
    "Plugin",
    "PluginCoordinator",
    "PluginRunContext",
    "RegularAspectEvent",
    "SagaEvent",
    "SagaRollbackCompletedEvent",
    "SagaRollbackStartedEvent",
    # Подписка и конфигурация
    "SubscriptionInfo",
    "SummaryAspectEvent",
    "UnhandledErrorEvent",
    "on",
]
