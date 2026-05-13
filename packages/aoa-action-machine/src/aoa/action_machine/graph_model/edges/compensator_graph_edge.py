# packages/aoa-action-machine/src/aoa/action_machine/graph_model/edges/compensator_graph_edge.py
"""
CompensatorGraphEdge — COMPOSITION from Action → Compensator interchange graph node.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Mirror :meth:`~aoa.action_machine.graph_model.edges.compensator_graph_edge.CompensatorGraphEdge.get_compensator_edges`:
composition keyed by compensator node's ``label``, ``is_dag=False``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    ActionGraphNode  ──{compensator_label}──►  CompensatorGraphNode
"""

from __future__ import annotations

from typing import Any

from aoa.action_machine.graph_model.nodes.compensator_graph_node import CompensatorGraphNode
from aoa.action_machine.intents.compensate.compensate_intent_resolver import CompensateIntentResolver
from aoa.graph.composition_graph_edge import CompositionGraphEdge


class CompensatorGraphEdge(CompositionGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed composition edge host Action → compensator graph node.
    CONTRACT: ``edge_name`` equals ``compensator_node.label``; ``target_node`` is the ``CompensatorGraphNode`` instance.
    INVARIANTS: Frozen via ``CompositionGraphEdge``; ``is_dag`` False.
    AI-CORE-END
    """

    def __init__(
        self,
        *,
        compensator_node: CompensatorGraphNode,
    ) -> None:
        super().__init__(
            edge_name="@compensate",
            is_dag=False,
            target_node_id=compensator_node.node_id,
            target_node=compensator_node,
        )

    def to_dict(self, *, source_id: str) -> dict[str, Any]:
        return {
            "source_id": source_id,
            "target_id": self.target_node_id,
            "type": self.edge_name,
            "relationship": self.edge_relationship.archimate_name,
            "is_dag": self.is_dag,
            "properties": {},
        }

    @staticmethod
    def get_compensator_edges(
        action_cls: type[Any],
    ) -> list[CompensatorGraphEdge]:
        """Return compensator composition edges for ``action_cls``."""
        return [
            CompensatorGraphEdge(
                compensator_node=CompensatorGraphNode(compensator_callable, action_cls),
            )
            for compensator_callable in CompensateIntentResolver.resolve_compensators(action_cls)
        ]
