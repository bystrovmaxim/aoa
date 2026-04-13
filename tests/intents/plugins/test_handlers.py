# tests/intents/plugins/test_handlers.py
"""Tests for the execution of plugin handlers and per-request state management.

═══════════════════ ════════════════════ ════════════════════ ════════════════════
PURPOSE
═══════════════════ ════════════════════ ════════════════════ ════════════════════

Checks the key mechanism of the plugin system: the handler receives
current per-request state of the plugin, updates it and returns.
PluginRunContext saves the updated state and passes it on
to the next handler of the same plugin.

States are created via PluginCoordinator.create_run_context(),
which calls get_initial_state() for each plugin. Everyone
call create_run_context() creates a new isolated context −
the states of one run() do not affect the other.

═══════════════════ ════════════════════ ════════════════════ ════════════════════
SCENARIOS COVERED
═══════════════════ ════════════════════ ════════════════════ ════════════════════

Executing handlers:
- One handler for one plugin updates state["count"].
- Two handlers for one plugin per event: both are executed,
  update various fields of the general status.
- Two plugins are independent states: changes to one are not visible to the other.

Initializing states:
- create_run_context() initializes states from get_initial_state().
- Custom initial state via plugin constructor parameter.
- Repeated create_run_context() creates fresh states, independent
  from the previous context (idempotency)."""

import pytest

from action_machine.intents.plugins.plugin_coordinator import PluginCoordinator

from .conftest import (
    CounterPlugin,
    CustomInitPlugin,
    DualHandlerPlugin,
    emit_global_finish,
)

# ═════════════════════════════════════════════════════════════════════════════
#Handler execution tests
# ═════════════════════════════════════════════════════════════════════════════


class TestRunHandlers:
    """Tests of handler execution and per-request state updates."""

    @pytest.mark.anyio
    async def test_single_handler_updates_state(self):
        """One CounterPlugin handler increments state["count"]
        at each global_finish event."""
        #Arrange - one counter plugin, context with initial state
        plugin = CounterPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()

        #Act - send one global_finish event
        await emit_global_finish(plugin_ctx)

        #Assert - the counter has been incremented
        state = plugin_ctx.get_plugin_state(plugin)
        assert state["count"] == 1

    @pytest.mark.anyio
    async def test_multiple_events_accumulate(self):
        """Three consecutive events global_finish - counter
        incremented three times within one context."""
        #Arrange - counter plugin
        plugin = CounterPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()

        #Act - three events in a row
        await emit_global_finish(plugin_ctx)
        await emit_global_finish(plugin_ctx)
        await emit_global_finish(plugin_ctx)

        #Assert - three increments
        state = plugin_ctx.get_plugin_state(plugin)
        assert state["count"] == 3

    @pytest.mark.anyio
    async def test_two_handlers_same_plugin(self):
        """DualHandlerPlugin has two handlers on global_finish.
        Both execute and update different fields of the general state:
        handler_a → state["a"] += 1, handler_b → state["b"] += 10."""
        #Arrange - plugin with two handlers
        plugin = DualHandlerPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()

        #Act - one event triggers both handlers
        await emit_global_finish(plugin_ctx)

        #Assert - both fields are updated
        state = plugin_ctx.get_plugin_state(plugin)
        assert state["a"] == 1
        assert state["b"] == 10

    @pytest.mark.anyio
    async def test_two_plugins_independent_states(self):
        """CounterPlugin and DualHandlerPlugin have independent states.
        Changes made by one plugin are not visible to the other."""
        #Arrange - two plugins with different states
        counter = CounterPlugin()
        dual = DualHandlerPlugin()
        coordinator = PluginCoordinator(plugins=[counter, dual])
        plugin_ctx = await coordinator.create_run_context()

        #Act - one event is processed by both plugins
        await emit_global_finish(plugin_ctx)

        #Assert - states are independent
        counter_state = plugin_ctx.get_plugin_state(counter)
        dual_state = plugin_ctx.get_plugin_state(dual)

        assert counter_state["count"] == 1
        assert "a" not in counter_state
        assert "b" not in counter_state

        assert dual_state["a"] == 1
        assert dual_state["b"] == 10
        assert "count" not in dual_state


# ═════════════════════════════════════════════════════════════════════════════
#State initialization tests
# ═════════════════════════════════════════════════════════════════════════════


class TestPluginStates:
    """Tests for initialization and isolation of per-request plugin states."""

    @pytest.mark.anyio
    async def test_initial_state_from_get_initial_state(self):
        """create_run_context() initializes the plugin state
        value from get_initial_state(). CounterPlugin returns
        {"count": 0}."""
        #Arrange - counter plugin
        plugin = CounterPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])

        #Act - create a context (calls get_initial_state)
        plugin_ctx = await coordinator.create_run_context()

        #Assert - initial state corresponds to get_initial_state()
        state = plugin_ctx.get_plugin_state(plugin)
        assert state == {"count": 0}

    @pytest.mark.anyio
    async def test_custom_initial_value_through_constructor(self):
        """CustomInitPlugin accepts an initial_value in its constructor.
        get_initial_state() returns {"value": initial_value}."""
        #Arrange - plugin with custom initial value 42
        plugin = CustomInitPlugin(initial_value=42)
        coordinator = PluginCoordinator(plugins=[plugin])

        #Act - creating context
        plugin_ctx = await coordinator.create_run_context()

        #Assert - the initial state contains a custom value
        state = plugin_ctx.get_plugin_state(plugin)
        assert state == {"value": 42}

    @pytest.mark.anyio
    async def test_new_context_has_fresh_states(self):
        """Calling create_run_context() again creates a new context.
        with initial states. The previous context is not affected.
        This ensures isolation between calls to machine.run()."""
        #Arrange - counter plugin, coordinator
        plugin = CounterPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])

        #Act - first context: increment the counter
        ctx1 = await coordinator.create_run_context()
        await emit_global_finish(ctx1)
        state1_after = ctx1.get_plugin_state(plugin)

        #Act - second context: fresh initial state
        ctx2 = await coordinator.create_run_context()
        state2_initial = ctx2.get_plugin_state(plugin)

        #Assert - first context: counter == 1
        assert state1_after["count"] == 1

        #Assert - second context: counter == 0 (fresh state)
        assert state2_initial["count"] == 0

        #Assert - the first context has not changed since the second one was created
        assert ctx1.get_plugin_state(plugin)["count"] == 1
        assert ctx1.get_plugin_state(plugin)["count"] == 1
