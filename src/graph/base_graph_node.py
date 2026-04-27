# src/graph/base_graph_node.py
"""
BaseGraphNode — generic frozen interchange node.

Constructor takes all interchange fields explicitly: ``node_id``, ``node_type``, ``label``,
``node_obj`` (the host object the node describes, typically a class), and optional ``properties``,
``edges``, and ``companion_nodes`` (each defaults to an empty ``dict`` / ``list`` when omitted or
``None``).

``companion_nodes`` lists **extra** interchange vertices shipped with this host row: nodes that have
no own graph-inspector axis (no ``type`` to walk), e.g. runtime-only rows such as
:class:`~action_machine.model.graph_model.checker_graph_node.CheckerGraphNode`. The host still wires
``edges`` to them by ``target_node_id``; contributors must **also** flatten the same instances into
:meth:`~graph.base_graph_node_inspector.BaseGraphNodeInspector.get_graph_nodes` output so
:class:`~graph.node_graph_coordinator.NodeGraphCoordinator` receives one vertex per id (the
coordinator does not walk ``companion_nodes`` itself).

``node_id``, ``node_type``, ``label``, ``properties``, ``edges``, ``node_obj``, and ``companion_nodes``
are frozen fields on the node (read-only after construction).

String fields must be non-empty (after strip); ``node_obj`` must not be ``None``. Because the node
is frozen, the constructor uses :func:`object.__setattr__`.

Each :class:`~graph.base_graph_edge.BaseGraphEdge` records ``edge_name``, ``is_dag``, **source** and **target**
``*_node_id``, ``*_node_type``, ``*_node_obj``, and ``properties``; concrete edge classes expose their fixed ``edge_relationship``.
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
