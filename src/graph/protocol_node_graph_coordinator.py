# src/graph/protocol_node_graph_coordinator.py
"""
Protocol for node-graph runtime metadata reads.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Define the smallest coordinator-facing contract that callers can depend on
while the graph migration moves runtime reads onto ``NodeGraphCoordinator``.
"""

from __future__ import annotations

from typing import Protocol

from action_machine.model.graph_model.regular_aspect_graph_node import (
    RegularAspectGraphNode,
)
from graph.base_graph_node import BaseGraphNode


class ProtocolNodeGraphCoordinator(Protocol):
    """Protocol for incremental node-graph runtime capabilities."""

    def get_node_by_id(
        self,
        node_id: str,
        node_type: str | None = None,
    ) -> BaseGraphNode[object]:
        """Return the graph node identified by ``node_id``."""

    def get_regular_aspect_nodes(
        self,
        action_cls: type,
    ) -> list[RegularAspectGraphNode]:
        """Return regular-aspect nodes linked from ``action_cls`` in the node graph."""
