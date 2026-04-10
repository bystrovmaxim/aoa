"""
Saga coordination component.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide a dedicated component for saga compensation orchestration during error
paths. This Step 7 implementation owns reverse rollback order, compensator
invocation, and saga lifecycle events.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    ActionProductMachine (error path)
        │
        └── SagaCoordinator.execute(machine, saga_stack, ...)
                │
                ├── emit SagaRollbackStartedEvent
                ├── iterate frames in reverse order
                │   ├── emit BeforeCompensateAspectEvent
                │   ├── invoke compensator (ContextView-aware)
                │   ├── emit AfterCompensateAspectEvent
                │   └── on failure emit CompensateFailedEvent and continue
                └── emit SagaRollbackCompletedEvent

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Rollback order is reverse of successful regular aspect execution.
- Compensator failures never stop remaining rollback frames.
- Saga start/completion events are emitted exactly once per execution.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path:
- `execute(...)` unwinds all compensators and emits completion summary.

Edge case:
- One compensator fails, `CompensateFailedEvent` is emitted, loop continues.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

This component coordinates rollback only. It does not run regular aspects or
`@on_error` handlers.

AI-CORE-BEGIN
ROLE: Saga rollback coordinator.
CONTRACT: execute(...) performs full compensation unwind with event contracts.
INVARIANTS: reverse order, resilient rollback loop, stable start/end events.
FLOW: stack + error -> compensator sequence -> rollback summary event.
FAILURES: compensator failures are emitted and suppressed for continued unwind.
EXTENSION POINTS: custom compensation policy can replace this coordinator.
AI-CORE-END
"""

from __future__ import annotations

import time
from typing import Any, Protocol, cast

from action_machine.compensate.compensate_gate_host_inspector import (
    CompensateGateHostInspector,
)
from action_machine.context.context_view import ContextView
from action_machine.core.base_state import BaseState
from action_machine.core.components.aspect_executor import AspectExecutor
from action_machine.core.components.error_handler_executor import ErrorHandlerExecutor
from action_machine.core.saga_frame import SagaFrame
from action_machine.core.tools_box import ToolsBox
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.logging.scoped_logger import ScopedLogger
from action_machine.plugins.events import (
    AfterCompensateAspectEvent,
    BeforeCompensateAspectEvent,
    CompensateFailedEvent,
    SagaRollbackCompletedEvent,
    SagaRollbackStartedEvent,
)
from action_machine.plugins.plugin_coordinator import PluginCoordinator


class SagaCoordinator:
    """Component owning rollback execution for saga frames."""

    def __init__(
        self,
        aspect_executor: AspectExecutor,
        error_handler_executor: ErrorHandlerExecutor,
        plugin_coordinator: PluginCoordinator,
        log_coordinator: LogCoordinator,
    ) -> None:
        self._aspect_executor = aspect_executor
        self._error_handler_executor = error_handler_executor
        self._plugin_coordinator = plugin_coordinator
        self._log_coordinator = log_coordinator

    async def execute(
        self,
        machine: _MachineLike,
        *,
        saga_stack: list[SagaFrame],
        error: Exception,
        action: Any,
        params: Any,
        box: ToolsBox,
        connections: Any,
        context: Any,
        plugin_ctx: Any,
    ) -> None:
        """Run rollback over saga frames in reverse order."""
        _ = (
            self._aspect_executor,
            self._error_handler_executor,
            self._plugin_coordinator,
        )
        base_fields = machine._base_event_fields(
            action,
            context,
            params,
            box.nested_level,
        )
        plugin_kwargs = machine._build_plugin_emit_kwargs(box.nested_level)

        compensator_count = sum(1 for frame in saga_stack if frame.compensator is not None)
        aspect_names_reversed = tuple(frame.aspect_name for frame in reversed(saga_stack))
        await plugin_ctx.emit_event(
            SagaRollbackStartedEvent(
                **base_fields,
                error=error,
                stack_depth=len(saga_stack),
                compensator_count=compensator_count,
                aspect_names=aspect_names_reversed,
            ),
            **plugin_kwargs,
        )

        succeeded = 0
        failed = 0
        skipped = 0
        failed_aspects: list[str] = []
        started_at = time.time()

        for frame in reversed(saga_stack):
            if frame.compensator is None:
                skipped += 1
                continue
            comp_meta: CompensateGateHostInspector.Snapshot.Compensator = frame.compensator
            await plugin_ctx.emit_event(
                BeforeCompensateAspectEvent(
                    **base_fields,
                    aspect_name=frame.aspect_name,
                    state_snapshot=None,
                    error=error,
                    compensator_name=comp_meta.method_name,
                    compensator_state_before=frame.state_before,
                    compensator_state_after=frame.state_after,
                ),
                **plugin_kwargs,
            )

            comp_started_at = time.time()
            try:
                comp_log = ScopedLogger(
                    coordinator=self._log_coordinator,
                    nest_level=box.nested_level,
                    machine_name=machine.__class__.__name__,
                    mode=machine._mode,
                    action_name=action.get_full_class_name(),
                    aspect_name=comp_meta.method_name,
                    context=context,
                    state=(
                        frame.state_before
                        if isinstance(frame.state_before, BaseState)
                        else BaseState()
                    ),
                    params=params,
                )
                comp_box = ToolsBox(
                    run_child=box.run_child,
                    factory=box.factory,
                    resources=box.resources,
                    context=context,
                    log=comp_log,
                    nested_level=box.nested_level,
                    rollup=box.rollup,
                )
                if comp_meta.context_keys:
                    ctx_view = ContextView(context, comp_meta.context_keys)
                    method_ref = cast(Any, comp_meta.method_ref)
                    await method_ref(
                        action,
                        params,
                        frame.state_before,
                        frame.state_after,
                        comp_box,
                        connections,
                        error,
                        ctx_view,
                    )
                else:
                    method_ref = cast(Any, comp_meta.method_ref)
                    await method_ref(
                        action,
                        params,
                        frame.state_before,
                        frame.state_after,
                        comp_box,
                        connections,
                        error,
                    )
                duration = time.time() - comp_started_at
                await plugin_ctx.emit_event(
                    AfterCompensateAspectEvent(
                        **base_fields,
                        aspect_name=frame.aspect_name,
                        state_snapshot=None,
                        error=error,
                        compensator_name=comp_meta.method_name,
                        duration_ms=duration * 1000,
                    ),
                    **plugin_kwargs,
                )
                succeeded += 1
            except Exception as comp_error:
                await plugin_ctx.emit_event(
                    CompensateFailedEvent(
                        **base_fields,
                        aspect_name=frame.aspect_name,
                        state_snapshot=None,
                        original_error=error,
                        compensator_error=comp_error,
                        compensator_name=comp_meta.method_name,
                        failed_for_aspect=frame.aspect_name,
                    ),
                    **plugin_kwargs,
                )
                failed += 1
                failed_aspects.append(frame.aspect_name)

        duration = time.time() - started_at
        await plugin_ctx.emit_event(
            SagaRollbackCompletedEvent(
                **base_fields,
                error=error,
                total_frames=len(saga_stack),
                succeeded=succeeded,
                failed=failed,
                skipped=skipped,
                duration_ms=duration * 1000,
                failed_aspects=tuple(failed_aspects),
            ),
            **plugin_kwargs,
        )


class _MachineLike(Protocol):
    _mode: str

    def _base_event_fields(
        self,
        action: Any,
        context: Any,
        params: Any,
        nest_level: int,
    ) -> dict[str, Any]:
        pass

    def _build_plugin_emit_kwargs(self, nest_level: int) -> dict[str, Any]:
        pass
