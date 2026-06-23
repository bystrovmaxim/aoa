# packages/aoa-action-machine/src/aoa/action_machine/runtime/saga_frame.py
"""
Saga compensation stack frame.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Each regular aspect contributes one ``SagaFrame`` before its ``call()`` starts.
The initial frame has ``state_after=None`` so a mid-call exception can still be
represented. Once the regular aspect step succeeds, the pipeline replaces the
immutable frame with one carrying the returned ``state_after``. Frames with no
compensator are skipped during rollback but still expose aspect states to
``GlobalFinishEvent``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    SagaFrame(..., state_after=None)
         |
         v
    regular aspect call() returned dict
         |
         +-- raise -> unwind pre-call frame
         |
         v
    validate result + replace state (checkers / declared fields)
         |
         v
    replace frame with state_after=returned state
         |
         v
    success continues; later failure unwinds current stack
         |
         v
    failure path -> reverse stack unwind in SagaCoordinator

Frame stores only aspect-unique rollback data:
- ``state_before``: state before aspect call
- ``state_after``: state after aspect call (or ``None`` when the call did not finish)
- ``compensator``: optional compensator graph node; ``None`` frames are read-only
  aspect-state records and are skipped by rollback.
- ``aspect_name``: aspect identifier for diagnostics/events

Pipeline-common values (params, connections, context, box) are passed to
rollback executor as separate arguments and are not duplicated in each frame.

"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aoa.action_machine.graph.nodes.compensator_graph_node import CompensatorGraphNode


@dataclass(frozen=True)
class SagaFrame:
    """
    One immutable compensation-stack frame.

    Appended for every regular aspect. Rollback acts only on frames whose
    ``compensator`` is not ``None``; finish events reuse ``state_after`` from the
    same frames instead of maintaining a second aspect-state accumulator.
    """

    compensator: CompensatorGraphNode | None
    aspect_name: str
    state_before: object  # BaseState frozen instance
    state_after: object | None  # BaseState | None frozen instance
