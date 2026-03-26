# tests/plugins/test_emit.py
"""
Тесты метода emit_event в PluginCoordinator.
"""

from unittest.mock import Mock

import pytest

from action_machine.plugins.plugin_coordinator import PluginCoordinator

from .conftest import SimplePlugin


class TestPluginCoordinatorEmit:
    @pytest.mark.anyio
    async def test_emit_event_with_handlers(self, mock_action, mock_params, mock_factory, mock_context):
        plugin = SimplePlugin()
        coordinator = PluginCoordinator([plugin])

        await coordinator.emit_event(
            event_name="test_event",
            action=mock_action,
            params=mock_params,
            state_aspect={},
            is_summary=False,
            result=None,
            duration=None,
            factory=mock_factory,
            context=mock_context,
            nest_level=0,
        )

        assert plugin.handlers_called == [("handle_test", "test_event")]
        assert coordinator._plugin_states[id(plugin)]["counter"] == 1

    @pytest.mark.anyio
    async def test_emit_event_passes_correct_event_object(self, mock_action, mock_params, mock_factory, mock_context):
        plugin = SimplePlugin()
        captured_event = None
        original_handle = plugin.handle_test

        async def mock_handle(state, event):
            nonlocal captured_event
            captured_event = event
            return await original_handle(state, event)

        coordinator = PluginCoordinator([plugin])

        original_run = coordinator._run_single_handler
        async def wrap_run(handler, ignore, p, event):
            nonlocal captured_event
            captured_event = event
            return await original_run(handler, ignore, p, event)

        coordinator._run_single_handler = wrap_run

        await coordinator.emit_event(
            event_name="test_event",
            action=mock_action,
            params=mock_params,
            state_aspect={"step": 1},
            is_summary=True,
            result=None,
            duration=None,
            factory=mock_factory,
            context=mock_context,
            nest_level=2,
        )

        assert captured_event is not None
        assert captured_event.event_name == "test_event"

    @pytest.mark.anyio
    async def test_emit_event_caches_handlers(self, mock_action, mock_params, mock_factory, mock_context):
        plugin = SimplePlugin()
        coordinator = PluginCoordinator([plugin])

        await coordinator.emit_event(
            event_name="test_event",
            action=mock_action,
            params=mock_params,
            state_aspect={},
            is_summary=False,
            result=None,
            duration=None,
            factory=mock_factory,
            context=mock_context,
            nest_level=0,
        )

        action_name = mock_action.get_full_class_name()
        cache_key = ("test_event", action_name)
        cached_handlers = coordinator._handler_cache[cache_key]

        # Заменяем AsyncMock на Mock, так как метод синхронный
        coordinator._get_handlers = Mock(return_value=cached_handlers)

        await coordinator.emit_event(
            event_name="test_event",
            action=mock_action,
            params=mock_params,
            state_aspect={},
            is_summary=False,
            result=None,
            duration=None,
            factory=mock_factory,
            context=mock_context,
            nest_level=0,
        )

        coordinator._get_handlers.assert_called_once_with("test_event", action_name)

    @pytest.mark.anyio
    async def test_emit_event_no_handlers(self, mock_action, mock_params, mock_factory, mock_context):
        plugin = SimplePlugin()
        coordinator = PluginCoordinator([plugin])
        coordinator._init_plugin_states = Mock()

        await coordinator.emit_event(
            event_name="unknown_event",
            action=mock_action,
            params=mock_params,
            state_aspect={},
            is_summary=False,
            result=None,
            duration=None,
            factory=mock_factory,
            context=mock_context,
            nest_level=0,
        )

        assert plugin.handlers_called == []
        coordinator._init_plugin_states.assert_not_called()

    @pytest.mark.anyio
    async def test_emit_event_empty_plugins_list(self, mock_action, mock_params, mock_factory, mock_context):
        coordinator = PluginCoordinator([])
        await coordinator.emit_event(
            event_name="test_event",
            action=mock_action,
            params=mock_params,
            state_aspect={},
            is_summary=False,
            result=None,
            duration=None,
            factory=mock_factory,
            context=mock_context,
            nest_level=0,
        )
        assert len(coordinator._handler_cache) == 1
