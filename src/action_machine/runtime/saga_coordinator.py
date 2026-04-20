# src/action_machine/runtime/saga_coordinator.py
"""
Saga coordination component.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide a dedicated component for saga compensation orchestration during error
paths. This Step 7 implementation owns reverse rollback order, compensator
invocation, and saga lifecycle events. Plugin event payloads are built through
``PluginEmitSupport`` so this class does not call private methods on the machine.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    ActionProductMachine (error path)
        │
        └── SagaCoordinator.execute(saga_stack, ...)
                │
                ├── plugin_emit.base_fields / emit_extra_kwargs
                ├── emit SagaRollbackStartedEvent
                ├── iterate frames in reverse order
                │   ├── emit BeforeCompensateAspectEvent
                │   ├── invoke compensator (ContextView-aware)
                │   ├── emit AfterCompensateAspectEvent
                │   └── on failure emit CompensateFailedEvent and continue
                └── emit SagaRollbackCompletedEvent

"""

from __future__ import annotations

import time
from typing import Any, cast

from action_machine.context.context_view import ContextView
from action_machine.legacy.compensate_intent_inspector import (
    CompensateIntentInspector,
)
from action_machine.logging.domain_resolver import resolve_domain
from action_machine.logging.scoped_logger import ScopedLogger
from action_machine.model.base_state import BaseState
from action_machine.plugin.events import (
    AfterCompensateAspectEvent,
    BeforeCompensateAspectEvent,
    CompensateFailedEvent,
    SagaRollbackCompletedEvent,
    SagaRollbackStartedEvent,
)
from action_machine.plugin.plugin_coordinator import PluginCoordinator
from action_machine.plugin.plugin_emit_support import PluginEmitSupport
from action_machine.runtime.aspect_executor import AspectExecutor
from action_machine.runtime.error_handler_executor import ErrorHandlerExecutor
from action_machine.runtime.saga_frame import SagaFrame
from action_machine.runtime.tools_box import ToolsBox


class SagaCoordinator:
    """Component owning rollback execution for saga frames."""

    def __init__(
        self,
        aspect_executor: AspectExecutor,
        error_handler_executor: ErrorHandlerExecutor,
        plugin_coordinator: PluginCoordinator,
        plugin_emit: PluginEmitSupport,
    ) -> None:
        self._aspect_executor = aspect_executor
        self._error_handler_executor = error_handler_executor
        self._plugin_coordinator = plugin_coordinator
        self._plugin_emit = plugin_emit

    async def execute(
        self,
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
        base_fields = self._plugin_emit.base_fields(
            action,
            context,
            params,
            box.nested_level,
        )
        plugin_kwargs = self._plugin_emit.emit_extra_kwargs(box.nested_level)

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
            comp_meta: CompensateIntentInspector.Snapshot.Compensator = frame.compensator
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
                    coordinator=self._plugin_emit.log_coordinator,
                    nest_level=box.nested_level,
                    machine_name=self._plugin_emit.machine_class_name,
                    mode=self._plugin_emit.mode,
                    action_name=action.get_full_class_name(),
                    aspect_name=comp_meta.method_name,
                    context=context,
                    state=(
                        frame.state_before
                        if isinstance(frame.state_before, BaseState)
                        else BaseState()
                    ),
                    params=params,
                    domain=resolve_domain(type(action)),
                )
                comp_box = ToolsBox(
                    run_child=box.run_child,
                    factory=box.factory,
                    resources=box.resources,
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
