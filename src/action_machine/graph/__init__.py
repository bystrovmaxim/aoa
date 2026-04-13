# src/action_machine/graph/__init__.py
"""
ActionMachine **graph** subpackage (facet snapshots, coordinator, inspectors).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

1. **Facet snapshots** — typed immutable snapshots per inspector.
   Roles, @meta, aspects/checkers, subscriptions, sensitive fields,
   error handlers and compensators live on facet snapshots
   (``get_role`` / ``get_meta``).

2. **GateCoordinator** — registry of ``BaseIntentInspector`` classes plus a
   transactional **facet graph** (``rx.PyDiGraph``): ``FacetPayload`` nodes,
   edges, key-uniqueness rules, structural acyclicity, and stub materialization
   for edge targets (including domain classes).

Public imports: ``BaseFacetSnapshot``, ``GateCoordinator``.
"""

from __future__ import annotations

from action_machine.graph.base_facet_snapshot import BaseFacetSnapshot
from action_machine.graph.gate_coordinator import GateCoordinator

__all__ = [
    "BaseFacetSnapshot",
    "GateCoordinator",
]
