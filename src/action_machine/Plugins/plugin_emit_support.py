# src/action_machine/plugins/plugin_emit_support.py
"""
Public helpers for building plugin event payloads.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide a small, typed surface for the data passed into ``PluginRunContext.emit_event``:
shared ``BasePluginEvent`` keyword arguments and the extra kwargs (log coordinator,
machine name, mode). Keeps coordinators such as ``SagaCoordinator`` independent of
private methods on ``ActionProductMachine``.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``base_fields`` output matches the historical shape produced by the machine’s
  former static helper (action_class, action_name, nest_level, context, params).
- ``emit_extra_kwargs`` output matches the historical ``_build_plugin_emit_kwargs``
  contract for ``emit_event``.
- ``machine_class_name`` is the runtime class name of the machine instance at
  construction time (supports subclasses).

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
                └── emit_extra_kwargs(nest_level) ──► **kwargs for emit_event

    SagaCoordinator.execute
        │
        ├── plugin_emit.base_fields(action, context, params, nest_level)
        ├── plugin_emit.emit_extra_kwargs(box.nested_level)
        └── ScopedLogger(..., machine_name=plugin_emit.machine_class_name,
                           mode=plugin_emit.mode, ...)

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path: machine constructs one ``PluginEmitSupport``; aspect pipeline and saga
rollback both consume ``base_fields`` / ``emit_extra_kwargs`` from the same object.

Edge case: a test injects a stub ``PluginEmitSupport`` with fixed dicts to assert
event shapes without constructing a full machine.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

This type does not emit events itself; callers still build concrete event classes
and call ``plugin_ctx.emit_event``.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Plugin event envelope factory (shared fields + emit kwargs).
CONTRACT: stable dict shapes for BasePluginEvent and emit_event extras.
INVARIANTS: no I/O; immutable configuration after construction.
FLOW: machine builds once -> components read base_fields / emit_extra_kwargs.
FAILURES: none by design (pure data assembly).
EXTENSION POINTS: subclass or replace when custom event base shapes are required.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from typing import Any

from action_machine.context.context import Context
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.logging.log_coordinator import LogCoordinator


class PluginEmitSupport:
    """
    Builds shared plugin event fields and ``emit_event`` extras.

    AI-CORE-BEGIN
    ROLE: Public alternative to calling private helpers on the machine.
    CONTRACT: ``base_fields`` + ``emit_extra_kwargs`` match machine legacy output.
    INVARIANTS: ``machine_class_name`` frozen at construction.
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
