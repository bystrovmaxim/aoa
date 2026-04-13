# src/action_machine/graph/__init__.py
"""
ActionMachine **graph** subpackage (facet snapshots, coordinator, inspectors).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide the shared graph-modeling surface for ActionMachine metadata:
typed facet snapshots and transactional graph assembly via ``GateCoordinator``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    decorators write class/method scratch
              │
              ▼
    inspectors read declarations -> FacetPayload + optional Snapshot
              │
              ▼
    GateCoordinator.build()
      (collect -> validate -> commit)
              │
              ▼
    graph topology + typed snapshot cache

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``GateCoordinator`` is the single graph assembly and validation entry point.
- Snapshot storage keys are inspector-defined but coordinator-managed.
- Read APIs require an explicitly built coordinator instance.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- This package root exports contracts; concrete behavior lives in submodules.
- Graph integrity failures surface during coordinator build phases.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Public namespace for graph core contracts.
CONTRACT: Export ``BaseFacetSnapshot`` and ``GateCoordinator`` as graph-layer API.
INVARIANTS: Inspectors populate payloads/snapshots; coordinator owns transactional build semantics.
FLOW: declaration scratch -> inspector extraction -> coordinator validation/commit -> graph read APIs.
FAILURES: Build/read lifecycle errors and graph validation exceptions are raised by coordinator internals.
EXTENSION POINTS: Add inspector modules and snapshot types without changing package root API.
AI-CORE-END
"""

from __future__ import annotations

from action_machine.graph.base_facet_snapshot import BaseFacetSnapshot
from action_machine.graph.gate_coordinator import GateCoordinator

__all__ = [
    "BaseFacetSnapshot",
    "GateCoordinator",
]
