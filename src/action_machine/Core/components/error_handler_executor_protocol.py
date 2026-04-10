# src/action_machine/core/components/error_handler_executor_protocol.py
"""
Protocol for on‑error handling component.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Define the contract for resolving and invoking `@on_error` handlers when an
aspect execution fails. The executor must locate a matching handler, execute it,
and return a substitute `BaseResult` or propagate the original exception.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    SagaCoordinator / ActionProductMachine
        │
        └── ErrorHandlerExecutorProtocol.handle(machine, error, action, params,
                                                state, box, connections, context,
                                                runtime, plugin_ctx, failed_aspect)
                │
                ├── searches runtime.error_handlers for matching exception type
                ├── creates ContextView if handler has @context_requires
                ├── invokes handler with appropriate signature
                ├── emits BeforeOnErrorAspectEvent / AfterOnErrorAspectEvent
                └── returns BaseResult from handler, or raises UnhandledErrorEvent

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Handlers are evaluated in declaration order; first match wins.
- If no handler matches, `UnhandledErrorEvent` is emitted and the original
  exception is re‑raised.
- `OnErrorHandlerError` is raised if the handler itself fails.
- Plugin events must be emitted in the same order as the current machine.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path:
- Matching handler returns substitute result and execution continues.

Edge case:
- No matching handler -> original exception is re-raised after error event.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- The executor does not modify the pipeline state; it only returns a substitute
  result.
- The fallback behavior when no handler is found is identical to the current
  machine implementation.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: On‑error handler executor contract.
CONTRACT: handle(...) -> BaseResult or re‑raise original exception.
INVARIANTS: handlers evaluated top‑to‑bottom; events emitted in correct order.
FLOW: error + runtime -> matching handler -> substitute result or exception.
FAILURES: UnhandledErrorEvent on no match; OnErrorHandlerError on handler failure.
EXTENSION POINTS: custom error handling can be injected via implementation.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from typing import Any, Protocol


class ErrorHandlerExecutorProtocol(Protocol):
    """Contract for handling execution errors through on_error handlers."""

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
    ) -> Any:
        """
        Handle aspect error and return handled result when possible.

        Args:
            machine: The executing machine (provides log/plugin coordinators).
            error: The exception raised during aspect execution.
            action: Action instance being executed.
            params: Input parameters (frozen BaseParams).
            state: Pipeline state at the moment of failure.
            box: ToolsBox instance for the current execution scope.
            connections: Normalized resource managers dictionary.
            context: Execution context.
            runtime: Pre‑computed action execution cache.
            plugin_ctx: Plugin run context for event emission.
            failed_aspect_name: Name of the aspect that raised the error,
                or None if the error occurred outside an aspect.

        Returns:
            A `BaseResult` produced by the matched `@on_error` handler.

        Raises:
            The original exception if no handler matches.
            OnErrorHandlerError if a matched handler raises an exception.
        """
        ...
