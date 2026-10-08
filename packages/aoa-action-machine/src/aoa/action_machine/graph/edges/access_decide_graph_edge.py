# packages/aoa-action-machine/src/aoa/action_machine/graph/edges/access_decide_graph_edge.py
"""
AccessDecideGraphEdge — COMPOSITION from Action → AccessDecide interchange graph node.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The edge that puts an operation's declared object check into the graph. There is
at most one such edge per operation, because there is at most one declaration:
:meth:`~aoa.action_machine.graph.edges.access_decide_graph_edge.AccessDecideGraphEdge.get_access_decide_edges`
asks the intent resolver, which returns nothing when the operation declares no
check and refuses to choose when it declares two.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    ActionGraphNode  ──@access_decide──▶  AccessDecideGraphNode

    ActionGraphNode.__init__ ──▶ get_access_decide_edges(action_cls)
        ├── nothing declared ──▶ []           (the operation has no object check)
        └── declared         ──▶ [one edge]
"""

from __future__ import annotations

from typing import Any

from aoa.action_machine.graph.core.composition_graph_edge import CompositionGraphEdge
from aoa.action_machine.graph.nodes.access_decide_graph_node import AccessDecideGraphNode
from aoa.action_machine.intents.access_decide.access_decide_intent_resolver import AccessDecideIntentResolver


class AccessDecideGraphEdge(CompositionGraphEdge):
    """
    AI-CORE-BEGIN
        ROLE: Typed composition edge host Action → the operation's declared object check.
        CONTRACT: ``edge_name`` is ``@access_decide``; ``target_node`` is the ``AccessDecideGraphNode`` instance; :meth:`get_access_decide_edges` returns zero or one edge from the declaration.
        INVARIANTS: Frozen via ``CompositionGraphEdge``; ``is_dag`` False.
    AI-CORE-END
    """

    def __init__(
        self,
        *,
        access_decide_node: AccessDecideGraphNode,
    ) -> None:
        super().__init__(
            edge_name="@access_decide",
            is_dag=False,
            target_node_id=access_decide_node.node_id,
            target_node=access_decide_node,
        )

    def to_dict(self, *, source_id: str) -> dict[str, Any]:
        """Return the JSON-safe edge from ``source_id`` to the declared check."""
        return {
            "source_id": source_id,
            "target_id": self.target_node_id,
            "type": self.edge_name,
            "relationship": self.edge_relationship.archimate_name,
            "is_dag": self.is_dag,
            "properties": {},
        }

    @staticmethod
    def get_access_decide_edges(action_cls: type[Any]) -> list[AccessDecideGraphEdge]:
        """Return the operation's object-check composition edge, or nothing when it declares none."""
        declared = AccessDecideIntentResolver.resolve_check(action_cls)
        if declared is None:
            return []
        return [AccessDecideGraphEdge(access_decide_node=AccessDecideGraphNode(declared, action_cls))]
