# src/action_machine/runtime/saga_frame.py
"""
Saga compensation stack frame.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Each regular aspect whose ``call()`` finished contributes one ``SagaFrame``
once result validation has run: on success the frame holds merged
``state_after``; on validation failure after ``call()`` the frame has
``state_after=None``. Frames are unwound in reverse order when the pipeline
fails.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    regular aspect call() returned dict
         |
         v
    validate result (checkers / declared fields)
         |
         +-- fail -> SagaFrame(..., state_after=None) -> raise
         |
         v
    merge state -> SagaFrame(..., state_after=merged)
         |
         v
    append to local saga stack (for current _run_internal call)
         |
         v
    failure path -> reverse stack unwind in SagaCoordinator

Frame stores only aspect-unique rollback data:
- ``state_before``: state before aspect call
- ``state_after``: state after aspect call (or ``None`` when rejected)
- ``compensator``: compensator metadata (or ``None``)
- ``aspect_name``: aspect identifier for diagnostics/events

Pipeline-common values (params, connections, context, box) are passed to
rollback executor as separate arguments and are not duplicated in each frame.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path:
    Aspect succeeds and checker passes -> frame keeps both ``state_before`` and
    ``state_after`` for potential rollback.

Edge case:
    Aspect ``call()`` returned but checker rejects output -> frame has
    ``state_after=None``; compensator still runs on unwind before earlier frames.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Immutable rollback metadata unit for one regular aspect step.
CONTRACT: Capture compensator binding and pre/post state snapshots per aspect.
INVARIANTS: Local per-run stack ownership and reverse-order unwind semantics.
FLOW: call -> validate -> frame append -> failure path -> coordinator unwind.
FAILURES: Missing compensator marks frame as skipped, not failed.
EXTENSION POINTS: Extend metadata fields cautiously without duplicating globals.
AI-CORE-END
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from action_machine.legacy.compensate_intent_inspector import (
        CompensateIntentInspector,
    )


@dataclass(frozen=True)
class SagaFrame:
    """
    One immutable compensation-stack frame.

    Captures per-aspect rollback metadata needed by saga coordinator.
    """

    compensator: CompensateIntentInspector.Snapshot.Compensator | None
    aspect_name: str
    state_before: object  # BaseState frozen instance
    state_after: object | None  # BaseState | None frozen instance
