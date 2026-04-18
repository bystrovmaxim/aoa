# src/action_machine/graph/graph_vertex.py
"""
Frozen interchange vertex for the coordinator graph (spec graph.md §10).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GraphVertex:
    """One coordinator graph vertex (interchange shape)."""

    id: str
    node_type: str
    label: str
    class_ref: type | None
    properties: dict[str, Any]
