# tests/plugins/test_emit.py
"""
Тесты основного метода emit_event в PluginCoordinator.

Проверяем:
- Рассылку событий всем подходящим обработчикам
- Кеширование обработчиков
- Пропуск событий без обработчиков
- Передачу всех параметров в обработчики
"""

from unittest.mock import Mock

import pytest

from action_machine.Plugins.Decorators import on
from action_machine.Plugins.PluginCoordinator import PluginCoordinator

from .conftest import MockParams, SimplePlugin


class TestPluginCoordinatorEmit:
    """Тесты основного метода emit_event."""

    # ------------------------------------------------------------------
    # ТЕСТЫ: Базовая рассылка
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_emit_event_with_handlers(self, mock_action, mock_factory, mock_context):
        """emit_event вызывает все подходящие обработчики."""
        plugin1 = SimplePlugin()
        plugin2 = SimplePlugin()
        coordinator = PluginCoordinator([plugin1, plugin2])

        params = MockParams()

        await coordinator.emit_event(
            event_name="test_event",
            action=mock_action,
            params=params,
            state_aspect={"key": "value"},
            is_summary=False,
            result=None,
            duration=0.5,
            factory=mock_factory,
            context=mock_context,
            nest_level=1,
        )

        # Проверяем что оба плагина вызваны
        assert plugin1.handlers_called == [("handle_test", "test_event")]
        assert plugin2.handlers_called == [("handle_test", "test_event")]

        # Проверяем что состояния обновились
        assert coordinator._plugin_states[id(plugin1)]["counter"] == 1
        assert coordinator._plugin_states[id(plugin2)]["counter"] == 1

    @pytest.mark.anyio
    async def test_emit_event_passes_correct_event_object(self, mock_action, mock_factory, mock_context):
        """emit_event создает правильный объект PluginEvent и передаёт его обработчикам."""

        class TrackingPlugin(SimplePlugin):
            @on("test_event", ".*", ignore_exceptions=False)
            async def handle_test(self, state, event):
                self.last_event = event
                state["counter"] = state.get("counter", 0) + 1
                self.handlers_called.append(("handle_test", event.event_name))
                return state

        plugin = TrackingPlugin()
        coordinator = PluginCoordinator([plugin])

        params = MockParams()
        state_aspect = {"test": "data"}

        await coordinator.emit_event(
            event_name="test_event",
            action=mock_action,
            params=params,
            state_aspect=state_aspect,
            is_summary=True,
            result=None,
            duration=1.5,
            factory=mock_factory,
            context=mock_context,
            nest_level=2,
        )

        # Проверяем поля события
        event = plugin.last_event
        assert event.event_name == "test_event"
        assert event.action_name == "test_plugin.MockAction"
        assert event.params is params
        assert event.state_aspect == state_aspect
        assert event.is_summary is True
        assert event.deps is mock_factory
        assert event.context is mock_context
        assert event.result is None
        assert event.duration == 1.5
        assert event.nest_level == 2

    # ------------------------------------------------------------------
    # ТЕСТЫ: Кеширование
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_emit_event_caches_handlers(self, mock_action, mock_factory, mock_context):
        """emit_event кеширует обработчики после первого вызова."""
        plugin = SimplePlugin()
        coordinator = PluginCoordinator([plugin])

        params = MockParams()

        # Первый вызов
        await coordinator.emit_event(
            event_name="test_event",
            action=mock_action,
            params=params,
            state_aspect={},
            is_summary=False,
            result=None,
            duration=None,
            factory=mock_factory,
            context=mock_context,
            nest_level=0,
        )

        # Проверяем что в кеше появилась запись
        cache_key = ("test_event", "test_plugin.MockAction")
        assert cache_key in coordinator._handler_cache

        # Сбрасываем счётчики плагина
        plugin.handlers_called = []

        # Второй вызов — должен использовать кеш
        await coordinator.emit_event(
            event_name="test_event",
            action=mock_action,
            params=params,
            state_aspect={},
            is_summary=False,
            result=None,
            duration=None,
            factory=mock_factory,
            context=mock_context,
            nest_level=0,
        )

        # Плагин всё равно вызван
        assert plugin.handlers_called == [("handle_test", "test_event")]

    # ------------------------------------------------------------------
    # ТЕСТЫ: Без обработчиков
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_emit_event_no_handlers(self, mock_action, mock_factory, mock_context):
        """emit_event без обработчиков ничего не делает."""
        plugin = SimplePlugin()  # только test_event
        coordinator = PluginCoordinator([plugin])

        params = MockParams()

        # Другое событие, для которого нет обработчиков
        await coordinator.emit_event(
            event_name="no_such_event",
            action=mock_action,
            params=params,
            state_aspect={},
            is_summary=False,
            result=None,
            duration=None,
            factory=mock_factory,
            context=mock_context,
            nest_level=0,
        )

        # Состояния не должны быть инициализированы
        assert coordinator._plugin_states == {}
        assert plugin.handlers_called == []

    @pytest.mark.anyio
    async def test_emit_event_empty_plugins_list(self, mock_action, mock_factory, mock_context):
        """emit_event с пустым списком плагинов не делает ничего."""
        coordinator = PluginCoordinator([])

        params = MockParams()

        # Не должно быть ошибок
        await coordinator.emit_event(
            event_name="any_event",
            action=mock_action,
            params=params,
            state_aspect={},
            is_summary=False,
            result=None,
            duration=None,
            factory=mock_factory,
            context=mock_context,
            nest_level=0,
        )

        # Состояния плагинов не должны измениться
        assert coordinator._plugin_states == {}

    # ------------------------------------------------------------------
    # ТЕСТЫ: Передача параметров
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_emit_event_with_result(self, mock_action, mock_factory, mock_context):
        """emit_event передаёт результат в обработчики (для global_finish)."""

        class ResultPlugin(SimplePlugin):
            @on("test_event", ".*", ignore_exceptions=False)
            async def handle_test(self, state, event):
                self.received_result = event.result
                self.handlers_called.append(("handle_test", event.event_name))
                return state

        plugin = ResultPlugin()
        coordinator = PluginCoordinator([plugin])

        params = MockParams()
        mock_result = Mock()

        await coordinator.emit_event(
            event_name="test_event",
            action=mock_action,
            params=params,
            state_aspect={},
            is_summary=False,
            result=mock_result,
            duration=0.5,
            factory=mock_factory,
            context=mock_context,
            nest_level=0,
        )

        assert plugin.received_result is mock_result

    @pytest.mark.anyio
    async def test_emit_event_with_duration(self, mock_action, mock_factory, mock_context):
        """emit_event передаёт длительность в обработчики."""

        class DurationPlugin(SimplePlugin):
            @on("test_event", ".*", ignore_exceptions=False)
            async def handle_test(self, state, event):
                self.received_duration = event.duration
                self.handlers_called.append(("handle_test", event.event_name))
                return state

        plugin = DurationPlugin()
        coordinator = PluginCoordinator([plugin])

        params = MockParams()
        test_duration = 2.5

        await coordinator.emit_event(
            event_name="test_event",
            action=mock_action,
            params=params,
            state_aspect={},
            is_summary=False,
            result=None,
            duration=test_duration,
            factory=mock_factory,
            context=mock_context,
            nest_level=0,
        )

        assert plugin.received_duration == test_duration