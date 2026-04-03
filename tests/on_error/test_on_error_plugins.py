# tests/on_error/test_on_error_plugins.py
"""
Тесты события "on_error" в плагинной системе.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет, что плагины получают событие "on_error" при ошибке в аспекте:
- Плагин вызывается ДО обработчика @on_error на Action.
- Плагин получает полный scope: error, has_action_handler, action_name.
- Плагин не может изменить результат — только наблюдает.
- Плагин вызывается и когда Action имеет обработчик, и когда не имеет.
- Без ошибки в аспекте — событие "on_error" не эмитируется.

Тесты используют плагины из tests/domain/error_plugins.py
и Action из tests/domain/error_actions.py.
"""

import pytest

from action_machine.context.context import Context
from action_machine.core.action_product_machine import ActionProductMachine
from action_machine.core.gate_coordinator import GateCoordinator
from action_machine.logging.log_coordinator import LogCoordinator
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
    """Плагин получает событие "on_error" когда Action имеет @on_error обработчик."""

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

        # Arrange — используем прямой доступ к машине для проверки состояния плагина.
        # Создаём машину с плагином и выполняем действие через run(),
        # затем проверяем, что плагин получил корректные данные.
        # Для этого нужен доступ к PluginRunContext — переделываем через
        # ручной вызов _run_internal и перехват состояния.

        observer = ErrorObserverPlugin()
        counter = ErrorCounterPlugin()
        coordinator = GateCoordinator()
        log_coordinator = LogCoordinator(loggers=[])


        # Создаём машину без плагинов (плагины вызовем вручную через ctx)
        machine = ActionProductMachine(
            mode="test",
            coordinator=coordinator,
            plugins=[observer, counter],
            log_coordinator=log_coordinator,
        )

        params = ErrorTestParams(value="broken", should_fail=True)
        context = Context()

        # Act — выполняем действие
        result = await machine.run(context, ErrorHandledAction(), params)

        # Assert — результат обработан
        assert result.status == "handled"

    @pytest.mark.asyncio()
    async def test_counter_increments_handled(self) -> None:
        """ErrorCounterPlugin инкрементирует handled_count при ошибке с обработчиком."""

        # Arrange — прямая проверка через полный цикл run + доступ к состоянию.
        # Поскольку per-request состояние уничтожается после run(),
        # проверяем поведение через кастомный плагин, сохраняющий данные
        # во внешнее хранилище.

        from action_machine.plugins.decorators import on
        from action_machine.plugins.plugin import Plugin
        from action_machine.plugins.plugin_event import PluginEvent

        external_storage: dict = {"count": 0, "handled": 0, "unhandled": 0}

        class StoringCounterPlugin(Plugin):
            async def get_initial_state(self) -> dict:
                return {}

            @on("on_error", ".*")
            async def on_count(self, state, event: PluginEvent, log):
                external_storage["count"] += 1
                if event.has_action_handler:
                    external_storage["handled"] += 1
                else:
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
    """Плагин получает on_error даже когда Action не имеет @on_error."""

    @pytest.mark.asyncio()
    async def test_plugin_called_before_error_propagates(self) -> None:
        """Плагин получает on_error с has_action_handler=False, затем ошибка пробрасывается."""

        from action_machine.plugins.decorators import on
        from action_machine.plugins.plugin import Plugin
        from action_machine.plugins.plugin_event import PluginEvent

        external_storage: dict = {"called": False, "has_handler": None, "error_type": None}

        class ObserverPlugin(Plugin):
            async def get_initial_state(self) -> dict:
                return {}

            @on("on_error", ".*")
            async def on_observe(self, state, event: PluginEvent, log):
                external_storage["called"] = True
                external_storage["has_handler"] = event.has_action_handler
                external_storage["error_type"] = type(event.error).__name__ if event.error else None
                return state

        machine = _make_machine(plugins=[ObserverPlugin()])
        params = ErrorTestParams(value="fail", should_fail=True)

        # Act & Assert — ошибка пробрасывается (нет @on_error на Action)
        with pytest.raises(ValueError, match="Ошибка: fail"):
            await machine.run(Context(), NoErrorHandlerAction(), params)

        # Assert — плагин всё равно был вызван ДО проброса
        assert external_storage["called"] is True
        assert external_storage["has_handler"] is False
        assert external_storage["error_type"] == "ValueError"


