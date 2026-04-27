"""
AssociationGraphEdge — convenience edge with fixed association relationship.

Provide a thin ``BaseGraphEdge`` specialization that exposes the fixed
``ASSOCIATION`` relationship while preserving the rest of the constructor shape.
"""

from __future__ import annotations

from graph.base_graph_edge import BaseGraphEdge
from graph.edge_relationship import ASSOCIATION, EdgeRelationship


class AssociationGraphEdge(BaseGraphEdge):
    """Base graph edge with fixed ``ASSOCIATION`` relationship."""

    @property
    def edge_relationship(self) -> EdgeRelationship:
        """Return the fixed association relationship."""
        return ASSOCIATION
