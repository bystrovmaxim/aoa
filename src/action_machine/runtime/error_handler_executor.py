# src/action_machine/runtime/error_handler_executor.py
"""
Error handler executor component wrapper.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide a dedicated component for the `@on_error` stage in machine execution.
This Step 6 implementation owns handler resolution, invocation, and fallback
event contracts. Plugin event payloads come from ``PluginCoordinator``, not from
private methods on the machine.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    ActionProductMachine
        │
        └── ErrorHandlerExecutor.handle(error, action, params,
                                        state, box, connections, context,
                                        error_handler_nodes, plugin_ctx,
                                        failed_aspect_name)
                │
                ├── plugin_coordinator.base_fields / emit_extra_kwargs
                ├── resolve first matching handler by isinstance
                ├── emit BeforeOnErrorAspectEvent
                ├── invoke handler (with ContextView when required)
                ├── emit AfterOnErrorAspectEvent
                └── or emit UnhandledErrorEvent and re-raise original error

"""

from __future__ import annotations

import time
from typing import Any, cast

from action_machine.context.context_view import ContextView
from action_machine.exceptions.action_result_declaration_error import (
    ActionResultDeclarationError,
)
from action_machine.exceptions.action_result_type_error import ActionResultTypeError
from action_machine.exceptions.on_error_handler_error import OnErrorHandlerError
from action_machine.graph_model.nodes.error_handler_graph_node import ErrorHandlerGraphNode
from action_machine.intents.action_schema.action_schema_intent_resolver import (
    ActionSchemaIntentResolver,
)
from action_machine.intents.context_requires.context_requires_resolver import (
    ContextRequiresResolver,
)
from action_machine.model.base_result import BaseResult
from action_machine.plugin.events import (
    AfterOnErrorAspectEvent,
    BeforeOnErrorAspectEvent,
    UnhandledErrorEvent,
)
from action_machine.plugin.plugin_coordinator import PluginCoordinator


class ErrorHandlerExecutor:
    """Component owning `@on_error` resolution and invocation."""

    def __init__(self, plugin_coordinator: PluginCoordinator) -> None:
        self._plugin_coordinator = plugin_coordinator

    async def handle(
        self,
        *,
        error: Exception,
        action: Any,
        params: Any,
        state: Any,
        box: Any,
        connections: Any,
        context: Any,
        error_handler_nodes: list[ErrorHandlerGraphNode],
        plugin_ctx: Any,
        failed_aspect_name: str | None,
    ) -> BaseResult:
        """Resolve and invoke matching `@on_error` handler."""
        base_fields = self._plugin_coordinator.base_fields(
            action,
            context,
            params,
            box.nested_level,
        )
        plugin_kwargs = self._plugin_coordinator.emit_extra_kwargs(box.nested_level)

        handler_node = None
        for candidate in error_handler_nodes:
            exception_types = candidate.properties.get("exception_types", ())
            if isinstance(exception_types, tuple) and isinstance(error, exception_types):
                handler_node = candidate
                break

        if handler_node is None:
            await plugin_ctx.emit_event(
                UnhandledErrorEvent(
                    **base_fields,
                    error=error,
                    failed_aspect_name=failed_aspect_name,
                ),
                **plugin_kwargs,
            )
            raise error

        handler_name = handler_node.label
        handler_ref = handler_node.node_obj
        context_keys = frozenset(
            ContextRequiresResolver.resolve_required_context_keys(handler_ref),
        )

        await plugin_ctx.emit_event(
            BeforeOnErrorAspectEvent(
                **base_fields,
                aspect_name=handler_name,
                state_snapshot=state.to_dict(),
                error=error,
                handler_name=handler_name,
            ),
            **plugin_kwargs,
        )
        started_at = time.time()
        try:
            if context_keys:
                ctx_view = ContextView(context, context_keys)
                result = await handler_ref(
                    action,
                    params,
                    state,
                    box,
                    connections,
                    error,
                    ctx_view,
                )
            else:
                result = await handler_ref(
                    action,
                    params,
                    state,
                    box,
                    connections,
                    error,
                )
            ActionSchemaIntentResolver.resolve_result_type(type(action))
            bound = cast(BaseResult, result)
            duration = time.time() - started_at
            await plugin_ctx.emit_event(
                AfterOnErrorAspectEvent(
                    **base_fields,
                    aspect_name=handler_name,
                    state_snapshot=state.to_dict(),
                    error=error,
                    handler_name=handler_name,
                    handler_result=bound,
                    duration_ms=duration * 1000,
                ),
                **plugin_kwargs,
            )
            return bound
        except (ActionResultTypeError, ActionResultDeclarationError):
            raise
        except Exception as handler_error:
            raise OnErrorHandlerError(
                f"Error handler '{handler_name}' in "
                f"{action.__class__.__name__} raised while handling "
                f"{type(error).__name__}: {handler_error}",
                handler_name=handler_name,
                original_error=error,
            ) from handler_error
