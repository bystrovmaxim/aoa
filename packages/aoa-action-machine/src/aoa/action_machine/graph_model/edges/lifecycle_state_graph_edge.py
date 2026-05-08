# packages/aoa-action-machine/src/aoa/action_machine/graph_model/edges/lifecycle_state_graph_edge.py
"""
LifeCycleStateGraphEdge — COMPOSITION from a lifecycle row to one state row.

Keeps every :class:`~aoa.action_machine.graph_model.nodes.state_graph_node.StateGraphNode`
visibly attached to its parent :class:`~aoa.action_machine.graph_model.nodes.lifecycle_graph_node.LifeCycleGraphNode`,
including initial states that have no incoming ``lifecycle_transition``.
"""

from __future__ import annotations

from typing import TypeVar

from aoa.action_machine.domain.lifecycle import Lifecycle
from aoa.action_machine.graph_model.nodes.state_graph_node import StateGraphNode
from aoa.graph.composition_graph_edge import CompositionGraphEdge

TLifecycle = TypeVar("TLifecycle", bound=Lifecycle)


class LifeCycleStateGraphEdge(CompositionGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed composition edge from a lifecycle interchange row to one state interchange row; :meth:`get_state_edges` builds sorted state interchange rows from a template.
    CONTRACT: ``edge_name`` ``lifecycle_contains_state``; ``is_dag`` False; target is a wired :class:`~aoa.action_machine.graph_model.nodes.state_graph_node.StateGraphNode`.
    INVARIANTS: Frozen via ``CompositionGraphEdge``.
    AI-CORE-END
    """

    def __init__(self, state_node: StateGraphNode) -> None:
        super().__init__(
            edge_name="lifecycle_contains_state",
            is_dag=False,
            target_node_id=state_node.node_id,
            target_node=state_node,
            properties={
                "state_key": state_node.node_obj.state_key,
            },
        )

    @staticmethod
    def get_state_edges(
        lifecycle_cls: type[TLifecycle],
        lifecycle_node_id: str,
    ) -> list[StateGraphNode]:
        """Sorted state interchange rows derived from ``lifecycle_cls``'s frozen template."""

        tpl = lifecycle_cls._get_template()
        if tpl is None:
            return []

        keys: set[str] = set()
        for from_key, state_info in tpl.get_states().items():
            keys.add(from_key)
            keys.update(state_info.transitions)
        sorted_keys = sorted(keys)
        return [StateGraphNode(lifecycle_cls, sk, lifecycle_node_id) for sk in sorted_keys]
