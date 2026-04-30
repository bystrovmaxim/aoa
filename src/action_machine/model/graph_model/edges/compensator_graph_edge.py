# src/action_machine/model/graph_model/edges/compensator_graph_edge.py
"""
CompensatorGraphEdge — COMPOSITION from Action → Compensator interchange vertex.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Mirror :meth:`~action_machine.model.graph_model.action_graph_node.ActionGraphNode.get_compensator_edges`:
composition keyed by compensator node's ``label``, ``is_dag=False``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    ActionGraphNode  ──{compensator_label}──►  CompensatorGraphNode
"""

from __future__ import annotations

from typing import Any

from action_machine.intents.compensate.compensate_intent_resolver import (
    CompensateIntentResolver,
)
from action_machine.model.base_action import BaseAction
from action_machine.model.graph_model.compensator_graph_node import CompensatorGraphNode
from graph.base_graph_node import BaseGraphNode
from graph.composition_graph_edge import CompositionGraphEdge


class CompensatorGraphEdge(CompositionGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed composition edge host Action → compensator vertex.
    CONTRACT: ``edge_name`` equals ``compensator_node.label``; ``target_node`` is the ``CompensatorGraphNode`` instance.
    INVARIANTS: Frozen via ``CompositionGraphEdge``; ``is_dag`` False.
    AI-CORE-END
    """

    def __init__(
        self,
        *,
        source_node: BaseGraphNode[Any],
        compensator_node: CompensatorGraphNode,
    ) -> None:
        super().__init__(
            edge_name=compensator_node.label,
            is_dag=False,
            source_node_id=source_node.node_id,
            source_node_type=source_node.node_type,
            source_node=source_node,
            target_node_id=compensator_node.node_id,
            target_node_type=compensator_node.node_type,
            target_node=compensator_node,
        )

    @staticmethod
    def edges_from_compensators(
        source_node: BaseGraphNode[Any],
        action_cls: type[BaseAction[Any, Any]],
    ) -> list[CompensatorGraphEdge]:
        """Return compensator composition edges for ``action_cls``."""
        return [
            CompensatorGraphEdge(
                source_node=source_node,
                compensator_node=CompensatorGraphNode(compensator_callable, action_cls),
            )
            for compensator_callable in CompensateIntentResolver.resolve_compensators(action_cls)
        ]
