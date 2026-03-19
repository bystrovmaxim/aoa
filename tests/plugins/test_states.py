"""
Tests for plugin state management in PluginCoordinator.

Checks:
- Plugin state initialization
- Idempotency of initialization (subsequent calls do not reset state)
- Custom initial states
"""

import pytest

from action_machine.Plugins.PluginCoordinator import PluginCoordinator

from .conftest import CustomStatePlugin, SimplePlugin


class TestPluginCoordinatorStates:
    """Tests for plugin state management."""

    # ------------------------------------------------------------------
    # TESTS: State initialization
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_init_plugin_states(self):
        """
        Plugin state initialization.

        Verifies:
        - States are created for all plugins
        - States have the correct initial values
        """
        plugin1 = SimplePlugin()
        plugin2 = SimplePlugin()
        coordinator = PluginCoordinator([plugin1, plugin2])

        await coordinator._init_plugin_states()

        assert len(coordinator._plugin_states) == 2
        assert id(plugin1) in coordinator._plugin_states
        assert id(plugin2) in coordinator._plugin_states
        assert coordinator._plugin_states[id(plugin1)] == {"counter": 0}
        assert coordinator._plugin_states[id(plugin2)] == {"counter": 0}

    @pytest.mark.anyio
    async def test_init_plugin_states_idempotent(self):
        """
        Repeated initialization does not change existing states.

        If a state has already been modified, it should not be reset.
        """
        plugin = SimplePlugin()
        coordinator = PluginCoordinator([plugin])

        # First initialization
        await coordinator._init_plugin_states()
        state1 = coordinator._plugin_states[id(plugin)]

        # Modify the state
        state1["counter"] = 42

        # Second initialization
        await coordinator._init_plugin_states()

        # State should not be reset
        assert coordinator._plugin_states[id(plugin)]["counter"] == 42

    @pytest.mark.anyio
    async def test_init_plugin_states_with_custom_initial(self):
        """
        Plugin with a custom initial state.

        Verifies that get_initial_state() is called and returns
        the correct initial state.
        """
        plugin = CustomStatePlugin()
        coordinator = PluginCoordinator([plugin])

        await coordinator._init_plugin_states()

        state = coordinator._plugin_states[id(plugin)]
        assert state == {"value": 100, "items": [1, 2, 3]}

    @pytest.mark.anyio
    async def test_init_plugin_states_preserves_independence(self):
        """
        States of different plugins are independent.

        Changing one plugin's state does not affect others.
        """
        plugin1 = SimplePlugin()
        plugin2 = SimplePlugin()
        coordinator = PluginCoordinator([plugin1, plugin2])

        await coordinator._init_plugin_states()

        # Change the state of the first plugin
        coordinator._plugin_states[id(plugin1)]["counter"] = 100

        # The second plugin should remain unchanged
        assert coordinator._plugin_states[id(plugin2)]["counter"] == 0

    @pytest.mark.anyio
    async def test_init_plugin_states_lazy_initialization(self):
        """
        States are initialized lazily (only on first access).

        Before calling _init_plugin_states, the state dictionary is empty.
        """
        plugin = SimplePlugin()
        coordinator = PluginCoordinator([plugin])

        # Before initialization, states are empty
        assert coordinator._plugin_states == {}

        # After initialization, the state appears
        await coordinator._init_plugin_states()
        assert len(coordinator._plugin_states) == 1

    @pytest.mark.anyio
    async def test_init_plugin_states_without_plugins(self):
        """
        Initialization without plugins does not cause errors.
        """
        coordinator = PluginCoordinator([])

        # Should not raise an exception
        await coordinator._init_plugin_states()

        assert coordinator._plugin_states == {}