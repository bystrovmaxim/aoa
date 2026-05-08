# packages/aoa-graph/src/aoa/graph/aggregation_graph_edge.py
"""
AggregationGraphEdge — convenience edge with fixed aggregation relationship.

Provide a thin ``BaseGraphEdge`` specialization that exposes the fixed
``AGGREGATION`` relationship while preserving the rest of the constructor shape.
"""

from __future__ import annotations

from aoa.graph.base_graph_edge import BaseGraphEdge
from aoa.graph.edge_relationship import AGGREGATION, EdgeRelationship


class AggregationGraphEdge(BaseGraphEdge):
    """Base graph edge with fixed ``AGGREGATION`` relationship."""

    @property
    def edge_relationship(self) -> EdgeRelationship:
        """Return the fixed aggregation relationship."""
        return AGGREGATION
