# src/action_machine/graph_model/edges/state_graph_edge.py
"""
StateGraphEdge — COMPOSITION modelling one directed template transition ``from_state → to_state``.

Standalone edge type using opaque source/target interchange ids (typically matching :class:`~action_machine.graph_model.nodes.state_graph_node.StateGraphNode` rows). Coordinators hydrate ``target_node`` later.

Not registered in package lazy exports in this revision.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from graph.base_graph_node import BaseGraphNode
from graph.composition_graph_edge import CompositionGraphEdge

if TYPE_CHECKING:
    from action_machine.graph_model.nodes.state_graph_node import StateGraphNode


class StateGraphEdge(CompositionGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed composition edge for one allowed lifecycle transition arc; :meth:`get_lifecycle_transition_edges` materializes template arcs from a state vertex.
    CONTRACT: ``edge_name`` ``lifecycle_transition``; ``is_dag`` False; ``properties`` hold ``from_state`` / ``to_state`` (arc semantics; scope is implied by wired ``StateGraphNode`` ids).
    INVARIANTS: Frozen via ``CompositionGraphEdge``; :attr:`edge_relationship` is ``COMPOSITION``.
    AI-CORE-END
    """

    def __init__(
        self,
        *,
        target_node_id: str,
        from_state: str,
        to_state: str,
        target_node: BaseGraphNode[Any] | None = None,
    ) -> None:
        super().__init__(
            edge_name="lifecycle_transition",
            is_dag=False,
            target_node_id=target_node_id,
            target_node=target_node,
            properties={
                "from_state": from_state,
                "to_state": to_state,
            },
        )

    @staticmethod
    def get_lifecycle_transition_edges(vertex: StateGraphNode) -> list[StateGraphEdge]:
        """One edge per outbound template arc from ``vertex`` when a frozen template defines that state."""

        tpl = vertex.node_obj.lifecycle_class._get_template()
        if tpl is None:
            return []

        nid_root = vertex.node_obj.lifecycle_graph_node_id
        state_info = tpl.get_states().get(vertex.node_obj.state_key)
        if state_info is None:
            return []

        return [
            StateGraphEdge(
                target_node_id=f"{nid_root}:{to_key}",
                from_state=vertex.node_obj.state_key,
                to_state=to_key,
                target_node=None,
            )
            for to_key in state_info.transitions
        ]
