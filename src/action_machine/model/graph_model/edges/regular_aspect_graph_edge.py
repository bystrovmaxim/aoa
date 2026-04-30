# src/action_machine/model/graph_model/edges/regular_aspect_graph_edge.py
"""
RegularAspectGraphEdge — COMPOSITION from Action → RegularAspect interchange vertex.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Mirror :meth:`~action_machine.model.graph_model.action_graph_node.ActionGraphNode.get_regular_aspect_edges`:
composition keyed by the aspect node's ``label``, ``is_dag=False``, materialized target.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    ActionGraphNode  ──{aspect_label}──►  RegularAspectGraphNode
"""

from __future__ import annotations

from typing import Any

from action_machine.model.graph_model.regular_aspect_graph_node import RegularAspectGraphNode
from graph.base_graph_node import BaseGraphNode
from graph.composition_graph_edge import CompositionGraphEdge


class RegularAspectGraphEdge(CompositionGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed composition edge host Action → regular aspect callable vertex.
    CONTRACT: ``edge_name`` equals ``aspect_node.label``; ``target_node`` is the ``RegularAspectGraphNode`` instance.
    INVARIANTS: Frozen via ``CompositionGraphEdge``; ``is_dag`` False.
    AI-CORE-END
    """

    def __init__(
        self,
        *,
        source_node: BaseGraphNode[Any],
        aspect_node: RegularAspectGraphNode,
    ) -> None:
        super().__init__(
            edge_name=aspect_node.label,
            is_dag=False,
            source_node_id=source_node.node_id,
            source_node_type=source_node.node_type,
            source_node=source_node,
            target_node_id=aspect_node.node_id,
            target_node_type=aspect_node.node_type,
            target_node=aspect_node,
        )
