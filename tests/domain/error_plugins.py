# tests/domain/error_plugins.py
"""
Тестовые плагины для наблюдения за событием "on_error".

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Содержит плагины, подписанные на событие "on_error" для тестирования
механизма наблюдения за ошибками аспектов. Плагины-наблюдатели не могут
изменить результат или подавить ошибку — они только записывают информацию
в своё per-request состояние.

═══════════════════════════════════════════════════════════════════════════════
ПЛАГИНЫ
═══════════════════════════════════════════════════════════════════════════════

- ErrorObserverPlugin — записывает все ошибки в state["errors"].
  Подписан на "on_error" для всех Action (".*").

- ErrorCounterPlugin — считает количество ошибок в state["count"].
  Подписан на "on_error" для всех Action (".*").

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

    # Проверяем состояние плагинов через plugin_ctx (в тестах —
    # через прямой доступ к _plugin_coordinator).
"""

from action_machine.logging.scoped_logger import ScopedLogger
from action_machine.plugins.decorators import on
from action_machine.plugins.plugin import Plugin
from action_machine.plugins.plugin_event import PluginEvent


class ErrorObserverPlugin(Plugin):
    """
    Плагин-наблюдатель, записывающий все ошибки аспектов в state.

    Per-request состояние: {"errors": []}. Каждая ошибка добавляется
    как словарь с полями action, error_type, error_message, has_handler.

    Подписан на "on_error" для всех Action. Не подавляет ошибки
    и не изменяет результат.
    """

    async def get_initial_state(self) -> dict:
        """Начальное состояние — пустой список ошибок."""
        return {"errors": []}

    @on("on_error", ".*")
    async def on_observe_error(
        self,
        state: dict,
        event: PluginEvent,
        log: ScopedLogger | None,
    ) -> dict:
        """
        Записывает информацию об ошибке в state["errors"].

        Не изменяет результат и не подавляет ошибку — только наблюдает.
        Вызывается ДО обработчика @on_error на уровне Action.
        """
        state["errors"].append({
            "action": event.action_name,
            "error_type": type(event.error).__name__ if event.error else "None",
            "error_message": str(event.error) if event.error else "",
            "has_handler": event.has_action_handler,
        })
        return state


class ErrorCounterPlugin(Plugin):
    """
    Плагин-счётчик ошибок аспектов.

    Per-request состояние: {"count": 0, "handled_count": 0, "unhandled_count": 0}.
    Инкрементирует count при каждом событии "on_error".
    Разделяет на handled (has_action_handler=True) и unhandled.

    Подписан на "on_error" для всех Action.
    """

    async def get_initial_state(self) -> dict:
        """Начальное состояние — нулевые счётчики."""
        return {"count": 0, "handled_count": 0, "unhandled_count": 0}

    @on("on_error", ".*")
    async def on_count_error(
        self,
        state: dict,
        event: PluginEvent,
        log: ScopedLogger | None,
    ) -> dict:
        """
        Инкрементирует счётчики ошибок.

        count — общее количество ошибок.
        handled_count — ошибки, для которых Action имеет обработчик.
        unhandled_count — ошибки без обработчика (пробросятся наружу).
        """
        state["count"] += 1
        if event.has_action_handler:
            state["handled_count"] += 1
        else:
            state["unhandled_count"] += 1
        return state
