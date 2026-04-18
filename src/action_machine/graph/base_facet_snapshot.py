# src/action_machine/graph/base_facet_snapshot.py
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

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``to_facet_vertex()`` is the single required projection contract.
- Snapshot classes are inspector-owned and transport-agnostic.
- Coordinator graph nodes keep skeletal topology; rich typed data remains in snapshot cache.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- This base class does not implement payload validation logic itself.
- Invalid payload shapes surface later in coordinator validation phases.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Abstract typed-snapshot contract for graph facets.
CONTRACT: Require deterministic projection from typed snapshot to ``FacetVertex``.
INVARIANTS: Snapshot type is inspector-defined; projection method is mandatory.
FLOW: inspector builds snapshot -> snapshot projects payload -> coordinator validates/commits graph.
FAILURES: Missing/incorrect projection implementations fail via abstract contract or downstream checks.
EXTENSION POINTS: Any inspector can define nested snapshot types inheriting this base.
AI-CORE-END
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from action_machine.graph.facet_vertex import FacetVertex


class BaseFacetSnapshot(ABC):
    """
    Abstract facet snapshot: single source for graph payload projection.

    Concrete snapshots usually live as nested classes on their inspector, e.g.
    ``RoleIntentInspector.Snapshot``.

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
