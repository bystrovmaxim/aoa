# src/action_machine/intents/plugins/events.py
"""
Иерархия классов событий плагинной системы ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Модуль содержит полную иерархию frozen-датаклассов событий, которые
машина (ActionProductMachine) создаёт в ключевых точках конвейера
выполнения действия и доставляет обработчикам плагинов через
PluginRunContext.emit_event().

Каждый класс события содержит РОВНО те поля, которые имеют смысл
для данного типа события. GlobalStartEvent не имеет поля result
(результат ещё не известен), AfterRegularAspectEvent не имеет поля
error (ошибки перехватываются отдельным событием). Это устраняет
проблему единого PluginEvent с Optional-полями, где большинство
полей равны None для конкретного события.

═══════════════════════════════════════════════════════════════════════════════
ИЕРАРХИЯ
═══════════════════════════════════════════════════════════════════════════════

    BasePluginEvent                              — корень, общие поля
    ├── GlobalLifecycleEvent                     — группа: start + finish
    │   ├── GlobalStartEvent                     — старт конвейера
    │   └── GlobalFinishEvent                    — финиш (+ result, duration_ms)
    ├── AspectEvent                              — группа: все аспектные события
    │   ├── RegularAspectEvent                   — группа: regular-аспекты
    │   │   ├── BeforeRegularAspectEvent         — перед regular
    │   │   └── AfterRegularAspectEvent          — после regular (+ aspect_result, duration_ms)
    │   ├── SummaryAspectEvent                   — группа: summary-аспекты
    │   │   ├── BeforeSummaryAspectEvent         — перед summary
    │   │   └── AfterSummaryAspectEvent          — после summary (+ result, duration_ms)
    │   ├── OnErrorAspectEvent                   — группа: on_error аспекты
    │   │   ├── BeforeOnErrorAspectEvent         — перед on_error (+ error)
    │   │   └── AfterOnErrorAspectEvent          — после on_error (+ error, handler_result, duration_ms)
    │   └── CompensateAspectEvent                — группа: события отдельных компенсаторов
    │       ├── BeforeCompensateAspectEvent      — перед компенсатором (+ error, state_before, state_after)
    │       ├── AfterCompensateAspectEvent       — после успешного компенсатора (+ duration_ms)
    │       └── CompensateFailedEvent            — сбой компенсатора (+ compensator_error)
    ├── SagaEvent                                — группа: события размотки стека Saga
    │   ├── SagaRollbackStartedEvent             — начало размотки стека
    │   └── SagaRollbackCompletedEvent           — конец размотки (+ итоги)
    ├── ErrorEvent                               — группа: ошибки конвейера
    │   └── UnhandledErrorEvent                  — ошибка без @on_error обработчика
    └── (будущие группы расширяются наследованием)

═══════════════════════════════════════════════════════════════════════════════
ПОДПИСКА ЧЕРЕЗ ИЕРАРХИЮ
═══════════════════════════════════════════════════════════════════════════════

Иерархия позволяет подписываться на события с разной степенью детализации
через isinstance-проверку в цепочке фильтров PluginRunContext:

    @on(BasePluginEvent)              — все события системы
    @on(GlobalLifecycleEvent)         — global_start + global_finish
    @on(GlobalFinishEvent)            — только global_finish
    @on(AspectEvent)                  — все before/after всех типов аспектов
    @on(RegularAspectEvent)           — before + after regular-аспектов
    @on(AfterRegularAspectEvent)      — только after regular-аспектов
    @on(CompensateAspectEvent)        — все события отдельных компенсаторов
    @on(CompensateFailedEvent)        — только сбои компенсаторов
    @on(SagaEvent)                    — все saga-события (начало/конец размотки)
    @on(SagaRollbackStartedEvent)     — только начало размотки
    @on(SagaRollbackCompletedEvent)   — только конец размотки
    @on(ErrorEvent)                   — все ошибки конвейера

Групповые классы (GlobalLifecycleEvent, AspectEvent, RegularAspectEvent,
CompensateAspectEvent, SagaEvent) не создаются машиной напрямую — машина
всегда создаёт конкретные leaf-классы. Групповые классы существуют
только для подписки через isinstance.

═══════════════════════════════════════════════════════════════════════════════
СОБЫТИЯ КОМПЕНСАЦИИ (SAGA)
═══════════════════════════════════════════════════════════════════════════════

События компенсации делятся на два уровня:

1. УРОВЕНЬ ВСЕЙ РАЗМОТКИ (SagaEvent):
   SagaRollbackStartedEvent   — эмитируется один раз перед началом размотки.
   SagaRollbackCompletedEvent — эмитируется один раз после завершения размотки.
   Содержит итоги: сколько компенсаторов выполнено, сколько упало, сколько
   пропущено. Позволяет плагину мониторинга видеть общую картину отката.

2. УРОВЕНЬ ОДНОГО КОМПЕНСАТОРА (CompensateAspectEvent):
   BeforeCompensateAspectEvent — перед каждым компенсатором.
   AfterCompensateAspectEvent  — после успешного компенсатора.
   CompensateFailedEvent       — при сбое компенсатора.

CompensateFailedEvent — отдельный тип (а не поле в AfterCompensateAspectEvent),
потому что сбой компенсатора — аварийная ситуация, на которую плагин
мониторинга реагирует ИНАЧЕ, чем на успешную компенсацию. Отдельный тип
позволяет подписаться точечно: @on(CompensateFailedEvent) — только сбои,
без потока успешных откатов.

Ошибки компенсаторов полностью подавляются внутри _rollback_saga() —
они не прерывают размотку стека и не пробрасываются в @on_error.
Информация о сбоях доступна ТОЛЬКО через CompensateFailedEvent.

═══════════════════════════════════════════════════════════════════════════════
FROZEN-СЕМАНТИКА
═══════════════════════════════════════════════════════════════════════════════

Все классы событий — frozen dataclass (frozen=True). Плагины-наблюдатели
читают данные события, но не могут их модифицировать. Попытка записи
в поле → FrozenInstanceError.

Это следствие общего принципа ActionMachine: все core-типы данных
(Params, Result, State, Context, события) — frozen после создания.

═══════════════════════════════════════════════════════════════════════════════
ПОЛЯ action_class И action_name
═══════════════════════════════════════════════════════════════════════════════

Каждое событие содержит оба поля:

    action_class: type — тип действия для типобезопасной фильтрации
        через isinstance в цепочке фильтров PluginRunContext.
        Пример: action_class=CreateOrderAction.

    action_name: str — полное строковое имя действия (module.ClassName)
        для шаблонов логирования ({%event.action_name}) и regex-фильтрации
        через action_name_pattern в декораторе @on.
        Пример: action_name="orders.actions.CreateOrderAction".

═══════════════════════════════════════════════════════════════════════════════
ПОЛЕ state_snapshot
═══════════════════════════════════════════════════════════════════════════════

Аспектные события содержат поле state_snapshot: dict[str, object] | None —
снимок состояния конвейера на момент события. Это обычный dict, а не
BaseState, потому что плагин не должен иметь доступ к мутабельному
объекту конвейера. Снимок создаётся через state.to_dict() в машине.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР СОЗДАНИЯ СОБЫТИЯ МАШИНОЙ
═══════════════════════════════════════════════════════════════════════════════

    # Global lifecycle: PluginEmitSupport.emit_global_start / emit_global_finish
    # build the same events and call plugin_ctx.emit_event. Shape example:
    event = GlobalStartEvent(
        action_class=type(action),
        action_name=action.get_full_class_name(),
        nest_level=current_nest,
        context=context,
        params=params,
    )
    await plugin_ctx.emit_event(event)

    # Regular/summary pipeline: ActionProductMachine calls PluginEmitSupport
    # (emit_before_regular_aspect / emit_after_regular_aspect / …), which builds
    # the same event objects and passes them to plugin_ctx.emit_event. Shape example:
    event = AfterRegularAspectEvent(
        action_class=type(action),
        action_name=action.get_full_class_name(),
        nest_level=box.nested_level,
        context=context,
        params=params,
        aspect_name=aspect_meta.method_name,
        state_snapshot=state.to_dict(),
        aspect_result=new_state_dict,
        duration_ms=aspect_duration * 1000,
    )
    await plugin_ctx.emit_event(event)

    # В ActionProductMachine._rollback_saga():
    event = SagaRollbackStartedEvent(
        action_class=type(action),
        action_name=action.get_full_class_name(),
        nest_level=box.nested_level,
        context=context,
        params=params,
        error=error,
        stack_depth=len(saga_stack),
        compensator_count=sum(1 for f in saga_stack if f.compensator),
        aspect_names=tuple(f.aspect_name for f in reversed(saga_stack)),
    )
    await plugin_ctx.emit_event(event)

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ В ПЛАГИНЕ
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.intents.logging.channel import Channel
    from action_machine.intents.plugins.events import (
        GlobalFinishEvent,
        AfterRegularAspectEvent,
        AspectEvent,
        CompensateFailedEvent,
        SagaRollbackCompletedEvent,
    )

    class MetricsPlugin(Plugin):

        async def get_initial_state(self) -> dict:
            return {"slow_count": 0, "saga_failures": 0}

        @on(GlobalFinishEvent)
        async def on_track_slow(self, state, event: GlobalFinishEvent, log):
            if event.duration_ms > 1000:
                state["slow_count"] += 1
            return state

        @on(AspectEvent)
        async def on_any_aspect(self, state, event: AspectEvent, log):
            await log.info(
                Channel.debug,
                "Аспект: {%var.name}",
                name=event.aspect_name,
            )
            return state

        @on(CompensateFailedEvent)
        async def on_compensate_failed(self, state, event: CompensateFailedEvent, log):
            await log.critical(
                Channel.error,
                "Сбой компенсатора {%var.comp} для аспекта {%var.aspect}: {%var.err}",
                comp=event.compensator_name,
                aspect=event.failed_for_aspect,
                err=str(event.compensator_error),
            )
            state["saga_failures"] += 1
            return state

        @on(SagaRollbackCompletedEvent)
        async def on_saga_complete(self, state, event: SagaRollbackCompletedEvent, log):
            await log.warning(
                Channel.business,
                "Размотка завершена: {%var.ok} успешно, {%var.fail} сбоев за {%var.ms}ms",
                ok=event.succeeded,
                fail=event.failed,
                ms=event.duration_ms,
            )
            return state
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from action_machine.intents.context.context import Context
from action_machine.model.base_schema import BaseSchema

# ═════════════════════════════════════════════════════════════════════════════
# Корневой класс
# ═════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class BasePluginEvent:
    """
    Корневой класс всех событий плагинной системы.

    Содержит поля, общие для КАЖДОГО события в системе. Любое событие,
    доставляемое обработчику плагина, является экземпляром BasePluginEvent.

    Подписка на BasePluginEvent через ``@on(BasePluginEvent)`` означает
    получение ВСЕХ событий системы без исключения.

    Атрибуты:
        action_class: тип действия (класс, наследующий BaseAction).
            Используется для типобезопасной фильтрации через isinstance
            в параметре action_class декоратора @on.
            Пример: CreateOrderAction, PingAction.

        action_name: полное строковое имя действия (module.ClassName).
            Используется для regex-фильтрации через action_name_pattern
            в декораторе @on и для шаблонов логирования
            ({%event.action_name} в ScopedLogger).
            Пример: "orders.actions.CreateOrderAction".

        nest_level: уровень вложенности вызова действия.
            0 — корневое действие (вызвано через machine.run()).
            1 — дочернее действие (вызвано через box.run() внутри аспекта).
            2 — действие, вложенное в дочернее, и т.д.
            Используется для фильтрации через nest_level в декораторе @on.

        context: контекст выполнения (информация о пользователе, запросе,
            среде выполнения). Frozen BaseSchema-наследник.

        params: входные параметры действия. Frozen BaseParams-наследник.
            Содержит данные, переданные при вызове machine.run().
    """

    action_class: type
    action_name: str
    nest_level: int
    context: Context
    params: BaseSchema


# ═════════════════════════════════════════════════════════════════════════════
# Группа: Global Lifecycle (старт и финиш конвейера)
# ═════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class GlobalLifecycleEvent(BasePluginEvent):
    """
    Групповой класс событий жизненного цикла действия.

    Объединяет GlobalStartEvent и GlobalFinishEvent. Подписка на
    ``@on(GlobalLifecycleEvent)`` доставляет оба события.

    Never instantiated directly; the production path emits concrete
    ``GlobalStartEvent`` / ``GlobalFinishEvent`` through ``PluginEmitSupport``.
    This class exists only for ``isinstance``-based subscriptions.
    """


@dataclass(frozen=True)
class GlobalStartEvent(GlobalLifecycleEvent):
    """
    Fired when a run is about to enter the aspect pipeline.

    Emitted via ``PluginEmitSupport.emit_global_start`` after role and connection
    gates and ``ToolsBox`` creation, before ``_execute_aspects_with_error_handling``.
    No ``result`` or ``duration_ms`` yet.
    """


@dataclass(frozen=True)
class GlobalFinishEvent(GlobalLifecycleEvent):
    """
    Fired when a run completes with a final result (summary or ``@on_error``).

    Emitted via ``PluginEmitSupport.emit_global_finish`` after
    ``_execute_aspects_with_error_handling`` returns.

    Attributes:
        result: Final frozen ``BaseResult`` (from summary or a matching error handler).
        duration_ms: Wall time for the whole ``_run_internal`` call, in milliseconds
            (from start of ``_run_internal`` until just before this event).
    """

    result: BaseSchema
    duration_ms: float


# ═════════════════════════════════════════════════════════════════════════════
# Группа: Aspect Events (события аспектов)
# ═════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class AspectEvent(BasePluginEvent):
    """
    Групповой класс всех аспектных событий.

    Объединяет все события, связанные с выполнением аспектов: regular,
    summary, on_error, compensate. Подписка на ``@on(AspectEvent)``
    доставляет все before/after события всех типов аспектов.

    Не создаётся машиной напрямую — машина создаёт конкретные
    BeforeRegularAspectEvent, AfterSummaryAspectEvent и т.д.

    Добавляет поля, специфичные для аспектных событий.

    Атрибуты:
        aspect_name: имя метода-аспекта (например, "validate_amount",
            "process_payment", "build_result_summary").
            Используется для фильтрации через aspect_name_pattern
            в декораторе @on.

        state_snapshot: снимок состояния конвейера на момент события
            как dict[str, object]. Создаётся через state.to_dict()
            в машине. None для событий, где состояние недоступно.
            Это обычный dict, а не BaseState — плагин не получает
            мутабельный объект конвейера.
    """

    aspect_name: str
    state_snapshot: dict[str, object] | None


# ─────────────────────────────────────────────────────────────────────────────
# Regular Aspect Events
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class RegularAspectEvent(AspectEvent):
    """
    Групповой класс событий regular-аспектов.

    Объединяет BeforeRegularAspectEvent и AfterRegularAspectEvent.
    Подписка на ``@on(RegularAspectEvent)`` доставляет оба.
    """


@dataclass(frozen=True)
class BeforeRegularAspectEvent(RegularAspectEvent):
    """
    Fired immediately before a regular aspect method runs.

    Emitted via ``PluginEmitSupport.emit_before_regular_aspect`` (which delegates to
    ``PluginRunContext.emit_event``). No ``aspect_result`` or ``duration_ms`` yet.
    """


@dataclass(frozen=True)
class AfterRegularAspectEvent(RegularAspectEvent):
    """
    Fired after a regular aspect completes and checkers have validated its output.

    Emitted via ``PluginEmitSupport.emit_after_regular_aspect``.

    Attributes:
        aspect_result: Dict merged into state after checker validation (e.g.
            ``{"txn_id": "TXN-001", "charged_amount": 500.0}``).
        duration_ms: Wall time for the aspect call plus checker work, in milliseconds.
    """

    aspect_result: dict[str, Any]
    duration_ms: float


# ─────────────────────────────────────────────────────────────────────────────
# Summary Aspect Events
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SummaryAspectEvent(AspectEvent):
    """
    Групповой класс событий summary-аспектов.

    Объединяет BeforeSummaryAspectEvent и AfterSummaryAspectEvent.
    Подписка на ``@on(SummaryAspectEvent)`` доставляет оба.
    """


@dataclass(frozen=True)
class BeforeSummaryAspectEvent(SummaryAspectEvent):
    """
    Fired immediately before the summary aspect runs.

    Emitted via ``PluginEmitSupport.emit_before_summary_aspect``. No ``result`` or
    ``duration_ms`` yet.
    """


@dataclass(frozen=True)
class AfterSummaryAspectEvent(SummaryAspectEvent):
    """
    Fired after the summary aspect returns the action's final result.

    Emitted via ``PluginEmitSupport.emit_after_summary_aspect``.

    Attributes:
        result: Frozen ``BaseResult`` subclass produced by the summary aspect.
        duration_ms: Summary aspect duration in milliseconds.
    """

    result: BaseSchema
    duration_ms: float


# ─────────────────────────────────────────────────────────────────────────────
# OnError Aspect Events
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class OnErrorAspectEvent(AspectEvent):
    """
    Групповой класс событий обработчиков ошибок (@on_error).

    Объединяет BeforeOnErrorAspectEvent и AfterOnErrorAspectEvent.
    Подписка на ``@on(OnErrorAspectEvent)`` доставляет оба.

    Эти события эмитируются только когда машина нашла подходящий
    @on_error обработчик для исключения аспекта. Если обработчик
    не найден — эмитируется UnhandledErrorEvent.
    """


@dataclass(frozen=True)
class BeforeOnErrorAspectEvent(OnErrorAspectEvent):
    """
    Событие перед вызовом обработчика @on_error.

    Эмитируется машиной после обнаружения подходящего @on_error
    обработчика, но перед его вызовом.

    Создаётся в ActionProductMachine._handle_aspect_error() перед
    вызовом handler_meta.method_ref().

    Атрибуты:
        error: исключение, возникшее в аспекте и перехваченное машиной.
            Экземпляр Exception. Плагин может прочитать тип и сообщение,
            но не может подавить или заменить ошибку.

        handler_name: имя метода @on_error обработчика, который будет
            вызван. Например: "validation_on_error".
    """

    error: Exception
    handler_name: str


@dataclass(frozen=True)
class AfterOnErrorAspectEvent(OnErrorAspectEvent):
    """
    Событие после вызова обработчика @on_error.

    Эмитируется машиной после успешного выполнения обработчика,
    который вернул альтернативный Result.

    Создаётся в ActionProductMachine._handle_aspect_error() после
    успешного возврата из handler_meta.method_ref().

    Атрибуты:
        error: исходное исключение аспекта.

        handler_name: имя метода @on_error обработчика.

        handler_result: альтернативный результат (frozen BaseResult),
            возвращённый обработчиком. Этот результат подменяет
            итоговый Result действия.

        duration_ms: длительность выполнения обработчика в миллисекундах.
    """

    error: Exception
    handler_name: str
    handler_result: BaseSchema
    duration_ms: float


# ─────────────────────────────────────────────────────────────────────────────
# Compensate Aspect Events (события отдельных компенсаторов)
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CompensateAspectEvent(AspectEvent):
    """
    Групповой класс событий компенсирующих аспектов (Saga).

    Объединяет BeforeCompensateAspectEvent, AfterCompensateAspectEvent
    и CompensateFailedEvent. Подписка на ``@on(CompensateAspectEvent)``
    доставляет все три типа — перед каждым компенсатором, после
    успешного и при сбое.

    События эмитируются из _rollback_saga() при размотке стека
    компенсации в обратном порядке. Каждый фрейм стека (SagaFrame)
    с непустым compensator порождает Before + (After или Failed).
    """


@dataclass(frozen=True)
class BeforeCompensateAspectEvent(CompensateAspectEvent):
    """
    Событие перед выполнением компенсатора.

    Эмитируется из _rollback_saga() непосредственно перед вызовом
    метода-компенсатора для каждого фрейма стека с непустым compensator.

    Содержит полную информацию для диагностики: какой компенсатор
    будет вызван, какое исключение вызвало размотку, какие состояния
    (до и после аспекта) доступны компенсатору.

    Атрибуты:
        error: исключение, вызвавшее размотку стека. Экземпляр Exception.
            Это ОРИГИНАЛЬНАЯ ошибка аспекта, а не ошибка компенсатора.

        compensator_name: имя метода-компенсатора, который будет вызван.
            Например: "rollback_payment_compensate".

        compensator_state_before: состояние конвейера ДО выполнения
            целевого аспекта. Frozen BaseState-наследник как объект.
            Компенсатор использует его для восстановления.

        compensator_state_after: состояние конвейера ПОСЛЕ выполнения
            целевого аспекта. Frozen BaseState-наследник или None.
            None означает: чекер отклонил результат, но побочный
            эффект мог произойти.
    """

    error: Exception
    compensator_name: str
    compensator_state_before: object  # BaseState
    compensator_state_after: object | None  # BaseState | None


@dataclass(frozen=True)
class AfterCompensateAspectEvent(CompensateAspectEvent):
    """
    Событие после успешного выполнения компенсатора.

    Эмитируется из _rollback_saga() после того, как метод-компенсатор
    завершился без исключения. Содержит длительность выполнения.

    Атрибуты:
        error: исключение, вызвавшее размотку стека. ОРИГИНАЛЬНАЯ
            ошибка аспекта.

        compensator_name: имя метода-компенсатора, который выполнился.

        duration_ms: длительность выполнения компенсатора в миллисекундах.
    """

    error: Exception
    compensator_name: str
    duration_ms: float


@dataclass(frozen=True)
class CompensateFailedEvent(CompensateAspectEvent):
    """
    Событие сбоя компенсатора.

    Эмитируется из _rollback_saga() когда метод-компенсатор бросил
    исключение. Размотка стека ПРОДОЛЖАЕТСЯ после эмиссии этого
    события — ошибки компенсаторов молчаливые.

    Это ЕДИНСТВЕННЫЙ способ узнать о сбое компенсатора. Фреймворк
    полностью подавляет ошибки компенсаторов внутри _rollback_saga().
    Плагин мониторинга, подписанный на CompensateFailedEvent, может
    записать информацию для аудита, отправить алерт, увеличить метрику.

    CompensateFailedEvent — отдельный тип (а не флаг в
    AfterCompensateAspectEvent), потому что сбой компенсатора —
    аварийная ситуация, требующая отдельной реакции. Отдельный тип
    позволяет подписаться точечно: @on(CompensateFailedEvent).

    Атрибуты:
        original_error: исключение, вызвавшее размотку стека.
            ОРИГИНАЛЬНАЯ ошибка аспекта. Плагин может различить:
            "размотка началась из-за PaymentDeclinedError, а
            компенсатор упал из-за ConnectionRefusedError".

        compensator_error: исключение, возникшее в компенсаторе.
            Экземпляр Exception. Содержит причину сбоя отката.

        compensator_name: имя метода-компенсатора, который упал.

        failed_for_aspect: имя regular-аспекта, для которого
            предназначался упавший компенсатор. Позволяет определить,
            какой побочный эффект НЕ был откачен.
    """

    original_error: Exception
    compensator_error: Exception
    compensator_name: str
    failed_for_aspect: str


# ═════════════════════════════════════════════════════════════════════════════
# Группа: Saga Events (события размотки стека)
# ═════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class SagaEvent(BasePluginEvent):
    """
    Групповой класс событий уровня всей размотки стека (Saga).

    Объединяет SagaRollbackStartedEvent и SagaRollbackCompletedEvent.
    Подписка на ``@on(SagaEvent)`` доставляет оба события.

    Эти события дают общую картину размотки: сколько фреймов в стеке,
    сколько компенсаторов выполнено успешно, сколько упало, общая
    длительность. Без них плагин вынужден самостоятельно агрегировать
    CompensateAspectEvent-события и отслеживать границы размотки.

    Не создаётся машиной напрямую — машина создаёт конкретные
    SagaRollbackStartedEvent или SagaRollbackCompletedEvent.
    """


@dataclass(frozen=True)
class SagaRollbackStartedEvent(SagaEvent):
    """
    Событие начала размотки стека компенсации.

    Эмитируется ОДИН РАЗ из _rollback_saga() перед началом обхода
    фреймов стека в обратном порядке. Позволяет плагину мониторинга
    зафиксировать момент начала отката, количество фреймов и
    исключение-причину.

    Создаётся в ActionProductMachine._rollback_saga() перед циклом
    по saga_stack.

    Атрибуты:
        error: исключение, вызвавшее размотку стека. Экземпляр Exception.

        stack_depth: общее количество фреймов в стеке (включая фреймы
            без компенсатора). Показывает, сколько аспектов успешно
            выполнилось до ошибки.

        compensator_count: количество фреймов, имеющих компенсатор
            (compensator is not None). Показывает, сколько компенсаторов
            БУДУТ вызваны (если не упадут).

        aspect_names: имена аспектов в стеке в порядке размотки
            (обратном порядке выполнения). Кортеж строк. Например:
            ("process_payment_aspect", "reserve_inventory_aspect",
             "validate_amount_aspect").
    """

    error: Exception
    stack_depth: int
    compensator_count: int
    aspect_names: tuple[str, ...]


@dataclass(frozen=True)
class SagaRollbackCompletedEvent(SagaEvent):
    """
    Событие завершения размотки стека компенсации.

    Эмитируется ОДИН РАЗ из _rollback_saga() после обхода всех
    фреймов стека. Содержит итоги размотки: сколько компенсаторов
    выполнено успешно, сколько упало, сколько пропущено (без
    компенсатора), общая длительность.

    Позволяет плагину мониторинга:
    - Замерить общую длительность размотки.
    - Оценить успешность отката (succeeded vs failed).
    - Выявить аспекты без компенсаторов (skipped).
    - Получить список аспектов, чьи компенсаторы упали (failed_aspects).

    Создаётся в ActionProductMachine._rollback_saga() после цикла
    по saga_stack.

    Атрибуты:
        error: исключение, вызвавшее размотку стека.

        total_frames: общее количество фреймов в стеке.

        succeeded: количество компенсаторов, выполненных успешно.

        failed: количество компенсаторов, завершившихся ошибкой.

        skipped: количество фреймов без компенсатора (пропущены
            при размотке).

        duration_ms: общая длительность размотки стека в миллисекундах.
            Включает время всех компенсаторов (успешных и упавших).

        failed_aspects: имена regular-аспектов, чьи компенсаторы упали.
            Кортеж строк. Пустой кортеж если все компенсаторы успешны.
            Позволяет определить, какие побочные эффекты НЕ были откачены.
    """

    error: Exception
    total_frames: int
    succeeded: int
    failed: int
    skipped: int
    duration_ms: float
    failed_aspects: tuple[str, ...]


# ═════════════════════════════════════════════════════════════════════════════
# Группа: Error Events (ошибки конвейера)
# ═════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class ErrorEvent(BasePluginEvent):
    """
    Групповой класс событий ошибок конвейера.

    Объединяет все события, связанные с ошибками, которые не были
    обработаны на уровне Action. Подписка на ``@on(ErrorEvent)``
    доставляет все типы ошибок.

    Отличие от OnErrorAspectEvent: OnErrorAspectEvent эмитируется
    когда @on_error обработчик НАЙДЕН и будет вызван. ErrorEvent
    эмитируется когда обработчик НЕ найден или сам упал.
    """


@dataclass(frozen=True)
class UnhandledErrorEvent(ErrorEvent):
    """
    Событие необработанной ошибки конвейера.

    Эмитируется машиной когда аспект бросил исключение, и ни один
    @on_error обработчик не подходит по типу (или обработчики
    вообще не объявлены). После эмиссии этого события исходное
    исключение пробрасывается наружу из machine.run().

    Если в Action есть компенсаторы, размотка стека (_rollback_saga)
    выполняется ДО эмиссии UnhandledErrorEvent. К моменту эмиссии
    все компенсаторы уже отработали (или упали).

    Плагин-наблюдатель не может подавить ошибку — он только
    наблюдает и может записать информацию для аудита.

    Создаётся в ActionProductMachine._execute_aspects_with_error_handling()
    перед повторным пробросом исходного исключения.

    Атрибуты:
        error: исключение, возникшее в аспекте. Экземпляр Exception.

        failed_aspect_name: имя аспекта, в котором произошла ошибка.
            Может быть None, если ошибка произошла вне аспекта
            (например, при проверке ролей — но такие ошибки обычно
            не доходят до плагинов).

        state_snapshot: снимок состояния конвейера на момент ошибки.
            Наследуется от AspectEvent через ErrorEvent. Содержит
            данные, накопленные успешно завершёнными аспектами.
    """

    error: Exception
    failed_aspect_name: str | None = None
