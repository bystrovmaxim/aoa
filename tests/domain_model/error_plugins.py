# tests/domain/error_plugins.py
"""
Тестовые плагины для наблюдения за ошибками аспектов.
═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════
Содержит плагины, подписанные на типизированные события ошибок из
иерархии BasePluginEvent для тестирования механизма наблюдения за
ошибками аспектов. Плагины-наблюдатели не могут изменить результат
или подавить ошибку — они только записывают информацию в своё
per-request состояние.

Типизированные события ошибок:
    UnhandledErrorEvent       — ошибка без подходящего @on_error обработчика
    BeforeOnErrorAspectEvent  — перед вызовом найденного @on_error обработчика
    AfterOnErrorAspectEvent   — после успешного @on_error обработчика

Машина (ActionProductMachine) эмитирует эти события в _handle_aspect_error():
- Если @on_error обработчик найден → BeforeOnErrorAspectEvent, затем
  AfterOnErrorAspectEvent после успешного вызова.
- Если @on_error обработчик не найден → UnhandledErrorEvent, затем
  исходное исключение пробрасывается наружу.

═══════════════════════════════════════════════════════════════════════════════
ПЛАГИНЫ
═══════════════════════════════════════════════════════════════════════════════
- ErrorObserverPlugin — записывает все ошибки в state["errors"].
  Подписан на UnhandledErrorEvent и BeforeOnErrorAspectEvent.
  Записывает action_name, тип ошибки, сообщение и тип события.

- ErrorCounterPlugin — считает количество ошибок в state["count"].
  Подписан на UnhandledErrorEvent и BeforeOnErrorAspectEvent.
  Разделяет на handled (BeforeOnErrorAspectEvent — обработчик найден)
  и unhandled (UnhandledErrorEvent — обработчик не найден).

═══════════════════════════════════════════════════════════════════════════════
ИСПОЛЬЗОВАНИЕ В ТЕСТАХ
═══════════════════════════════════════════════════════════════════════════════
    from tests.domain.error_plugins import ErrorObserverPlugin, ErrorCounterPlugin

    observer = ErrorObserverPlugin()
    counter = ErrorCounterPlugin()
    bench = TestBench(
        plugins=[observer, counter],
        log_coordinator=LogCoordinator(loggers=[]),
    )
    result = await bench.run(ErrorHandledAction(), params, rollup=False)
"""
from action_machine.logging.scoped_logger import ScopedLogger
from action_machine.plugins.decorators import on
from action_machine.plugins.events import (
    BeforeOnErrorAspectEvent,
    UnhandledErrorEvent,
)
from action_machine.plugins.plugin import Plugin


class ErrorObserverPlugin(Plugin):
    """
    Плагин-наблюдатель, записывающий все ошибки аспектов в state.

    Per-request состояние: {"errors": []}. Каждая ошибка добавляется
    как словарь с полями action, error_type, error_message, event_type.

    Подписан на два типа событий:

    1. UnhandledErrorEvent — ошибка без подходящего @on_error обработчика.
       Поля: error (Exception), failed_aspect_name (str | None).
       has_handler записывается как False.

    2. BeforeOnErrorAspectEvent — перед вызовом найденного @on_error.
       Поля: error (Exception), handler_name (str).
       has_handler записывается как True.

    Не подавляет ошибки и не изменяет результат — только наблюдает.
    """

    async def get_initial_state(self) -> dict:
        """Начальное состояние — пустой список ошибок."""
        return {"errors": []}

    @on(UnhandledErrorEvent)
    async def on_observe_unhandled(
        self,
        state: dict,
        event: UnhandledErrorEvent,
        log: ScopedLogger | None,
    ) -> dict:
        """
        Записывает информацию о необработанной ошибке в state["errors"].

        UnhandledErrorEvent эмитируется когда ни один @on_error обработчик
        не подошёл по типу исключения. После эмиссии этого события
        исходное исключение пробрасывается наружу из machine.run().
        """
        state["errors"].append({
            "action": event.action_name,
            "error_type": type(event.error).__name__,
            "error_message": str(event.error),
            "has_handler": False,
            "event_type": type(event).__name__,
            "failed_aspect_name": event.failed_aspect_name,
        })
        return state

    @on(BeforeOnErrorAspectEvent)
    async def on_observe_before_handler(
        self,
        state: dict,
        event: BeforeOnErrorAspectEvent,
        log: ScopedLogger | None,
    ) -> dict:
        """
        Записывает информацию об ошибке перед вызовом @on_error обработчика.

        BeforeOnErrorAspectEvent эмитируется когда машина нашла подходящий
        @on_error обработчик, но ещё не вызвала его. Плагин-наблюдатель
        фиксирует факт ошибки и имя обработчика.
        """
        state["errors"].append({
            "action": event.action_name,
            "error_type": type(event.error).__name__,
            "error_message": str(event.error),
            "has_handler": True,
            "event_type": type(event).__name__,
            "handler_name": event.handler_name,
        })
        return state


class ErrorCounterPlugin(Plugin):
    """
    Плагин-счётчик ошибок аспектов.

    Per-request состояние: {"count": 0, "handled_count": 0, "unhandled_count": 0}.
    Инкрементирует count при каждом событии ошибки.
    Разделяет на handled (BeforeOnErrorAspectEvent — обработчик найден)
    и unhandled (UnhandledErrorEvent — обработчик не найден).

    Подписан на два типа событий для раздельного подсчёта.
    """

    async def get_initial_state(self) -> dict:
        """Начальное состояние — нулевые счётчики."""
        return {"count": 0, "handled_count": 0, "unhandled_count": 0}

    @on(UnhandledErrorEvent)
    async def on_count_unhandled(
        self,
        state: dict,
        event: UnhandledErrorEvent,
        log: ScopedLogger | None,
    ) -> dict:
        """
        Инкрементирует счётчики для необработанной ошибки.

        count — общее количество ошибок.
        unhandled_count — ошибки без обработчика (пробросятся наружу).
        """
        state["count"] += 1
        state["unhandled_count"] += 1
        return state

    @on(BeforeOnErrorAspectEvent)
    async def on_count_handled(
        self,
        state: dict,
        event: BeforeOnErrorAspectEvent,
        log: ScopedLogger | None,
    ) -> dict:
        """
        Инкрементирует счётчики для обработанной ошибки.

        count — общее количество ошибок.
        handled_count — ошибки, для которых Action имеет обработчик.
        """
        state["count"] += 1
        state["handled_count"] += 1
        return state
