# src/action_machine/graph/reverse_edge.py
"""
Build the **reverse** :class:`~action_machine.graph.graph_edge.GraphEdge` for a §5.3 **direct** edge
(``graph.md`` v4.1 §11.4).

Used by :mod:`action_machine.graph.graph_builder` (§5.3 reversals), tests, and fixtures so reverse
edge typing stays aligned with ``REVERSE_EDGE_MAP``.
"""

from __future__ import annotations

from typing import Any

from action_machine.graph.constants import REVERSE_EDGE_MAP, REVERSE_EDGE_STEREOTYPE
from action_machine.graph.graph_edge import GraphEdge


def reverse_direct_edge(edge: GraphEdge) -> GraphEdge | None:
    """
    Return the paired reverse edge, or ``None`` if ``edge`` is not a direct §5.3 forward edge.
    """
    if edge.category != "direct":
        return None
    reverse_type = REVERSE_EDGE_MAP.get(edge.edge_type)
    if reverse_type is None:
        return None
    rev_st = REVERSE_EDGE_STEREOTYPE.get(edge.edge_type)
    if rev_st is None:
        msg = f"missing REVERSE_EDGE_STEREOTYPE for forward edge type {edge.edge_type!r}"
        raise RuntimeError(msg)
    props: dict[str, Any] = dict(edge.properties) if edge.properties else {}
    return GraphEdge(
        source_id=edge.target_id,
        target_id=edge.source_id,
        edge_type=reverse_type,
        stereotype=rev_st,
        category="reverse",
        is_dag=False,
        properties=props,
    )
