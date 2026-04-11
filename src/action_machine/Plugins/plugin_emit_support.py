# src/action_machine/plugins/plugin_emit_support.py
"""
Public helpers for plugin event payloads and typed aspect-pipeline emissions.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide a small, typed surface for data passed into ``PluginRunContext.emit_event``:
shared ``BasePluginEvent`` keyword arguments, extra kwargs for ``emit_event``, and
async helpers that build and emit **regular** and **summary** aspect events. Keeps
``ActionProductMachine`` and coordinators such as ``SagaCoordinator`` free of
duplicated event construction for those pipeline stages.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``base_fields`` output matches the historical shape (``action_class``,
  ``action_name``, ``nest_level``, ``context``, ``params``).
- ``emit_extra_kwargs`` output matches the historical ``emit_event`` extras
  (``log_coordinator``, ``machine_name``, ``mode``).
- ``machine_class_name`` is the runtime class name of the machine at construction
  (subclass-aware).
- **No per-run state:** ``PluginRunContext`` is **never** stored on this object.
  Every emit helper takes ``plugin_ctx`` as an argument so one ``PluginEmitSupport``
  instance can serve many ``run`` calls without reset.

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
                └── emit_*_aspect(plugin_ctx, ...)  ──► await emit_event(...)

    SagaCoordinator.execute
        │
        ├── plugin_emit.base_fields(action, context, params, nest_level)
        ├── plugin_emit.emit_extra_kwargs(box.nested_level)
        └── ScopedLogger(..., machine_name=plugin_emit.machine_class_name,
                           mode=plugin_emit.mode, ...)

    ActionProductMachine._execute_regular_aspects / _execute_aspects_with_error_handling
        │
        └── await plugin_emit.emit_before_regular_aspect(plugin_ctx, ...)
            await plugin_emit.emit_after_regular_aspect(plugin_ctx, ...)
            await plugin_emit.emit_before_summary_aspect(plugin_ctx, ...)
            await plugin_emit.emit_after_summary_aspect(plugin_ctx, ...)

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path: the machine constructs one ``PluginEmitSupport``; the aspect pipeline
calls the ``emit_*_aspect`` helpers with the run-local ``plugin_ctx``.

Edge case: a test passes a stub ``plugin_ctx`` that records ``emit_event`` calls
to assert event types and payloads without a full ``PluginCoordinator``.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

Exceptions from ``plugin_ctx.emit_event`` propagate to the caller. Global start
and finish events are still emitted by the machine (see plan: part 2 may move them
here).

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Plugin event envelope factory + aspect-pipeline emit façade.
CONTRACT: Stable shapes for BasePluginEvent kwargs and emit_event extras;
  regular/summary aspect events built only inside this type for those stages.
INVARIANTS: No I/O; immutable config after construction; no stored PluginRunContext.
FLOW: Machine constructs once → components call base_fields / emit_extra_kwargs /
  emit_*_aspect with a per-run plugin_ctx.
FAILURES: Delegates to plugin_ctx.emit_event (handler/plugin errors propagate).
EXTENSION POINTS: Subclass or replace when custom event base shapes are required.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from typing import Any

from action_machine.context.context import Context
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.plugins.events import (
    AfterRegularAspectEvent,
    AfterSummaryAspectEvent,
    BeforeRegularAspectEvent,
    BeforeSummaryAspectEvent,
)
from action_machine.plugins.plugin_run_context import PluginRunContext


class PluginEmitSupport:
    """
    Builds shared plugin event fields, emit extras, and emits aspect pipeline events.

    AI-CORE-BEGIN
    ROLE: Public alternative to inlined event construction on the machine.
    CONTRACT: ``base_fields`` + ``emit_extra_kwargs`` match historical machine output;
      aspect emit helpers delegate to ``plugin_ctx.emit_event`` with a passed-in ctx.
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
