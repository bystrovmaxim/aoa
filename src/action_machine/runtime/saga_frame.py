# src/action_machine/runtime/saga_frame.py
"""
Saga compensation stack frame.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Each successfully executed regular aspect contributes one ``SagaFrame``.
Frames are collected in a per-run local stack and unwound in reverse order
during rollback when pipeline execution fails.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    regular aspect succeeds
         |
         v
    create SagaFrame(state_before, state_after, compensator, aspect_name)
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
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Every ``_run_internal`` call owns its own independent local stack.
- Nested child actions maintain isolated stacks.
- Frames with ``compensator=None`` are skipped during unwind.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path:
    Aspect succeeds and checker passes -> frame keeps both ``state_before`` and
    ``state_after`` for potential rollback.

Edge case:
    Aspect succeeds but checker rejects output -> ``state_after`` may be ``None``.
    Compensators then lack post-aspect state keys (e.g. external ids never
    written into state). See ``compensate`` package ERRORS / LIMITATIONS for
    application-level external-consistency patterns.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- ``SagaFrame`` is data-only; rollback policy/execution lives in coordinator.
- Correctness depends on accurate frame creation timing in pipeline executor.
- ``state_before/state_after`` are typed as ``object`` to avoid runtime coupling.
- ``state_after is None`` does not imply “no external side effects”; it means the
  pipeline did not adopt checker-passed state. External systems are not tracked
  by the frame beyond what the app put in ``state_before`` / ``params`` / logs.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Immutable rollback metadata unit for one regular aspect step.
CONTRACT: Capture compensator binding and pre/post state snapshots per aspect.
INVARIANTS: Local per-run stack ownership and reverse-order unwind semantics.
FLOW: aspect success -> frame append -> failure path -> coordinator unwind.
FAILURES: Missing compensator marks frame as skipped, not failed.
EXTENSION POINTS: Extend metadata fields cautiously without duplicating globals.
AI-CORE-END
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from action_machine.graph.inspectors.compensate_intent_inspector import (
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
