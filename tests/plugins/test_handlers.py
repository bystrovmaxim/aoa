# tests/plugins/test_handlers.py
"""
Тесты выполнения обработчиков (_run_single_handler) и управления состояниями.
"""

import pytest

from action_machine.Plugins.PluginCoordinator import PluginCoordinator

from .conftest import CustomStatePlugin, MultiHandlerPlugin, SimplePlugin


class TestPluginCoordinatorRunHandlers:
    @pytest.mark.anyio
    async def test_run_single_handler(self, event_factory):
        plugin = SimplePlugin()
        coordinator = PluginCoordinator([plugin])

        await coordinator._init_plugin_states()
        event = event_factory(event_name="test_event")

        handlers = coordinator._get_handlers("test_event", event.action_name)
        handler, ignore, _ = handlers[0]

        await coordinator._run_single_handler(handler, ignore, plugin, event)

        assert plugin.handlers_called == [("handle_test", "test_event")]
        assert coordinator._plugin_states[id(plugin)]["counter"] == 1

    @pytest.mark.anyio
    async def test_run_multiple_handlers_same_plugin(self, event_factory):
        plugin = MultiHandlerPlugin()
        coordinator = PluginCoordinator([plugin])

        await coordinator._init_plugin_states()

        # Генерируем событие, на которое подписан только один метод
        event = event_factory(event_name="event1")
        handlers = coordinator._get_handlers("event1", event.action_name)

        for handler, ignore, p in handlers:
            await coordinator._run_single_handler(handler, ignore, p, event)

        # Вызовется только handle_event1, так как get_handlers ищет точное совпадение
        assert len(plugin.handlers_called) == 1
        assert plugin.handlers_called[0] == ("event1", "event1")

    @pytest.mark.anyio
    async def test_plugins_independent_states(self, event_factory):
        plugin1 = SimplePlugin()
        plugin2 = SimplePlugin()
        coordinator = PluginCoordinator([plugin1, plugin2])

        await coordinator._init_plugin_states()

        coordinator._plugin_states[id(plugin1)]["counter"] = 10
        coordinator._plugin_states[id(plugin2)]["counter"] = 20

        event = event_factory(event_name="test_event")
        handlers = coordinator._get_handlers("test_event", event.action_name)

        for handler, ignore, plugin in handlers:
            await coordinator._run_single_handler(handler, ignore, plugin, event)

        assert coordinator._plugin_states[id(plugin1)]["counter"] == 11
        assert coordinator._plugin_states[id(plugin2)]["counter"] == 21


class TestPluginCoordinatorStates:
    @pytest.mark.anyio
    async def test_init_plugin_states(self):
        plugin1 = SimplePlugin()
        plugin2 = MultiHandlerPlugin()
        coordinator = PluginCoordinator([plugin1, plugin2])

        assert len(coordinator._plugin_states) == 0
        await coordinator._init_plugin_states()

        assert len(coordinator._plugin_states) == 2
        assert coordinator._plugin_states[id(plugin1)] == {"counter": 0}
        assert coordinator._plugin_states[id(plugin2)] == {"last": None, "any": False}

    @pytest.mark.anyio
    async def test_init_plugin_states_with_custom_initial(self):
        plugin = CustomStatePlugin()
        coordinator = PluginCoordinator([plugin])

        await coordinator._init_plugin_states()

        state = coordinator._plugin_states[id(plugin)]
        assert isinstance(state, CustomStatePlugin.MyState)
        assert state.value == 0

    @pytest.mark.anyio
    async def test_init_plugin_states_idempotent(self):
        plugin = SimplePlugin()
        coordinator = PluginCoordinator([plugin])

        await coordinator._init_plugin_states()
        coordinator._plugin_states[id(plugin)]["counter"] = 42

        await coordinator._init_plugin_states()
        assert coordinator._plugin_states[id(plugin)]["counter"] == 42
