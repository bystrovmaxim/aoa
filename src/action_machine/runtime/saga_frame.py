# src/action_machine/runtime/saga_frame.py
"""
Saga compensation stack frame.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Each regular aspect whose ``call()`` finished may contribute one ``SagaFrame``
after validation: only when that aspect has a compensator snapshot from the
facet cache (aspects without ``@compensate`` do not push a frame). On success
the frame holds merged ``state_after``; on validation failure after ``call()`` the
frame has ``state_after=None``. Frames are unwound in reverse order when the pipeline
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
    merge state -> optional SagaFrame(..., state_after=merged) if compensator exists
         |
         v
    append to local saga stack (undoable aspects only)
         |
         v
    failure path -> reverse stack unwind in SagaCoordinator

Frame stores only aspect-unique rollback data:
- ``state_before``: state before aspect call
- ``state_after``: state after aspect call (or ``None`` when rejected)
- ``compensator``: compensator metadata (required for pushed frames; stack holds only actionable undo)
- ``aspect_name``: aspect identifier for diagnostics/events

Pipeline-common values (params, connections, context, box) are passed to
rollback executor as separate arguments and are not duplicated in each frame.

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

    Appended only for regular aspects that have a compensator; rollback metadata
    flows to saga coordinator.
    """

    compensator: CompensateIntentInspector.Snapshot.Compensator | None
    aspect_name: str
    state_before: object  # BaseState frozen instance
    state_after: object | None  # BaseState | None frozen instance
