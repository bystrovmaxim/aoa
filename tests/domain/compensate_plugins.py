# tests/domain/compensate_plugins.py
"""
Плагины-наблюдатели для событий компенсации (Saga) в тестах.
═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════
Содержит плагины, подписанные на типизированные события Saga из иерархии
BasePluginEvent. Плагины-наблюдатели записывают информацию о каждом
событии в своё per-request состояние (state) И дублируют в атрибут
экземпляра collected_events — для прямого доступа из тестов.

Дублирование необходимо, потому что TestBench не экспонирует
PluginRunContext.get_plugin_state() наружу. Per-request state доступен
только внутри машины на время одного run(). Атрибут collected_events
доступен тестам напрямую через saga_observer.collected_events.

Плагины-наблюдатели НЕ МОГУТ изменить результат или подавить ошибку —
они только фиксируют факты для последующей проверки в assert.
═══════════════════════════════════════════════════════════════════════════════
ТИПИЗИРОВАННЫЕ СОБЫТИЯ КОМПЕНСАЦИИ
═══════════════════════════════════════════════════════════════════════════════
Машина (ActionProductMachine) эмитирует пять типов событий компенсации
в методе _rollback_saga():

Уровень ВСЕЙ РАЗМОТКИ (saga-level):
    SagaRollbackStartedEvent — начало размотки стека. Содержит:
        error, stack_depth, compensator_count, aspect_names.
    SagaRollbackCompletedEvent — конец размотки. Содержит:
        error, total_frames, succeeded, failed, skipped,
        duration_ms, failed_aspects.

Уровень ОДНОГО КОМПЕНСАТОРА (compensator-level):
    BeforeCompensateAspectEvent — перед вызовом компенсатора. Содержит:
        error, compensator_name, compensator_state_before,
        compensator_state_after.
    AfterCompensateAspectEvent — после успешного компенсатора. Содержит:
        error, compensator_name, duration_ms.
    CompensateFailedEvent — сбой компенсатора. Содержит:
        original_error, compensator_error, compensator_name,
        failed_for_aspect.
═══════════════════════════════════════════════════════════════════════════════
ПЛАГИНЫ
═══════════════════════════════════════════════════════════════════════════════
SagaObserverPlugin — записывает ВСЕ пять типов событий компенсации
    в state["events"] (per-request) и в self.collected_events (persistent).
    Каждое событие сохраняется как dict с полями event_type, action_name
    и специфичными данными события. Позволяет тестам проверять полную
    последовательность событий, их данные и порядок.
═══════════════════════════════════════════════════════════════════════════════
ИСПОЛЬЗОВАНИЕ В ТЕСТАХ
═══════════════════════════════════════════════════════════════════════════════
    from tests.domain.compensate_plugins import SagaObserverPlugin

    observer = SagaObserverPlugin()
    bench = TestBench(
        plugins=[observer],
        log_coordinator=AsyncMock(),
    )

    # После выполнения действия с ошибкой:
    await bench.run(action, params, rollup=False)

    # Проверка событий через атрибут экземпляра:
    events = observer.collected_events
    assert events[0]["event_type"] == "SagaRollbackStartedEvent"
    assert events[-1]["event_type"] == "SagaRollbackCompletedEvent"

═══════════════════════════════════════════════════════════════════════════════
УДВОЕНИЕ СОБЫТИЙ
═══════════════════════════════════════════════════════════════════════════════
TestBench.run() прогоняет ДВУМЯ машинами (async и sync) с
_reset_all_mocks() между ними. Плагины НЕ сбрасываются между
прогонами — collected_events содержит события от ОБОИХ прогонов.
Тесты должны учитывать удвоение или вызывать observer.reset()
перед run().
"""
from action_machine.logging.scoped_logger import ScopedLogger
from action_machine.plugins.decorators import on
from action_machine.plugins.events import (
    AfterCompensateAspectEvent,
    BeforeCompensateAspectEvent,
    CompensateFailedEvent,
    SagaRollbackCompletedEvent,
    SagaRollbackStartedEvent,
)
from action_machine.plugins.plugin import Plugin


