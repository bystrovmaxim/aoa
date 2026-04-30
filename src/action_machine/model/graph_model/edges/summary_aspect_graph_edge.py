# src/action_machine/model/graph_model/edges/summary_aspect_graph_edge.py
"""
SummaryAspectGraphEdge — COMPOSITION from Action → SummaryAspect interchange vertex.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Mirror :meth:`~action_machine.model.graph_model.action_graph_node.ActionGraphNode.get_summary_aspect_edges`
construction: composition keyed by summary node's ``label``, ``is_dag=False``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    ActionGraphNode  ──{summary_label}──►  SummaryAspectGraphNode
"""

from __future__ import annotations

from typing import Any

from action_machine.model.graph_model.summary_aspect_graph_node import SummaryAspectGraphNode
from graph.base_graph_node import BaseGraphNode
from graph.composition_graph_edge import CompositionGraphEdge


class SummaryAspectGraphEdge(CompositionGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed composition edge host Action → summary aspect vertex.
    CONTRACT: ``edge_name`` equals ``summary_node.label``; ``target_node`` is the ``SummaryAspectGraphNode`` instance.
    INVARIANTS: Frozen via ``CompositionGraphEdge``; ``is_dag`` False.
    AI-CORE-END
    """

    def __init__(
        self,
        *,
        source_node: BaseGraphNode[Any],
        summary_node: SummaryAspectGraphNode,
    ) -> None:
        super().__init__(
            edge_name=summary_node.label,
            is_dag=False,
            source_node_id=source_node.node_id,
            source_node_type=source_node.node_type,
            source_node=source_node,
            target_node_id=summary_node.node_id,
            target_node_type=summary_node.node_type,
            target_node=summary_node,
        )
