# src/action_machine/plugin/plugin_coordinator.py
"""
PluginCoordinator — stateless plugin lifecycle coordinator for ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

PluginCoordinator stores plugin instances, creates isolated run contexts
(``PluginRunContext``) for each ``run()`` call, and builds machine-owned plugin
events. Coordinator itself is per-request stateless: it keeps no mutable
per-request data.

All mutable plugin data (handler states and accumulated per-run values) lives
inside ``PluginRunContext``, which exists only for a single run lifecycle.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

PluginCoordinator is the single creation point for ``PluginRunContext`` and
the shared emitter for runtime-owned lifecycle events. ``ActionProductMachine``
holds a coordinator instance and calls ``create_run_context()`` at the start of
each ``_run_internal()``. Returned context is used for all ``emit_event()``
calls inside that run and then discarded.

    ActionProductMachine
        │
        │  self._plugin_coordinator = PluginCoordinator(plugins=[...])
        │
        │  In each _run_internal():
        │    plugin_ctx = await self._plugin_coordinator.create_run_context()
        │    ...
        │    await _plugin_coordinator.emit_global_start(plugin_ctx, ...)
        │    ... aspect pipeline ...
        │    await _plugin_coordinator.emit_global_finish(plugin_ctx, ...)
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

"""

from __future__ import annotations

from typing import Any

from action_machine.context.context import Context
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.plugin.events import (
    AfterRegularAspectEvent,
    AfterSummaryAspectEvent,
    BeforeRegularAspectEvent,
    BeforeSummaryAspectEvent,
    GlobalFinishEvent,
    GlobalStartEvent,
)
from action_machine.plugin.plugin import Plugin
from action_machine.plugin.plugin_run_context import PluginRunContext


class PluginCoordinator:
    """
AI-CORE-BEGIN
    ROLE: Runtime coordinator for plugin context creation and machine-owned event emissions.
    CONTRACT: Build context with initial states for registered plugins; build and emit shared lifecycle event payloads.
    INVARIANTS: Coordinator stores no mutable per-run plugin state.
    AI-CORE-END
"""

    def __init__(
        self,
        plugins: list[Plugin],
        log_coordinator: LogCoordinator | None = None,
    ) -> None:
        """
        Initialize plugin coordinator with registered plugin instances.
        """
        self._plugins: list[Plugin] = plugins
        self._log_coordinator = log_coordinator or LogCoordinator()

    @property
    def log_coordinator(self) -> LogCoordinator:
        """Log coordinator wired into plugin handler loggers."""
        return self._log_coordinator

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

    def base_fields(
        self,
        action: BaseAction[Any, Any],
        context: Context,
        params: BaseParams,
        nest_level: int,
    ) -> dict[str, Any]:
        """Keyword arguments shared by ``BasePluginEvent`` subclasses."""
        return {
            "action_class": type(action),
            "action_name": action.get_full_class_name(),
            "nest_level": nest_level,
            "context": context,
            "params": params,
        }

    def emit_extra_kwargs(self, _nest_level: int) -> dict[str, Any]:
        """Extra kwargs passed to ``PluginRunContext.emit_event``."""
        _ = _nest_level
        return {"log_coordinator": self._log_coordinator}

    async def emit_global_start(
        self,
        plugin_ctx: PluginRunContext,
        *,
        action: BaseAction[Any, Any],
        context: Context,
        params: BaseParams,
        nest_level: int,
    ) -> None:
        """Emit ``GlobalStartEvent`` after gates and before the aspect pipeline."""
        base = self.base_fields(action, context, params, nest_level)
        kwargs = self.emit_extra_kwargs(nest_level)
        await plugin_ctx.emit_event(GlobalStartEvent(**base), **kwargs)

    async def emit_global_finish(
        self,
        plugin_ctx: PluginRunContext,
        *,
        action: BaseAction[Any, Any],
        context: Context,
        params: BaseParams,
        nest_level: int,
        result: BaseResult,
        duration_ms: float,
    ) -> None:
        """Emit ``GlobalFinishEvent`` with the final result and total duration."""
        base = self.base_fields(action, context, params, nest_level)
        kwargs = self.emit_extra_kwargs(nest_level)
        await plugin_ctx.emit_event(
            GlobalFinishEvent(**base, result=result, duration_ms=duration_ms),
            **kwargs,
        )

    async def emit_before_regular_aspect(
        self,
        plugin_ctx: PluginRunContext,
        *,
        action: BaseAction[Any, Any],
        context: Context,
        params: BaseParams,
        nest_level: int,
        aspect_name: str,
        state_snapshot: dict[str, Any],
    ) -> None:
        """Emit ``BeforeRegularAspectEvent`` for one regular aspect."""
        base = self.base_fields(action, context, params, nest_level)
        kwargs = self.emit_extra_kwargs(nest_level)
        await plugin_ctx.emit_event(
            BeforeRegularAspectEvent(
                **base,
                aspect_name=aspect_name,
                state_snapshot=state_snapshot,
            ),
            **kwargs,
        )

    async def emit_after_regular_aspect(
        self,
        plugin_ctx: PluginRunContext,
        *,
        action: BaseAction[Any, Any],
        context: Context,
        params: BaseParams,
        nest_level: int,
        aspect_name: str,
        state_snapshot: dict[str, Any],
        aspect_result: dict[str, Any],
        duration_ms: float,
    ) -> None:
        """Emit ``AfterRegularAspectEvent`` for one regular aspect."""
        base = self.base_fields(action, context, params, nest_level)
        kwargs = self.emit_extra_kwargs(nest_level)
        await plugin_ctx.emit_event(
            AfterRegularAspectEvent(
                **base,
                aspect_name=aspect_name,
                state_snapshot=state_snapshot,
                aspect_result=aspect_result,
                duration_ms=duration_ms,
            ),
            **kwargs,
        )

    async def emit_before_summary_aspect(
        self,
        plugin_ctx: PluginRunContext,
        *,
        action: BaseAction[Any, Any],
        context: Context,
        params: BaseParams,
        nest_level: int,
        aspect_name: str,
        state_snapshot: dict[str, Any],
    ) -> None:
        """Emit ``BeforeSummaryAspectEvent`` before the summary aspect."""
        base = self.base_fields(action, context, params, nest_level)
        kwargs = self.emit_extra_kwargs(nest_level)
        await plugin_ctx.emit_event(
            BeforeSummaryAspectEvent(
                **base,
                aspect_name=aspect_name,
                state_snapshot=state_snapshot,
            ),
            **kwargs,
        )

    async def emit_after_summary_aspect(
        self,
        plugin_ctx: PluginRunContext,
        *,
        action: BaseAction[Any, Any],
        context: Context,
        params: BaseParams,
        nest_level: int,
        aspect_name: str,
        state_snapshot: dict[str, Any],
        result: BaseResult,
        duration_ms: float,
    ) -> None:
        """Emit ``AfterSummaryAspectEvent`` after the summary aspect returns."""
        base = self.base_fields(action, context, params, nest_level)
        kwargs = self.emit_extra_kwargs(nest_level)
        await plugin_ctx.emit_event(
            AfterSummaryAspectEvent(
                **base,
                aspect_name=aspect_name,
                state_snapshot=state_snapshot,
                result=result,
                duration_ms=duration_ms,
            ),
            **kwargs,
        )