class SagaObserverPlugin(Plugin):
    """
    Плагин-наблюдатель, записывающий все события компенсации.

    Помимо per-request state (для PluginRunContext), дублирует события
    в атрибут экземпляра self.collected_events — список dict, доступный
    тестам напрямую через saga_observer.collected_events после bench.run().

    Это обходит ограничение TestBench, который не экспонирует
    PluginRunContext.get_plugin_state() наружу.

    Per-request состояние: {"events": []}. Каждое событие добавляется
    как словарь с полем event_type (имя класса события) и специфичными
    данными, извлечёнными из объекта события.

    Подписан на пять типов событий:
    1. SagaRollbackStartedEvent — начало размотки стека.
       Записывает: stack_depth, compensator_count, aspect_names.
    2. BeforeCompensateAspectEvent — перед каждым компенсатором.
       Записывает: compensator_name, aspect_name.
    3. AfterCompensateAspectEvent — после успешного компенсатора.
       Записывает: compensator_name, aspect_name, duration_ms.
    4. CompensateFailedEvent — сбой компенсатора.
       Записывает: compensator_name, failed_for_aspect,
       original_error_type, compensator_error_type.
    5. SagaRollbackCompletedEvent — конец размотки.
       Записывает: total_frames, succeeded, failed, skipped,
       duration_ms, failed_aspects.

    Порядок записи событий соответствует порядку эмиссии машиной:
    Started → (Before → After|Failed)* → Completed.
    Тесты проверяют этот порядок через индексы списка.
    """

    def __init__(self) -> None:
        super().__init__()
        self.collected_events: list[dict] = []

    def reset(self) -> None:
        """
        Сбрасывает собранные события.

        Вызывается в фикстуре перед каждым тестом для изоляции.
        TestBench.run() прогоняет две машины — без reset() события
        накапливаются между тестами.
        """
        self.collected_events = []

    async def get_initial_state(self) -> dict:
        """Начальное состояние — пустой список событий."""
        return {"events": []}

    @on(SagaRollbackStartedEvent)
    async def on_saga_started(
        self,
        state: dict,
        event: SagaRollbackStartedEvent,
        log: ScopedLogger | None,
    ) -> dict:
        """
        Записывает начало размотки стека компенсации.

        SagaRollbackStartedEvent эмитируется ОДИН РАЗ перед началом
        обхода стека в обратном порядке. Содержит общую информацию
        о стеке: глубину, количество компенсаторов, имена аспектов.
        """
        entry = {
            "event_type": "SagaRollbackStartedEvent",
            "action_name": event.action_name,
            "error_type": type(event.error).__name__,
            "error_message": str(event.error),
            "stack_depth": event.stack_depth,
            "compensator_count": event.compensator_count,
            "aspect_names": list(event.aspect_names),
        }
        state["events"].append(entry)
        self.collected_events.append(entry)
        return state

    @on(BeforeCompensateAspectEvent)
    async def on_before_compensate(
        self,
        state: dict,
        event: BeforeCompensateAspectEvent,
        log: ScopedLogger | None,
    ) -> dict:
        """
        Записывает момент перед вызовом одного компенсатора.

        BeforeCompensateAspectEvent эмитируется для каждого фрейма
        в стеке, имеющего компенсатор (фреймы без компенсатора
        пропускаются). Позволяет проверить обратный порядок вызовов.
        """
        entry = {
            "event_type": "BeforeCompensateAspectEvent",
            "action_name": event.action_name,
            "aspect_name": event.aspect_name,
            "compensator_name": event.compensator_name,
        }
        state["events"].append(entry)
        self.collected_events.append(entry)
        return state

    @on(AfterCompensateAspectEvent)
    async def on_after_compensate(
        self,
        state: dict,
        event: AfterCompensateAspectEvent,
        log: ScopedLogger | None,
    ) -> dict:
        """
        Записывает успешное завершение одного компенсатора.

        AfterCompensateAspectEvent эмитируется только если компенсатор
        выполнился без исключения. Содержит duration_ms — время
        выполнения компенсатора в миллисекундах.
        """
        entry = {
            "event_type": "AfterCompensateAspectEvent",
            "action_name": event.action_name,
            "aspect_name": event.aspect_name,
            "compensator_name": event.compensator_name,
            "duration_ms": event.duration_ms,
        }
        state["events"].append(entry)
        self.collected_events.append(entry)
        return state

    @on(CompensateFailedEvent)
    async def on_compensate_failed(
        self,
        state: dict,
        event: CompensateFailedEvent,
        log: ScopedLogger | None,
    ) -> dict:
        """
        Записывает сбой одного компенсатора.

        CompensateFailedEvent эмитируется когда компенсатор бросает
        исключение. Содержит две ошибки: original_error (ошибка
        аспекта, вызвавшая размотку) и compensator_error (ошибка
        самого компенсатора). Размотка ПРОДОЛЖАЕТСЯ после сбоя —
        следующие компенсаторы в стеке получат шанс выполниться.
        """
        entry = {
            "event_type": "CompensateFailedEvent",
            "action_name": event.action_name,
            "aspect_name": event.aspect_name,
            "compensator_name": event.compensator_name,
            "failed_for_aspect": event.failed_for_aspect,
            "original_error_type": type(event.original_error).__name__,
            "compensator_error_type": type(event.compensator_error).__name__,
            "compensator_error_message": str(event.compensator_error),
        }
        state["events"].append(entry)
        self.collected_events.append(entry)
        return state

    @on(SagaRollbackCompletedEvent)
    async def on_saga_completed(
        self,
        state: dict,
        event: SagaRollbackCompletedEvent,
        log: ScopedLogger | None,
    ) -> dict:
        """
        Записывает завершение размотки стека компенсации.

        SagaRollbackCompletedEvent эмитируется ОДИН РАЗ после обхода
        всех фреймов стека. Содержит итоги: сколько компенсаторов
        выполнено успешно (succeeded), сколько упало (failed),
        сколько пропущено из-за отсутствия компенсатора (skipped),
        общую длительность (duration_ms) и имена аспектов, чьи
        компенсаторы упали (failed_aspects).
        """
        entry = {
            "event_type": "SagaRollbackCompletedEvent",
            "action_name": event.action_name,
            "error_type": type(event.error).__name__,
            "total_frames": event.total_frames,
            "succeeded": event.succeeded,
            "failed": event.failed,
            "skipped": event.skipped,
            "duration_ms": event.duration_ms,
            "failed_aspects": list(event.failed_aspects),
        }
        state["events"].append(entry)
        self.collected_events.append(entry)
        return state