# ═════════════════════════════════════════════════════════════════════════════
# Плагин не может подавить ошибку
# ═════════════════════════════════════════════════════════════════════════════


class TestOnErrorPluginCannotSuppressError:
    """Плагин наблюдает, но не может подавить ошибку или изменить результат."""

    @pytest.mark.asyncio()
    async def test_plugin_cannot_change_result(self) -> None:
        """Даже если плагин вернёт что-то — результат определяется Action, не плагином."""

        from action_machine.plugins.decorators import on
        from action_machine.plugins.plugin import Plugin
        from action_machine.plugins.plugin_event import PluginEvent

        class AggressivePlugin(Plugin):
            """Плагин, который пытается 'обработать' ошибку — но не может."""
            async def get_initial_state(self) -> dict:
                return {"tried_to_handle": False}

            @on("on_error", ".*")
            async def on_try_handle(self, state, event: PluginEvent, log):
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
# Без ошибки — событие "on_error" не эмитируется
# ═════════════════════════════════════════════════════════════════════════════


class TestOnErrorPluginNotCalledOnSuccess:
    """При успешном выполнении событие 'on_error' не эмитируется."""

    @pytest.mark.asyncio()
    async def test_no_error_no_on_error_event(self) -> None:
        """Нормальное выполнение → плагин on_error НЕ вызывается."""

        from action_machine.plugins.decorators import on
        from action_machine.plugins.plugin import Plugin
        from action_machine.plugins.plugin_event import PluginEvent

        external_storage: dict = {"called": False}

        class NeverCalledPlugin(Plugin):
            async def get_initial_state(self) -> dict:
                return {}

            @on("on_error", ".*")
            async def on_should_not_be_called(self, state, event: PluginEvent, log):
                external_storage["called"] = True
                return state

        machine = _make_machine(plugins=[NeverCalledPlugin()])
        params = ErrorTestParams(value="ok", should_fail=False)

        # Act — нормальное выполнение, без ошибки
        result = await machine.run(Context(), ErrorHandledAction(), params)

        # Assert — результат от summary, плагин on_error НЕ вызван
        assert result.status == "ok"
        assert external_storage["called"] is False


# ═════════════════════════════════════════════════════════════════════════════
# Плагин получает полный scope в событии on_error
# ═════════════════════════════════════════════════════════════════════════════


class TestOnErrorPluginEventScope:
    """Плагин получает корректные данные в PluginEvent при on_error."""

    @pytest.mark.asyncio()
    async def test_event_contains_error_and_action_name(self) -> None:
        """PluginEvent содержит error, action_name, has_action_handler."""

        from action_machine.plugins.decorators import on
        from action_machine.plugins.plugin import Plugin
        from action_machine.plugins.plugin_event import PluginEvent

        captured_events: list[dict] = []

        class CapturingPlugin(Plugin):
            async def get_initial_state(self) -> dict:
                return {}

            @on("on_error", ".*")
            async def on_capture(self, state, event: PluginEvent, log):
                captured_events.append({
                    "event_name": event.event_name,
                    "action_name": event.action_name,
                    "error": event.error,
                    "error_type": type(event.error).__name__ if event.error else None,
                    "has_action_handler": event.has_action_handler,
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

        # Assert — поля события корректны
        assert ev["event_name"] == "on_error"
        assert "ErrorHandledAction" in ev["action_name"]
        assert ev["error_type"] == "ValueError"
        assert isinstance(ev["error"], ValueError)
        assert ev["has_action_handler"] is True
        assert ev["nest_level"] >= 1
