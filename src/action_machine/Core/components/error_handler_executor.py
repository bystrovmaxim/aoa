# src/action_machine/core/components/error_handler_executor.py
"""
Error handler executor component wrapper.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide a component entry point for the `@on_error` handling stage in the machine
orchestration. Currently delegates to existing machine internals; full logic
migration happens in a later step.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    ActionProductMachine / SagaCoordinator
        │
        └── ErrorHandlerExecutor.handle(machine, error, action, params,
                                        state, box, connections, context,
                                        runtime, plugin_ctx, failed_aspect_name)
                │
                └── machine._handle_aspect_error(...)   // temporary delegation

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Delegation target remains stable during scaffolding phase.
- Return value contract (BaseResult or exception propagation) is preserved.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path:
- Matching `@on_error` handler returns substitute `BaseResult`.

Edge case:
- No matching handler causes original exception propagation.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Implementation is temporary and delegates to a private machine method.
- All exceptions from the underlying method propagate unchanged.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: On‑error handler executor scaffolding.
CONTRACT: handle(...) -> BaseResult or re‑raise original exception.
INVARIANTS: delegation is temporary; signature matches protocol.
FLOW: machine -> ErrorHandlerExecutor.handle -> legacy machine method.
FAILURES: propagates OnErrorHandlerError, UnhandledErrorEvent, etc.
EXTENSION POINTS: future replacement with direct handler resolution logic.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from typing import Any


class ErrorHandlerExecutor:
    """Component entry point for @on_error handling stage.

    This is a scaffolding implementation that delegates to the existing
    machine's internal method. Full migration of on‑error handling logic will
    happen in a subsequent step.
    """

    async def handle(self, machine: object, **kwargs: Any) -> Any:
        """Delegate error handling to current machine logic."""
        return await machine._handle_aspect_error(**kwargs)  # noqa: SLF001