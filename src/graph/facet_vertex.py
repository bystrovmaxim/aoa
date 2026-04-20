# src/graph/facet_vertex.py
"""
Facet-layer node + outgoing edges (:class:`FacetVertex`), collected before interchange.

Pairs with :class:`~graph.graph_vertex.GraphVertex` after commit.
Outgoing edges use :class:`~graph.facet_edge.FacetEdge`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from graph.facet_edge import FacetEdge


@dataclass(frozen=True)
class FacetVertex:
    """
AI-CORE-BEGIN
    ROLE: Immutable node+edges transport envelope.
    CONTRACT: Represent one facet node emitted by an inspector for coordinator build phases.
    INVARIANTS: Node identity is ``node_type`` + ``node_name``; edges are attached as immutable tuples.
    AI-CORE-END
"""

    node_type: str
    node_name: str
    node_class: type
    node_meta: tuple[tuple[str, Any], ...] = field(default_factory=tuple)
    edges: tuple[FacetEdge, ...] = field(default_factory=tuple)
    merge_group_key: str | None = None
    merge_node_type: str | None = None
    merge_node_name: str | None = None
    skip_node_type_snapshot_fallback: bool = False
