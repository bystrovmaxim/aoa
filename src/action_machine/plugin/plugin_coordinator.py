# src/action_machine/plugin/plugin_coordinator.py
"""
PluginCoordinator — stateless plugin lifecycle coordinator for ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

PluginCoordinator stores plugin instances and creates isolated run contexts
(``PluginRunContext``) for each ``run()`` call. Coordinator itself is fully
stateless: it keeps no mutable per-request data.

All mutable plugin data (handler states and accumulated per-run values) lives
inside ``PluginRunContext``, which exists only for a single run lifecycle.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

PluginCoordinator is the single creation point for ``PluginRunContext``.
``ActionProductMachine`` holds coordinator instance and calls
``create_run_context()`` at the start of each ``_run_internal()``.
Returned context is used for all ``emit_event()`` calls inside that run and
then discarded.

    ActionProductMachine
        │
        │  self._plugin_coordinator = PluginCoordinator(plugins=[...])
        │
        │  In each _run_internal():
        │    plugin_ctx = await self._plugin_coordinator.create_run_context()
        │    ...
        │    await plugin_ctx.emit_event(GlobalStartEvent(...), ...)
        │    ... aspect pipeline ...
        │    await plugin_ctx.emit_event(GlobalFinishEvent(...), ...)
        │    ... plugin_ctx is discarded (out of scope) ...
        ▼

═══════════════════════════════════════════════════════════════════════════════
REQUEST ISOLATION
═══════════════════════════════════════════════════════════════════════════════

Each ``ActionProductMachine._run_internal`` call (including nested child runs)
creates its own ``PluginRunContext``. Parallel root runs (e.g. via
``asyncio.gather``) also use separate contexts. State does not leak across run
levels or concurrent requests.

If plugin needs cross-request accumulation (metrics/counters), it should use
external storage passed via plugin constructor. Framework guarantees per-request
state isolation; long-term accumulation policy is user responsibility.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.plugin.plugin_coordinator import PluginCoordinator

    coordinator = PluginCoordinator(plugins=[CounterPlugin(), MetricsPlugin()])

    # At the start of each run():
    plugin_ctx = await coordinator.create_run_context()

    # Emit typed events through context:
    await plugin_ctx.emit_event(
        GlobalStartEvent(action_class=..., ...),
        log_coordinator=log_coord,
        machine_name="ActionProductMachine",
        mode="production",
        coordinator=gate_coordinator,
    )

    # Read plugin state in tests:
    state = plugin_ctx.get_plugin_state(counter_plugin)
"""

from __future__ import annotations

from typing import Any

from action_machine.plugin.plugin import Plugin
from action_machine.plugin.plugin_run_context import PluginRunContext


class PluginCoordinator:
    """
    Stateless plugin lifecycle coordinator.

    Stores plugin instance list and creates isolated ``PluginRunContext`` for
    every run call.

    AI-CORE-BEGIN
    ROLE: Runtime coordinator for plugin context creation per run.
    CONTRACT: Build context with initial states for registered plugins.
    INVARIANTS: Coordinator remains stateless across requests.
    AI-CORE-END
    """

    def __init__(
        self,
        plugins: list[Plugin],
    ) -> None:
        """
        Initialize plugin coordinator with registered plugin instances.
        """
        self._plugins: list[Plugin] = plugins

    async def create_run_context(self) -> PluginRunContext:
        """
        Create isolated plugin context for one run invocation.

        Calls ``get_initial_state()`` for each plugin and creates
        ``PluginRunContext`` with resulting initial states map.
        """
        initial_states: dict[int, Any] = {}
        for plugin in self._plugins:
            plugin_id = id(plugin)
            state = await plugin.get_initial_state()
            initial_states[plugin_id] = state

        return PluginRunContext(
            plugins=self._plugins,
            initial_states=initial_states,
        )

    @property
    def plugins(self) -> list[Plugin]:
        """
        Return registered plugin instances.
        """
        return self._plugins
