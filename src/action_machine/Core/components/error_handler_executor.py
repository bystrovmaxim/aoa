# src/action_machine/core/components/error_handler_executor.py
"""
Error handler executor component wrapper.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide a dedicated component for the `@on_error` stage in machine execution.
This Step 6 implementation owns handler resolution, invocation, and fallback
event contracts.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    ActionProductMachine
        │
        └── ErrorHandlerExecutor.handle(machine, error, action, params,
                                        state, box, connections, context,
                                        runtime, plugin_ctx, failed_aspect_name)
                │
                ├── resolve first matching handler by isinstance
                ├── emit BeforeOnErrorAspectEvent
                ├── invoke handler (with ContextView when required)
                ├── emit AfterOnErrorAspectEvent
                └── or emit UnhandledErrorEvent and re-raise original error

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Handler resolution order is declaration order, first match wins.
- Event ordering and fallback semantics are preserved.
- Handler failures are wrapped into `OnErrorHandlerError`.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path:
- Matching `@on_error` handler returns substitute `BaseResult`.

Edge case:
- No matching handler emits `UnhandledErrorEvent` then re-raises.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Component depends on machine helper methods for event base fields.
- Executor does not mutate pipeline state; it returns handled result only.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: On-error handler execution component.
CONTRACT: handle(...) -> BaseResult or re‑raise original exception.
INVARIANTS: first matching handler wins; event order remains stable.
FLOW: resolve handler -> emit before -> invoke -> emit after/fallback.
FAILURES: OnErrorHandlerError on handler failure; original error when unhandled.
EXTENSION POINTS: custom handler strategy can replace this component.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import time
from typing import Any
from typing import cast

from action_machine.context.context_view import ContextView
from action_machine.core.base_result import BaseResult
from action_machine.core.exceptions import OnErrorHandlerError
from action_machine.plugins.events import (
    AfterOnErrorAspectEvent,
    BeforeOnErrorAspectEvent,
    UnhandledErrorEvent,
)


class ErrorHandlerExecutor:
    """Component owning `@on_error` resolution and invocation."""

    async def handle(
        self,
        machine: object,
        *,
        error: Exception,
        action: Any,
        params: Any,
        state: Any,
        box: Any,
        connections: Any,
        context: Any,
        runtime: Any,
        plugin_ctx: Any,
        failed_aspect_name: str | None,
    ) -> BaseResult:
        """Resolve and invoke matching `@on_error` handler."""
        base_fields = machine._base_event_fields(  # noqa: SLF001
            action,
            context,
            params,
            box.nested_level,
        )
        plugin_kwargs = machine._build_plugin_emit_kwargs(box.nested_level)  # noqa: SLF001

        handler_meta = None
        for candidate in runtime.error_handlers:
            if isinstance(error, candidate.exception_types):
                handler_meta = candidate
                break

        if handler_meta is None:
            await plugin_ctx.emit_event(
                UnhandledErrorEvent(
                    **base_fields,
                    error=error,
                    failed_aspect_name=failed_aspect_name,
                ),
                **plugin_kwargs,
            )
            raise error

        await plugin_ctx.emit_event(
            BeforeOnErrorAspectEvent(
                **base_fields,
                aspect_name=handler_meta.method_name,
                state_snapshot=state.to_dict(),
                error=error,
                handler_name=handler_meta.method_name,
            ),
            **plugin_kwargs,
        )
        started_at = time.time()
        try:
            if handler_meta.context_keys:
                ctx_view = ContextView(context, handler_meta.context_keys)
                result = await handler_meta.method_ref(
                    action,
                    params,
                    state,
                    box,
                    connections,
                    error,
                    ctx_view,
                )
            else:
                result = await handler_meta.method_ref(
                    action,
                    params,
                    state,
                    box,
                    connections,
                    error,
                )
            duration = time.time() - started_at
            await plugin_ctx.emit_event(
                AfterOnErrorAspectEvent(
                    **base_fields,
                    aspect_name=handler_meta.method_name,
                    state_snapshot=state.to_dict(),
                    error=error,
                    handler_name=handler_meta.method_name,
                    handler_result=cast("BaseResult", result),
                    duration_ms=duration * 1000,
                ),
                **plugin_kwargs,
            )
            return cast("BaseResult", result)
        except Exception as handler_error:
            raise OnErrorHandlerError(
                f"Error handler '{handler_meta.method_name}' in "
                f"{action.__class__.__name__} raised while handling "
                f"{type(error).__name__}: {handler_error}",
                handler_name=handler_meta.method_name,
                original_error=error,
            ) from handler_error