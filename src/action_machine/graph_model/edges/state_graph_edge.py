# src/action_machine/graph_model/edges/state_graph_edge.py
"""
StateGraphEdge — COMPOSITION modelling one directed template transition ``from_state → to_state``.

Standalone edge type using opaque source/target interchange ids (typically matching :class:`~action_machine.graph_model.nodes.state_graph_node.StateGraphNode` rows). Coordinators hydrate ``target_node`` later.

Not registered in package lazy exports in this revision.
"""

from __future__ import annotations

from typing import Any

from graph.base_graph_node import BaseGraphNode
from graph.composition_graph_edge import CompositionGraphEdge


class StateGraphEdge(CompositionGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed composition edge for one allowed lifecycle transition arc.
    CONTRACT: ``edge_name`` ``lifecycle_transition``; ``is_dag`` False; ``properties`` hold ``from_state`` / ``to_state`` (arc semantics; scope is implied by wired ``StateGraphNode`` ids).
    INVARIANTS: Frozen via ``CompositionGraphEdge``; :attr:`edge_relationship` is ``COMPOSITION``.
    AI-CORE-END
    """

    def __init__(
        self,
        *,
        source_node_id: str,
        source_node: BaseGraphNode[Any],
        target_node_id: str,
        from_state: str,
        to_state: str,
        target_node: BaseGraphNode[Any] | None = None,
    ) -> None:
        super().__init__(
            edge_name="lifecycle_transition",
            is_dag=False,
            source_node_id=source_node_id,
            source_node=source_node,
            target_node_id=target_node_id,
            target_node=target_node,
            properties={
                "from_state": from_state,
                "to_state": to_state,
            },
        )
