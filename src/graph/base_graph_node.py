# src/graph/base_graph_node.py
"""
BaseGraphNode — generic frozen interchange node.

Constructor takes all interchange fields explicitly: ``node_id``, ``node_type``, ``label``,
``properties``, ``edges``, and ``node_obj`` (the host object the node describes, typically
a class).

``node_id``, ``node_type``, ``label``, ``properties``, and ``edges`` are frozen fields on
the node (read-only after construction).

String fields must be non-empty (after strip); ``node_obj`` must not be ``None``; ``properties`` and
``edges`` must not be ``None`` (empty ``dict`` / ``list`` are allowed). Because the node is frozen,
the constructor uses :func:`object.__setattr__`.

Each :class:`~graph.base_graph_edge.BaseGraphEdge` records ``edge_name``, ``is_dag``, **source** and **target**
``*_node_id``, ``*_node_type``, ``*_node_obj``, ``edge_relationship``, and ``properties`` (set by each ``*Node`` when building outgoing edges).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from graph.base_graph_edge import BaseGraphEdge
from graph.validation import require_non_empty_str, require_non_null


@dataclass(init=False, frozen=True)
class BaseGraphNode[T: object]:
    """
    AI-CORE-BEGIN
    ROLE: Frozen interchange node (id, type, label, properties, edges, host object).
    CONTRACT: Non-empty string ids/types/label; non-null ``node_obj``; ``properties`` and ``edges`` never ``None``.
    INVARIANTS: Frozen; ``edges`` is a shallow copy of the passed-in list.
    AI-CORE-END
    """

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
        object.__setattr__(self, "node_id", require_non_empty_str("node_id", node_id))
        object.__setattr__(self, "node_type", require_non_empty_str("node_type", node_type))
        object.__setattr__(self, "label", require_non_empty_str("label", label))

        if properties is None:
            msg = "properties must not be None (use an empty dict if there are no properties)"
            raise ValueError(msg)
        if not isinstance(properties, Mapping):
            msg = f"properties must be a mapping, not {type(properties).__name__}"
            raise TypeError(msg)
        object.__setattr__(self, "properties", dict(properties))

        if edges is None:
            msg = "edges must not be None (use an empty list if there are no edges)"
            raise ValueError(msg)
        if not isinstance(edges, list):
            msg = f"edges must be a list, not {type(edges).__name__}"
            raise TypeError(msg)
        object.__setattr__(self, "edges", list(edges))

        object.__setattr__(self, "node_obj", require_non_null("node_obj", node_obj))
