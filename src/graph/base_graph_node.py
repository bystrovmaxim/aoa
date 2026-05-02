# src/graph/base_graph_node.py
"""
BaseGraphNode — generic frozen interchange node.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Frozen interchange row built from explicit ``node_id``, ``node_type``, ``label``,
non-null ``node_obj``, and normalized ``properties`` (subclasses add ``edges`` /
``companion_nodes``). Optional **companion** vertices bundle child interchange rows that
have no inspector axis—e.g. checker nodes—into the owning host row; coordinators expand
companions recursively with the same duplicate-id discipline as outbound edges.

Nonempty stripped strings everywhere required; assigns use :func:`object.__setattr__`
because instances are immutable.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from graph.base_graph_edge import BaseGraphEdge
from graph.validation import require_non_empty_str, require_non_null


@dataclass(init=False, frozen=True)
class BaseGraphNode[T: object](ABC):
    """
    AI-CORE-BEGIN
    ROLE: Frozen interchange node (id, type, label, properties, edges, host object, optional companions).
    CONTRACT: Non-empty string ids/types/label; non-null ``node_obj``; ``properties`` / ``edges`` /
    ``companion_nodes`` optional (empty when omitted or ``None``). Use ``companion_nodes`` for child
    vertices without a dedicated inspector (see module docstring).
    INVARIANTS: Frozen; ``properties`` is ``dict(...)`` of the argument; ``edges`` and ``companion_nodes``
    are ``list(...)`` copies when provided.
    AI-CORE-END
    """

    node_id: str
    node_type: str
    label: str
    properties: dict[str, Any]
    node_obj: T

    @abstractmethod
    def __init__(
        self,
        *,
        node_id: str,
        node_type: str,
        label: str,
        node_obj: T,
        properties: dict[str, Any] | None = None,
    ) -> None:
        properties = {} if properties is None else dict(properties)

        object.__setattr__(self, "node_id", require_non_empty_str("node_id", node_id))
        object.__setattr__(self, "node_type", require_non_empty_str("node_type", node_type))
        object.__setattr__(self, "label", require_non_empty_str("label", label))
        object.__setattr__(self, "node_obj", require_non_null("node_obj", node_obj))
        object.__setattr__(self, "properties", properties)

    def get_all_edges(self) -> list[BaseGraphEdge]:
        """Return outgoing graph edges exposed by this node."""
        return []

    def get_companion_nodes(self) -> list[BaseGraphNode[Any]]:
        """Return additional graph nodes that must be included with this node."""
        return []
