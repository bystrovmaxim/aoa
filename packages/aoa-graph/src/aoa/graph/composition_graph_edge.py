# packages/aoa-graph/src/aoa/graph/composition_graph_edge.py
"""
CompositionGraphEdge — convenience edge with fixed composition relationship.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide a thin ``BaseGraphEdge`` specialization that exposes the fixed
``COMPOSITION`` relationship while preserving the rest of the constructor shape.
"""

from __future__ import annotations

from aoa.graph.base_graph_edge import BaseGraphEdge
from aoa.graph.edge_relationship import COMPOSITION, EdgeRelationship


class CompositionGraphEdge(BaseGraphEdge):
    """Base graph edge with fixed ``COMPOSITION`` relationship."""

    @property
    def edge_relationship(self) -> EdgeRelationship:
        """Return the fixed composition relationship."""
        return COMPOSITION
