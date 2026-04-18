# src/action_machine/graph/model.py
"""
Frozen vertex/edge transport types for the coordinator graph (spec graph.md §10).

Interchange lists are built from facet payloads or from a small synthetic JSON bundle;
they are independent of ``rustworkx`` until commit into ``GraphCoordinator._graph``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GraphVertex:
    """One coordinator graph vertex (interchange shape)."""

    id: str
    vertex_type: str
    stereotype: str
    display_name: str
    class_ref: type | None
    properties: dict[str, Any]


@dataclass(frozen=True)
class GraphEdge:
    """One directed coordinator graph edge (interchange shape)."""

    source_id: str
    target_id: str
    edge_type: str
    stereotype: str
    category: str
    is_dag: bool
    attributes: dict[str, Any]
