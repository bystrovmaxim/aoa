# src/action_machine/runtime/saga_frame.py
"""
Saga compensation stack frame.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Each regular aspect with a compensator snapshot contributes one ``SagaFrame``
before its ``call()`` starts. The initial frame has ``state_after=None`` so a
mid-call exception can still be compensated. Once the call returns, the executor
replaces the immutable frame with one carrying merged ``state_after`` before
running checkers. Frames are unwound in reverse order when the pipeline fails.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    optional SagaFrame(..., state_after=None) if compensator exists
         |
         v
    regular aspect call() returned dict
         |
         +-- raise -> unwind pre-call frame
         |
         v
    merge state -> replace frame with state_after=merged
         |
         v
    validate result (checkers / declared fields)
         |
         v
    success continues; later failure unwinds current stack
         |
         v
    failure path -> reverse stack unwind in SagaCoordinator

Frame stores only aspect-unique rollback data:
- ``state_before``: state before aspect call
- ``state_after``: state after aspect call (or ``None`` when the call did not finish)
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
