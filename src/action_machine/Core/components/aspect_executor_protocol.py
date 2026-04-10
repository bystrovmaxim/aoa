# src/action_machine/core/components/aspect_executor_protocol.py
"""
Protocol for aspect execution component.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Define the contract for aspect execution in an action pipeline. The executor
handles invocation, regular-aspect validation, and immutable state merge.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    ActionProductMachine / SagaCoordinator
        │
        ├── call(...)
        ├── execute_regular(...)
        └── execute_summary(...)

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- `call(...)` preserves ContextView behavior for `context_requires`.
- `execute_regular(...)` validates checker contracts before merge.
- State transitions are immutable (new `BaseState` instance).

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path:
- `execute_regular(...)` returns merged state and payload dict.

Edge case:
- Regular aspect returning unknown fields raises `ValidationFieldError`.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Validation errors raise `ValidationFieldError`.
- Type mismatches in regular result raise `TypeError`.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Aspect execution component contract.
CONTRACT: call/execute_regular/execute_summary signatures.
INVARIANTS: context injection, checker validation, immutable merge.
FLOW: invoke -> validate -> merge -> optional saga stack update.
FAILURES: ValidationFieldError, TypeError on contract violations.
EXTENSION POINTS: custom aspect execution can be injected via implementation.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from typing import Any, Protocol


class AspectExecutorProtocol(Protocol):
    """Contract for aspect execution component."""

    async def call(
        self,
        machine: object,
        *,
        aspect_meta: Any,
        action: Any,
        params: Any,
        state: Any,
        box: Any,
        connections: Any,
        context: Any,
    ) -> Any:
        """Call one aspect and return raw result."""
        pass

    async def execute_regular(
        self,
        machine: object,
        *,
        aspect_meta: Any,
        action: Any,
        params: Any,
        state: Any,
        box: Any,
        connections: Any,
        context: Any,
        runtime: Any,
        saga_stack: list[Any],
    ) -> tuple[Any, dict[str, Any], float]:
        """Execute one regular aspect with validation and merge."""
        pass

    async def execute_summary(
        self,
        machine: object,
        *,
        summary_meta: Any,
        action: Any,
        params: Any,
        state: Any,
        box: Any,
        connections: Any,
        context: Any,
    ) -> tuple[Any, float]:
        """Execute summary aspect and return result with duration."""
        pass
