# src/action_machine/metadata/base_facet_snapshot.py
"""
BaseFacetSnapshot — typed facet view built by a gate-host inspector.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Each inspector may declare a **nested Snapshot** dataclass (or similar) next to
the gate: rich fields + callables stay here; ``to_facet_payload()`` produces the
serialisable :class:`FacetPayload` stored in the graph.

``GateCoordinator`` caches snapshots during ``build()`` (phase 1) when
``BaseGateHostInspector.facet_snapshot_for_class()`` returns non-``None``.

Inspectors that do not participate yet leave the default hook returning ``None``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from action_machine.metadata.payload import FacetPayload


class BaseFacetSnapshot(ABC):
    """
    Abstract facet snapshot: single source for graph payload projection.

    Concrete snapshots usually live as nested classes on their inspector, e.g.
    ``RoleGateHostInspector.Snapshot``.
    """

    @abstractmethod
    def to_facet_payload(self) -> FacetPayload:
        """Serialise this snapshot into a coordinator ``FacetPayload``."""
        raise NotImplementedError
