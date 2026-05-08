# packages/aoa-graph/src/aoa/graph/graph_edge.py
"""
Frozen interchange edge for the coordinator graph (spec graph.md §10).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GraphEdge:
    """One directed coordinator graph edge (interchange shape)."""

    source_id: str
    target_id: str
    edge_type: str
    stereotype: str
    category: str
    is_dag: bool
    properties: dict[str, Any]
