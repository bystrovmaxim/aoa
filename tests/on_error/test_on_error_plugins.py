# tests/on_error/test_on_error_plugins.py
"""
Тесты событий ошибок в плагинной системе.
═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════
Проверяет, что плагины получают типизированные события ошибок при
исключении в аспекте:

- BeforeOnErrorAspectEvent эмитируется когда Action имеет @on_error
  обработчик — плагин вызывается ДО вызова обработчика [1].
- UnhandledErrorEvent эмитируется когда Action НЕ имеет подходящего
  @on_error обработчика — плагин вызывается ДО проброса исключения [1].
- Плагин не может изменить результат — только наблюдает.
- Плагин вызывается и когда Action имеет обработчик, и когда не имеет.
- Без ошибки в аспекте — события ошибок не эмитируются.

В новой типизированной системе вместо единого строкового события
"on_error" с Optional-полем has_action_handler используются два
отдельных типа событий с разными полями:

    BeforeOnErrorAspectEvent  — обработчик найден (поля: error, handler_name)
    UnhandledErrorEvent       — обработчик не найден (поля: error, failed_aspect_name)

Тесты используют плагины из tests/domain/error_plugins.py
и Action из tests/domain/error_actions.py.
"""
import pytest

from action_machine.context.context import Context
from action_machine.core.action_product_machine import ActionProductMachine
from action_machine.core.gate_coordinator import GateCoordinator
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.plugins.decorators import on
from action_machine.plugins.events import (
    BeforeOnErrorAspectEvent,
    UnhandledErrorEvent,
)
from action_machine.plugins.plugin import Plugin
from tests.domain import (
    ErrorHandledAction,
    ErrorTestParams,
    NoErrorHandlerAction,
)
from tests.domain.error_plugins import ErrorCounterPlugin, ErrorObserverPlugin

# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательная функция для создания машины с плагинами
# ═════════════════════════════════════════════════════════════════════════════

def _make_machine(
    plugins: list,
) -> ActionProductMachine:
    """Создаёт машину с переданными плагинами и тихим логгером."""
    return ActionProductMachine(
        mode="test",
        coordinator=GateCoordinator(),
        plugins=plugins,
        log_coordinator=LogCoordinator(loggers=[]),
    )


# ═════════════════════════════════════════════════════════════════════════════
# Плагин вызывается при ошибке с обработчиком на Action
# ═════════════════════════════════════════════════════════════════════════════

class TestOnErrorPluginWithHandler:
    """
    Плагин получает BeforeOnErrorAspectEvent когда Action имеет @on_error обработчик.

    Машина эмитирует BeforeOnErrorAspectEvent перед вызовом найденного
    @on_error обработчика [1]. Событие содержит error (исключение) и
    handler_name (имя метода обработчика).
    """

    @pytest.mark.asyncio()
    async def test_observer_receives_error_event(self) -> None:
        """ErrorObserverPlugin записывает ошибку в state["errors"]."""
        # Arrange — плагин-наблюдатель + Action с обработчиком ValueError
        observer = ErrorObserverPlugin()
        machine = _make_machine(plugins=[observer])
        params = ErrorTestParams(value="test", should_fail=True)
        context = Context()

        # Act — аспект бросает ValueError, обработчик Action перехватывает
        result = await machine.run(context, ErrorHandledAction(), params)

        # Assert — результат от обработчика (ошибка обработана)
        assert result.status == "handled"

    @pytest.mark.asyncio()
    async def test_observer_records_error_details(self) -> None:
        """Плагин записывает тип ошибки, сообщение и наличие обработчика."""
        # Arrange
        observer = ErrorObserverPlugin()
        counter = ErrorCounterPlugin()
        machine = ActionProductMachine(
            mode="test",
            coordinator=GateCoordinator(),
            plugins=[observer, counter],
            log_coordinator=LogCoordinator(loggers=[]),
        )
        params = ErrorTestParams(value="broken", should_fail=True)
        context = Context()

        # Act — выполняем действие
        result = await machine.run(context, ErrorHandledAction(), params)

        # Assert — результат обработан
        assert result.status == "handled"

    @pytest.mark.asyncio()
    async def test_counter_increments_handled(self) -> None:
        """
        Плагин с внешним хранилищем инкрементирует handled_count
        при ошибке с обработчиком на Action.

        Подписан на BeforeOnErrorAspectEvent — эмитируется когда машина
        нашла подходящий @on_error обработчик [1].
        """
        external_storage: dict = {"count": 0, "handled": 0, "unhandled": 0}

        class StoringCounterPlugin(Plugin):
            async def get_initial_state(self) -> dict:
                return {}

            @on(BeforeOnErrorAspectEvent)
            async def on_count_handled(self, state, event: BeforeOnErrorAspectEvent, log):
                external_storage["count"] += 1
                external_storage["handled"] += 1
                return state

            @on(UnhandledErrorEvent)
            async def on_count_unhandled(self, state, event: UnhandledErrorEvent, log):
                external_storage["count"] += 1
                external_storage["unhandled"] += 1
                return state

        machine = _make_machine(plugins=[StoringCounterPlugin()])
        params = ErrorTestParams(value="test", should_fail=True)

        # Act — ошибка обработана Action
        result = await machine.run(Context(), ErrorHandledAction(), params)

        # Assert
        assert result.status == "handled"
        assert external_storage["count"] == 1
        assert external_storage["handled"] == 1
        assert external_storage["unhandled"] == 0


