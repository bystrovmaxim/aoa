# src/action_machine/metadata/__init__.py
"""
ActionMachine **metadata and graph** subpackage.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

1. **Facet snapshots** — typed immutable snapshots per inspector.
   Roles, @meta, aspects/checkers, subscriptions, sensitive fields,
   error handlers and compensators live on facet snapshots
   (``get_role`` / ``get_meta``).

2. **GateCoordinator** — registry of ``BaseGateHostInspector`` classes plus a
   transactional **facet graph** (``rx.PyDiGraph``): ``FacetPayload`` nodes,
   edges, key-uniqueness rules, structural acyclicity, and stub materialization
   for edge targets (including domain classes).

Public imports: ``BaseFacetSnapshot``, ``GateCoordinator``.

═══════════════════════════════════════════════════════════════════════════════
RELATION TO ``action_machine.core``
═══════════════════════════════════════════════════════════════════════════════

``GateCoordinator`` is also re-exported from ``action_machine.core.gate_coordinator``.
"""

from __future__ import annotations

from .base_facet_snapshot import BaseFacetSnapshot
from .gate_coordinator import GateCoordinator

__all__ = [
    "BaseFacetSnapshot",
    "GateCoordinator",
]
