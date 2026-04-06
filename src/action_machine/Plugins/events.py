# src/action_machine/plugins/events.py
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
    │   └── CompensateAspectEvent                — группа: compensate (зарезервировано)
    │       ├── BeforeCompensateAspectEvent      — перед compensate
    │       └── AfterCompensateAspectEvent       — после compensate (+ duration_ms)
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
    @on(ErrorEvent)                   — все ошибки конвейера

Групповые классы (GlobalLifecycleEvent, AspectEvent, RegularAspectEvent)
не создаются машиной напрямую — машина всегда создаёт конкретные
leaf-классы (GlobalStartEvent, BeforeRegularAspectEvent и т.д.).
Групповые классы существуют только для подписки через isinstance.

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

    # В ActionProductMachine._run_internal():
    event = GlobalStartEvent(
        action_class=type(action),
        action_name=action.get_full_class_name(),
        nest_level=current_nest,
        context=context,
        params=params,
    )
    await plugin_ctx.emit_event(event)

    # В ActionProductMachine._execute_regular_aspects():
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

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ В ПЛАГИНЕ
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.plugins.events import (
        GlobalFinishEvent,
        AfterRegularAspectEvent,
        AspectEvent,
    )

    class MetricsPlugin(Plugin):
        async def get_initial_state(self) -> dict:
            return {"slow_count": 0}

        @on(GlobalFinishEvent)
        async def on_track_slow(self, state, event: GlobalFinishEvent, log):
            if event.duration_ms > 1000:
                state["slow_count"] += 1
            return state

        @on(AspectEvent)
        async def on_any_aspect(self, state, event: AspectEvent, log):
            await log.info("Аспект: {%var.name}", name=event.aspect_name)
            return state
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from action_machine.context.context import Context
from action_machine.core.base_schema import BaseSchema

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

    Не создаётся машиной напрямую — машина всегда создаёт конкретные
    GlobalStartEvent или GlobalFinishEvent. Этот класс существует
    только для группового подписывания через isinstance.
    """


@dataclass(frozen=True)
class GlobalStartEvent(GlobalLifecycleEvent):
    """
    Событие начала выполнения действия.

    Эмитируется машиной (ActionProductMachine) сразу после проверки
    ролей, валидации соединений и получения фабрики зависимостей,
    но ДО выполнения первого аспекта.

    Не содержит result и duration_ms — результат ещё не известен,
    время ещё не замерено.

    Создаётся в ActionProductMachine._run_internal() перед вызовом
    _execute_aspects_with_error_handling().
    """


@dataclass(frozen=True)
class GlobalFinishEvent(GlobalLifecycleEvent):
    """
    Событие завершения выполнения действия.

    Эмитируется машиной после успешного завершения конвейера аспектов
    (включая summary) или после успешной обработки ошибки через @on_error.

    Содержит итоговый результат и общую длительность выполнения.

    Создаётся в ActionProductMachine._run_internal() после возврата
    результата из _execute_aspects_with_error_handling().

    Атрибуты:
        result: итоговый результат действия (frozen BaseResult-наследник).
            Всегда не None — к моменту global_finish результат сформирован
            (либо summary-аспектом, либо @on_error обработчиком).

        duration_ms: общая длительность выполнения действия в миллисекундах.
            Включает время всех аспектов, проверку ролей, валидацию
            соединений, работу плагинов. Замер начинается в начале
            _run_internal() и заканчивается перед эмиссией этого события.
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
    Событие перед выполнением regular-аспекта.

    Эмитируется машиной непосредственно перед вызовом метода-аспекта.
    Не содержит результата аспекта (ещё не выполнен) и длительности.

    Создаётся в ActionProductMachine._execute_regular_aspects() перед
    вызовом _call_aspect() для каждого regular-аспекта.
    """


@dataclass(frozen=True)
class AfterRegularAspectEvent(RegularAspectEvent):
    """
    Событие после выполнения regular-аспекта.

    Эмитируется машиной после успешного выполнения метода-аспекта
    и прохождения валидации чекерами.

    Создаётся в ActionProductMachine._execute_regular_aspects() после
    _apply_checkers() и обновления state.

    Атрибуты:
        aspect_result: словарь с данными, возвращёнными аспектом.
            Это dict, который аспект вернул из своего метода. Уже
            провалидирован чекерами и добавлен в state.
            Пример: {"txn_id": "TXN-001", "charged_amount": 500.0}.

        duration_ms: длительность выполнения аспекта в миллисекундах.
            Включает время вызова метода и проверки чекерами.
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
    Событие перед выполнением summary-аспекта.

    Эмитируется машиной непосредственно перед вызовом summary-метода.
    Не содержит результата (ещё не сформирован) и длительности.

    Создаётся в ActionProductMachine._execute_aspects_with_error_handling()
    перед вызовом _call_aspect(summary_meta, ...).
    """


@dataclass(frozen=True)
class AfterSummaryAspectEvent(SummaryAspectEvent):
    """
    Событие после выполнения summary-аспекта.

    Эмитируется машиной после успешного выполнения summary-метода,
    сформировавшего итоговый Result действия.

    Создаётся в ActionProductMachine._execute_aspects_with_error_handling()
    после вызова _call_aspect(summary_meta, ...).

    Атрибуты:
        result: итоговый результат действия (frozen BaseResult-наследник),
            сформированный summary-аспектом.

        duration_ms: длительность выполнения summary-аспекта в миллисекундах.
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
# Compensate Aspect Events (зарезервировано для будущих версий)
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CompensateAspectEvent(AspectEvent):
    """
    Групповой класс событий компенсирующих аспектов.

    Зарезервирован для будущих версий ActionMachine, где может появиться
    механизм компенсации (Saga pattern). Объединяет
    BeforeCompensateAspectEvent и AfterCompensateAspectEvent.
    """


@dataclass(frozen=True)
class BeforeCompensateAspectEvent(CompensateAspectEvent):
    """
    Событие перед выполнением компенсирующего аспекта.

    Зарезервировано для будущих версий. Не создаётся текущей машиной.
    """


@dataclass(frozen=True)
class AfterCompensateAspectEvent(CompensateAspectEvent):
    """
    Событие после выполнения компенсирующего аспекта.

    Зарезервировано для будущих версий. Не создаётся текущей машиной.

    Атрибуты:
        duration_ms: длительность выполнения компенсирующего аспекта
            в миллисекундах.
    """

    duration_ms: float


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
