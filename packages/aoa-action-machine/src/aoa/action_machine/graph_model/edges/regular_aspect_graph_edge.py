# packages/aoa-action-machine/src/aoa/action_machine/graph_model/edges/regular_aspect_graph_edge.py
"""
RegularAspectGraphEdge — COMPOSITION from Action → RegularAspect interchange graph node.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Mirror :meth:`~aoa.action_machine.graph_model.nodes.action_graph_node.ActionGraphNode.get_regular_aspect`:
composition keyed by the aspect node's ``label``, ``is_dag=False``, materialized target.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    ActionGraphNode  ──{aspect_label}──►  RegularAspectGraphNode
"""

from __future__ import annotations

from typing import Any

from aoa.action_machine.graph_model.nodes.regular_aspect_graph_node import RegularAspectGraphNode
from aoa.action_machine.intents.aspects.regular_aspect_intent_resolver import RegularAspectIntentResolver
from aoa.graph.composition_graph_edge import CompositionGraphEdge


class RegularAspectGraphEdge(CompositionGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed composition edge host Action → regular aspect callable graph node.
    CONTRACT: ``edge_name`` equals ``aspect_node.label``; ``target_node`` is the ``RegularAspectGraphNode`` instance.
    INVARIANTS: Frozen via ``CompositionGraphEdge``; ``is_dag`` False.
    AI-CORE-END
    """

    def __init__(
        self,
        *,
        aspect_node: RegularAspectGraphNode,
    ) -> None:
        super().__init__(
            edge_name="@regular_aspect",
            is_dag=False,
            target_node_id=aspect_node.node_id,
            target_node=aspect_node,
        )

    @staticmethod
    def get_regular_aspect_edges(
        action_cls: type[Any],
    ) -> list[RegularAspectGraphEdge]:
        """Return regular aspect composition edges for ``action_cls``."""
        return [
            RegularAspectGraphEdge(
                aspect_node=RegularAspectGraphNode(aspect_callable, action_cls),
            )
            for aspect_callable in RegularAspectIntentResolver.resolve_regular_aspects(action_cls)
        ]
