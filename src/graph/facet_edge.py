# src/graph/facet_edge.py
"""
Facet-layer directed edge (:class:`FacetEdge`), collected before interchange projection.

Pairs with :class:`~graph.graph_edge.GraphEdge` after commit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Hashable facet ``node_meta`` row: string keys, opaque values (see inspector hydrators).
FacetMetaRow = tuple[tuple[str, Any], ...]


@dataclass(frozen=True)
class FacetEdge:
    """
AI-CORE-BEGIN
    ROLE: Immutable edge transport row.
    CONTRACT: Describe one outgoing graph edge with target identity and structural semantics.
    INVARIANTS: Structural flag drives cycle checks; metadata remains tuple-encoded until commit.
    AI-CORE-END
"""

    target_node_type: str
    target_name: str
    edge_type: str
    is_structural: bool
    edge_meta: tuple[tuple[str, Any], ...] = field(default_factory=tuple)
    target_class_ref: type | None = None
    synthetic_stub_edges: tuple[FacetEdge, ...] = field(default_factory=tuple)
