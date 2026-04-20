# src/graph/edge_relationship.py
"""
ArchiMate-style **relationship** kinds for interchange edge endpoints.

Values follow the ArchiMate 3 relationship layer naming (string values match common spellings).
Extend this enum when new connector semantics appear in the interchange graph.
"""

from __future__ import annotations

from enum import StrEnum


class EdgeRelationship(StrEnum):
    """Relationship kind at one end of a :class:`~graph.base_graph_edge.BaseGraphEdge`."""

    ASSOCIATION = "Association"
    AGGREGATION = "Aggregation"
    ASSIGNMENT = "Assignment"
    COMPOSITION = "Composition"
    FLOW = "Flow"
    INFLUENCE = "Influence"
    REALIZATION = "Realization"
    SERVING = "Serving"
    SPECIALIZATION = "Specialization"
    TRIGGERING = "Triggering"
    ACCESS = "Access"
