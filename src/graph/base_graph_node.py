# src/graph/base_graph_node.py
"""
BaseGraphNode — generic frozen interchange node.

Constructor takes all interchange fields explicitly: ``node_id``, ``node_type``, ``label``,
``properties``, ``edges``, and ``node_obj`` (the host object the node describes, typically
a class).

``node_id``, ``node_type``, ``label``, ``properties``, and ``edges`` are frozen fields on
the node (read-only after construction).

Because the node is frozen, the constructor uses :func:`object.__setattr__`.

Each :class:`~graph.base_graph_edge.BaseGraphEdge` records ``edge_name``, ``is_dag``, **source** and **target**
``*_node_id``, ``*_node_type``, and ``*_node_obj`` (set by each ``*Node`` when building outgoing edges).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from graph.base_graph_edge import BaseGraphEdge


@dataclass(init=False, frozen=True)
class BaseGraphNode[T: object]:
    node_id: str
    node_type: str
    label: str
    properties: dict[str, Any]
    edges: list[BaseGraphEdge]
    node_obj: T

    def __init__(
        self,
        *,
        node_id: str,
        node_type: str,
        label: str,
        properties: dict[str, Any],
        edges: list[BaseGraphEdge],
        node_obj: T,
    ) -> None:
        object.__setattr__(self, "node_id", node_id)
        object.__setattr__(self, "node_type", node_type)
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "properties", properties)
        object.__setattr__(self, "edges", edges)
        object.__setattr__(self, "node_obj", node_obj)
