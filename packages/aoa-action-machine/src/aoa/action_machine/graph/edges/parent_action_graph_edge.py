# packages/aoa-action-machine/src/aoa/action_machine/graph/edges/parent_action_graph_edge.py
"""
ParentActionGraphEdge — GENERALIZATION (``parent_action``) from action class → direct base action.
"""

from __future__ import annotations

from typing import Any

from aoa.action_machine.graph.core.base_graph_edge import BaseGraphEdge
from aoa.action_machine.graph.core.exclude_graph_model import excluded_from_graph_model
from aoa.action_machine.graph.core.generalization_graph_edge import GeneralizationGraphEdge
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.system_core.type_introspection import TypeIntrospection


class ParentActionGraphEdge(GeneralizationGraphEdge):
    """
    Thin generalization edge: ``edge_name`` ``parent_action``, fixed ``GENERALIZATION`` relationship.
    """

    def __init__(
        self,
        *,
        parent_cls: type[BaseAction[Any, Any]],
    ) -> None:
        super().__init__(
            edge_name="parent_action",
            is_dag=False,
            target_node_id=TypeIntrospection.full_qualname(parent_cls),
            target_node=None,
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


def build_parent_action_edges(host_cls: type[BaseAction[Any, Any]]) -> list[BaseGraphEdge]:
    """Emit ``parent_action`` edges for direct :class:`BaseAction` bases (plan §I.5, §I.7.1–2)."""
    out: list[BaseGraphEdge] = []
    for parent in GeneralizationGraphEdge.collect_direct_parents(host_cls, BaseAction):
        if excluded_from_graph_model(parent):
            continue
        out.append(ParentActionGraphEdge(parent_cls=parent))
    return out