# ═════════════════════════════════════════════════════════════════════════════
# Плагин вызывается при ошибке БЕЗ обработчика на Action
# ═════════════════════════════════════════════════════════════════════════════

class TestOnErrorPluginWithoutHandler:
    """
    Плагин получает UnhandledErrorEvent когда Action не имеет @on_error.

    Машина эмитирует UnhandledErrorEvent когда ни один @on_error обработчик
    не подошёл по типу исключения [1]. После эмиссии события исходное
    исключение пробрасывается наружу.
    """

    @pytest.mark.asyncio()
    async def test_plugin_called_before_error_propagates(self) -> None:
        """Плагин получает UnhandledErrorEvent, затем ошибка пробрасывается."""
        external_storage: dict = {"called": False, "error_type": None}

        class ObserverPlugin(Plugin):
            async def get_initial_state(self) -> dict:
                return {}

            @on(UnhandledErrorEvent)
            async def on_observe(self, state, event: UnhandledErrorEvent, log):
                external_storage["called"] = True
                external_storage["error_type"] = type(event.error).__name__
                return state

        machine = _make_machine(plugins=[ObserverPlugin()])
        params = ErrorTestParams(value="fail", should_fail=True)

        # Act & Assert — ошибка пробрасывается (нет @on_error на Action)
        with pytest.raises(ValueError, match="Ошибка: fail"):
            await machine.run(Context(), NoErrorHandlerAction(), params)

        # Assert — плагин всё равно был вызван ДО проброса
        assert external_storage["called"] is True
        assert external_storage["error_type"] == "ValueError"


# ═════════════════════════════════════════════════════════════════════════════
# Плагин не может подавить ошибку
# ═════════════════════════════════════════════════════════════════════════════

class TestOnErrorPluginCannotSuppressError:
    """Плагин наблюдает, но не может подавить ошибку или изменить результат."""

    @pytest.mark.asyncio()
    async def test_plugin_cannot_change_result(self) -> None:
        """Даже если плагин вернёт что-то — результат определяется Action, не плагином."""

        class AggressivePlugin(Plugin):
            """Плагин, который пытается 'обработать' ошибку — но не может."""

            async def get_initial_state(self) -> dict:
                return {"tried_to_handle": False}

            @on(BeforeOnErrorAspectEvent)
            async def on_try_handle(self, state, event: BeforeOnErrorAspectEvent, log):
                state["tried_to_handle"] = True
                # Плагин не может подавить ошибку — только наблюдает.
                # Возвращаем state, но это не влияет на результат Action.
                return state

        machine = _make_machine(plugins=[AggressivePlugin()])
        params = ErrorTestParams(value="test", should_fail=True)

        # Act — Action имеет обработчик, результат от Action, не от плагина
        result = await machine.run(Context(), ErrorHandledAction(), params)

        # Assert — результат определяется @on_error обработчиком Action
        assert result.status == "handled"


# ═════════════════════════════════════════════════════════════════════════════
# Без ошибки — события ошибок не эмитируются
# ═════════════════════════════════════════════════════════════════════════════

