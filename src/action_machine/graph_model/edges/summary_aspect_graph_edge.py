# src/action_machine/graph_model/edges/summary_aspect_graph_edge.py
"""
SummaryAspectGraphEdge — COMPOSITION from Action → SummaryAspect interchange vertex.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Mirror :meth:`~action_machine.graph_model.nodes.action_graph_node.ActionGraphNode.get_summary_aspect_graph_node`
construction: composition keyed by summary node's ``label``, ``is_dag=False``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    ActionGraphNode  ──{summary_label}──►  SummaryAspectGraphNode
"""

from __future__ import annotations

from typing import Any

from action_machine.graph_model.nodes.summary_aspect_graph_node import SummaryAspectGraphNode
from action_machine.intents.aspects.summary_aspect_intent_resolver import (
    SummaryAspectIntentResolver,
)
from action_machine.model.base_action import BaseAction
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
            edge_name="@summary_aspect",
            is_dag=False,
            source=source_node,
            target_node_id=summary_node.node_id,
            target_node=summary_node,
        )

    @staticmethod
    def get_summary_aspect_edges(
        source_node: BaseGraphNode[Any],
        action_cls: type[BaseAction[Any, Any]],
    ) -> list[SummaryAspectGraphEdge]:
        """Return summary aspect composition edges for ``action_cls``."""
        return [
            SummaryAspectGraphEdge(
                source_node=source_node,
                summary_node=SummaryAspectGraphNode(aspect_callable, action_cls),
            )
            for aspect_callable in SummaryAspectIntentResolver.resolve_summary_aspects(action_cls)
        ]
