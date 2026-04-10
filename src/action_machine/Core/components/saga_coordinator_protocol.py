"""
Protocol for saga coordination component.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Define the contract for rollback coordination over saga frames after aspect
failures. Implementations orchestrate compensator execution and saga-level
event semantics.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Rollback order is reverse of successful regular-aspect execution.
- Compensator failures do not stop remaining rollback frames.
- Start/completed rollback events preserve stable emission order.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path:
- Rollback traverses stack in reverse and completes with summary event.

Edge case:
- One compensator fails but remaining compensators continue execution.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

The protocol defines rollback coordination only; handler selection and summary
execution are outside this contract.

AI-CORE-BEGIN
ROLE: Saga coordination contract.
CONTRACT: rollback(...) executes compensation unwind semantics.
INVARIANTS: reverse order, resilient compensator loop, stable events.
FLOW: saga stack + error -> rollback sequence -> completion.
FAILURES: compensator failures are recorded, not re-raised by contract.
EXTENSION POINTS: custom saga policies can implement this protocol.
AI-CORE-END
"""

from __future__ import annotations

from typing import Any, Protocol


class SagaCoordinatorProtocol(Protocol):
    """Contract for rollback coordination and saga flow execution."""

    async def rollback(self, machine: object, **kwargs: Any) -> None:
        """Execute rollback for currently accumulated saga frames."""