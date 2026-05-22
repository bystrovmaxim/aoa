# packages/aoa-action-machine/src/aoa/action_machine/graph/edges/parent_role_graph_edge.py
"""
ParentRoleGraphEdge — GENERALIZATION (``parent_role``) from role class → direct base role.
"""

from __future__ import annotations

from typing import Any

from aoa.action_machine.auth.base_role import BaseRole
from aoa.action_machine.graph.core.base_graph_edge import BaseGraphEdge
from aoa.action_machine.graph.core.exclude_graph_model import excluded_from_graph_model
from aoa.action_machine.graph.core.generalization_graph_edge import GeneralizationGraphEdge
from aoa.action_machine.system_core.type_introspection import TypeIntrospection


class ParentRoleGraphEdge(GeneralizationGraphEdge):
    """Thin generalization edge: ``edge_name`` ``parent_role``, fixed ``GENERALIZATION`` relationship."""

    def __init__(
        self,
        *,
        parent_cls: type[BaseRole],
    ) -> None:
        super().__init__(
            edge_name="parent_role",
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


def build_parent_role_edges(host_cls: type[BaseRole]) -> list[BaseGraphEdge]:
    """Emit ``parent_role`` edges for direct :class:`BaseRole` bases (plan §I.5, §I.7.1–2)."""
    out: list[BaseGraphEdge] = []
    for parent in GeneralizationGraphEdge.collect_direct_parents(host_cls, BaseRole):
        if excluded_from_graph_model(parent):
            continue
        out.append(ParentRoleGraphEdge(parent_cls=parent))
    return out