class TestOnErrorPluginNotCalledOnSuccess:
    """При успешном выполнении события ошибок не эмитируются."""

    @pytest.mark.asyncio()
    async def test_no_error_no_error_event(self) -> None:
        """Нормальное выполнение → плагины на события ошибок НЕ вызываются."""
        external_storage: dict = {"called": False}

        class NeverCalledPlugin(Plugin):
            async def get_initial_state(self) -> dict:
                return {}

            @on(BeforeOnErrorAspectEvent)
            async def on_should_not_be_called_handled(self, state, event: BeforeOnErrorAspectEvent, log):
                external_storage["called"] = True
                return state

            @on(UnhandledErrorEvent)
            async def on_should_not_be_called_unhandled(self, state, event: UnhandledErrorEvent, log):
                external_storage["called"] = True
                return state

        machine = _make_machine(plugins=[NeverCalledPlugin()])
        params = ErrorTestParams(value="ok", should_fail=False)

        # Act — нормальное выполнение, без ошибки
        result = await machine.run(Context(), ErrorHandledAction(), params)

        # Assert — результат от summary, плагины ошибок НЕ вызваны
        assert result.status == "ok"
        assert external_storage["called"] is False


# ═════════════════════════════════════════════════════════════════════════════
# Плагин получает полный scope в событии ошибки
# ═════════════════════════════════════════════════════════════════════════════

class TestOnErrorPluginEventScope:
    """Плагин получает корректные данные в типизированном событии ошибки."""

    @pytest.mark.asyncio()
    async def test_event_contains_error_and_action_name(self) -> None:
        """BeforeOnErrorAspectEvent содержит error, action_name, handler_name."""
        captured_events: list[dict] = []

        class CapturingPlugin(Plugin):
            async def get_initial_state(self) -> dict:
                return {}

            @on(BeforeOnErrorAspectEvent)
            async def on_capture(self, state, event: BeforeOnErrorAspectEvent, log):
                captured_events.append({
                    "event_type": type(event).__name__,
                    "action_name": event.action_name,
                    "error": event.error,
                    "error_type": type(event.error).__name__,
                    "handler_name": event.handler_name,
                    "nest_level": event.nest_level,
                })
                return state

        machine = _make_machine(plugins=[CapturingPlugin()])
        params = ErrorTestParams(value="broken", should_fail=True)

        # Act
        await machine.run(Context(), ErrorHandledAction(), params)

        # Assert — один event захвачен
        assert len(captured_events) == 1
        ev = captured_events[0]

        # Assert — поля типизированного события корректны
        assert ev["event_type"] == "BeforeOnErrorAspectEvent"
        assert "ErrorHandledAction" in ev["action_name"]
        assert ev["error_type"] == "ValueError"
        assert isinstance(ev["error"], ValueError)
        assert isinstance(ev["handler_name"], str)
        assert ev["nest_level"] >= 1

    @pytest.mark.asyncio()
    async def test_unhandled_event_contains_failed_aspect_name(self) -> None:
        """UnhandledErrorEvent содержит error и failed_aspect_name."""
        captured_events: list[dict] = []

        class CapturingPlugin(Plugin):
            async def get_initial_state(self) -> dict:
                return {}

            @on(UnhandledErrorEvent)
            async def on_capture_unhandled(self, state, event: UnhandledErrorEvent, log):
                captured_events.append({
                    "event_type": type(event).__name__,
                    "action_name": event.action_name,
                    "error": event.error,
                    "error_type": type(event.error).__name__,
                    "failed_aspect_name": event.failed_aspect_name,
                    "nest_level": event.nest_level,
                })
                return state

        machine = _make_machine(plugins=[CapturingPlugin()])
        params = ErrorTestParams(value="fail", should_fail=True)

        # Act & Assert — ошибка пробрасывается
        with pytest.raises(ValueError):
            await machine.run(Context(), NoErrorHandlerAction(), params)

        # Assert — один event захвачен
        assert len(captured_events) == 1
        ev = captured_events[0]

        # Assert — поля UnhandledErrorEvent корректны
        assert ev["event_type"] == "UnhandledErrorEvent"
        assert "NoErrorHandlerAction" in ev["action_name"]
        assert ev["error_type"] == "ValueError"
        assert isinstance(ev["error"], ValueError)
        assert ev["nest_level"] >= 1
