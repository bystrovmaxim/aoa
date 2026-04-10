# src/action_machine/core/components/aspect_executor_protocol.py
"""
Protocol for aspect execution component.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Define the contract for executing a single aspect (regular or summary) within
an action pipeline. The executor handles context injection, checker validation,
and state merging.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    ActionProductMachine / SagaCoordinator
        │
        └── AspectExecutorProtocol.call(machine, aspect_meta, action,
                                        params, state, box, connections, context)
                │
                ├── creates ContextView if aspect has @context_requires
                ├── invokes the aspect method with appropriate arguments
                ├── for regular aspects: validates returned dict with checkers
                └── returns raw result (dict for regular, BaseResult for summary)

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- The executor must not modify the input `state`; it returns the aspect result.
- Checker validation must be applied only to regular aspects.
- ContextView creation must be performed when `aspect_meta.context_keys` is non-empty.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path:
- Regular aspect returns state patch dict and passes checker validation.

Edge case:
- Summary aspect returns final `BaseResult` and bypasses regular checker flow.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Validation errors (e.g., missing required field) raise `ValidationFieldError`.
- Type mismatches in aspect return values raise `TypeError`.
- The executor does not manage state merging; that is the caller's responsibility.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Aspect executor contract.
CONTRACT: call(...) -> aspect raw result.
INVARIANTS: context injection per aspect meta; checkers applied to regular results.
FLOW: aspect meta + runtime data -> method invocation -> raw result.
FAILURES: ValidationFieldError, TypeError on contract violations.
EXTENSION POINTS: custom aspect execution can be injected via implementation.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from typing import Any, Protocol


class AspectExecutorProtocol(Protocol):
    """Contract for executing one regular/summary aspect."""

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
        """
        Execute one aspect and return its raw result.

        Args:
            machine: The executing machine (provides log coordinator and helpers).
            aspect_meta: Aspect snapshot metadata (type, method_ref, context_keys).
            action: Action instance being executed.
            params: Input parameters (frozen BaseParams).
            state: Current pipeline state (frozen BaseState).
            box: ToolsBox instance for the current execution scope.
            connections: Normalized resource managers dictionary.
            context: Execution context.

        Returns:
            For regular aspects: a `dict` of fields to merge into state.
            For summary aspects: a `BaseResult` instance.
        """
        ...