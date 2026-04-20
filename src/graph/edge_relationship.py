# src/graph/edge_relationship.py
"""
ArchiMate-style **relationship** kinds for interchange edges.

Values follow the ArchiMate 3 relationship layer naming (string values match common spellings).
UML-style **Generalization** is included alongside ArchiMate **Specialization** for interchange sources that use either label.
Extend this enum when new connector semantics appear in the interchange graph.
"""

from __future__ import annotations

from enum import StrEnum


class EdgeRelationship(StrEnum):
    """ArchiMate-style relationship kind carried by a :class:`~graph.base_graph_edge.BaseGraphEdge`."""

    ASSOCIATION = "Association"
    AGGREGATION = "Aggregation"
    ASSIGNMENT = "Assignment"
    COMPOSITION = "Composition"
    FLOW = "Flow"
    GENERALIZATION = "Generalization"
    INFLUENCE = "Influence"
    REALIZATION = "Realization"
    SERVING = "Serving"
    SPECIALIZATION = "Specialization"
    TRIGGERING = "Triggering"
    ACCESS = "Access"
