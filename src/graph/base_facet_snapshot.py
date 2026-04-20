# src/graph/base_facet_snapshot.py
"""
BaseFacetSnapshot — typed facet view built by an intent inspector.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Each inspector may declare a **nested Snapshot** dataclass (or similar) next to
the facet: rich fields + callables stay here; ``to_facet_vertex()`` produces the
serialisable :class:`FacetVertex` used for validation; the coordinator keeps
typed snapshots separately and commits only ``node_type`` / ``name`` /
``class_ref`` on graph nodes.

``GraphCoordinator`` caches snapshots during ``build()`` (phase 1) when
``BaseIntentInspector.facet_snapshot_for_class()`` returns non-``None``.

Inspectors that do not participate yet leave the default hook returning ``None``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    inspector-specific typed Snapshot
              │
              ▼
    to_facet_vertex()
              │
              ▼
    FacetVertex (validation/projection format)
              │
              ├─ cached as typed snapshot in coordinator
              └─ consumed for graph build validation/commit
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from graph.facet_vertex import FacetVertex


class BaseFacetSnapshot(ABC):
    """
AI-CORE-BEGIN
    ROLE: Base ABC for typed facet snapshot implementations.
    CONTRACT: Implement ``to_facet_vertex``.
    INVARIANTS: Projection should be side-effect free and return a valid payload object.
    AI-CORE-END
"""

    @abstractmethod
    def to_facet_vertex(self) -> FacetVertex:
        """Serialise this snapshot into a coordinator ``FacetVertex``."""
        raise NotImplementedError
