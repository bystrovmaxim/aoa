# src/action_machine/plugin/plugin_emit_support.py
"""
Public helpers for plugin event payloads and typed aspect-pipeline emissions.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide a small, typed surface for data passed into ``PluginRunContext.emit_event``:
shared ``BasePluginEvent`` keyword arguments, extra kwargs for ``emit_event``, and
async helpers that build and emit **global** lifecycle events plus **regular** and
**summary** aspect events. Keeps ``ActionProductMachine`` and coordinators such as
``SagaCoordinator`` free of duplicated event construction for those pipeline stages.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    ActionProductMachine.__init__
        │
        └── PluginEmitSupport(log_coordinator, machine_class_name, mode)
                │
                ├── base_fields(...)  ──► **kwargs for BasePluginEvent subclasses
                │
                ├── emit_extra_kwargs(nest_level) ──► **kwargs for emit_event
                │
                ├── emit_global_start / emit_global_finish(plugin_ctx, ...)
                │
                └── emit_*_aspect(plugin_ctx, ...)  ──► await emit_event(...)

    SagaCoordinator.execute
        │
        ├── plugin_emit.base_fields(action, context, params, nest_level)
        ├── plugin_emit.emit_extra_kwargs(box.nested_level)
        └── ScopedLogger(..., machine_name=plugin_emit.machine_class_name,
                           mode=plugin_emit.mode, domain=resolve_domain(type(action)), ...)

    ActionProductMachine._run_internal
        │
        ├── await plugin_emit.emit_global_start(plugin_ctx, ...)
        ├── await _execute_aspects_with_error_handling(...)
        └── await plugin_emit.emit_global_finish(plugin_ctx, ...)

    ActionProductMachine._execute_regular_aspects / _execute_aspects_with_error_handling
        │
        └── await plugin_emit.emit_before_regular_aspect(plugin_ctx, ...)
            await plugin_emit.emit_after_regular_aspect(plugin_ctx, ...)
            await plugin_emit.emit_before_summary_aspect(plugin_ctx, ...)
            await plugin_emit.emit_after_summary_aspect(plugin_ctx, ...)

═══════════════════════════════════════════════════════════════════════════════
COMPONENTS
═══════════════════════════════════════════════════════════════════════════════

- ``PluginEmitSupport``: immutable envelope builder and emit facade.
- ``base_fields(...)``: shared kwargs for ``BasePluginEvent`` subclasses.
- ``emit_extra_kwargs(...)``: stable extra kwargs for ``emit_event``.
- ``emit_global_start`` / ``emit_global_finish``: global lifecycle events.
- ``emit_before_*`` / ``emit_after_*``: regular and summary aspect events.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path: the machine constructs one ``PluginEmitSupport``; ``_run_internal`` calls
``emit_global_start`` / ``emit_global_finish`` and the aspect pipeline uses the
``emit_*_aspect`` helpers, all with the run-local ``plugin_ctx``.

Edge case: a test passes a stub ``plugin_ctx`` that records ``emit_event`` calls
to assert event types and payloads without a full ``PluginCoordinator``.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Plugin event envelope factory + emit façade for global and aspect pipeline
  events owned by the production machine path.
CONTRACT: Stable shapes for BasePluginEvent kwargs and emit_event extras; global
  start/finish and regular/summary aspect events built only here for those stages.
INVARIANTS: No I/O; immutable config after construction; no stored PluginRunContext.
FLOW: Machine constructs once → _run_internal and nested helpers call emit_* with
  a per-run plugin_ctx.
FAILURES: Delegates to plugin_ctx.emit_event (handler/plugin errors propagate).
EXTENSION POINTS: Subclass or replace when custom event base shapes are required.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
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
from action_machine.plugin.plugin_run_context import PluginRunContext


class PluginEmitSupport:
    """
    Builds shared plugin fields, emit extras, and emits global + aspect pipeline events.

    AI-CORE-BEGIN
    ROLE: Public alternative to inlined event construction on the machine.
    CONTRACT: ``base_fields`` + ``emit_extra_kwargs`` match historical machine output;
      global and aspect emit helpers delegate to ``plugin_ctx.emit_event``.
    INVARIANTS: ``machine_class_name`` frozen at construction; no ``PluginRunContext``
      stored on ``self``.
    AI-CORE-END
    """

    __slots__ = ("_log_coordinator", "_machine_class_name", "_mode")

    def __init__(
        self,
        log_coordinator: LogCoordinator,
        *,
        machine_class_name: str,
        mode: str,
    ) -> None:
        self._log_coordinator = log_coordinator
        self._machine_class_name = machine_class_name
        self._mode = mode

    @property
    def log_coordinator(self) -> LogCoordinator:
        """Log coordinator wired into ``emit_event`` extras."""
        return self._log_coordinator

    @property
    def machine_class_name(self) -> str:
        """Machine class name used in logs and plugin kwargs (subclass-aware)."""
        return self._machine_class_name

    @property
    def mode(self) -> str:
        """Execution mode string (e.g. production vs test)."""
        return self._mode

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
        """Extra kwargs passed to ``PluginRunContext.emit_event`` (after event object)."""
        _ = _nest_level
        return {
            "log_coordinator": self._log_coordinator,
            "machine_name": self._machine_class_name,
            "mode": self._mode,
        }

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
        """Emit ``BeforeRegularAspectEvent`` for one regular aspect (before execution)."""
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
        """Emit ``AfterRegularAspectEvent`` for one regular aspect (after execution)."""
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
        """Emit ``BeforeSummaryAspectEvent`` immediately before the summary aspect."""
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
