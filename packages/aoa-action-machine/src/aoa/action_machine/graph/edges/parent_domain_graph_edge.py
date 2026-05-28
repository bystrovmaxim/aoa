# packages/aoa-action-machine/src/aoa/action_machine/graph/edges/parent_domain_graph_edge.py
"""
ParentDomainGraphEdge — GENERALIZATION (``parent_domain``) from domain class → direct base domain.
"""

from __future__ import annotations

from typing import Any

from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.graph.core.base_graph_edge import BaseGraphEdge
from aoa.action_machine.graph.core.exclude_graph_model import excluded_from_graph_model
from aoa.action_machine.graph.core.generalization_graph_edge import GeneralizationGraphEdge
from aoa.action_machine.system_core.type_introspection import TypeIntrospection


class ParentDomainGraphEdge(GeneralizationGraphEdge):
    """
    Thin generalization edge: ``edge_name`` ``parent_domain``, fixed ``GENERALIZATION`` relationship.
    """

    def __init__(
        self,
        *,
        parent_cls: type[BaseDomain],
    ) -> None:
        super().__init__(
            edge_name="parent_domain",
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


def build_parent_domain_edges(host_cls: type[BaseDomain]) -> list[BaseGraphEdge]:
    """Emit ``parent_domain`` edges for direct :class:`BaseDomain` bases (plan §I.5, §I.7.1–2)."""
    out: list[BaseGraphEdge] = []
    for parent in GeneralizationGraphEdge.collect_direct_parents(host_cls, BaseDomain):
        if excluded_from_graph_model(parent):
            continue
        out.append(ParentDomainGraphEdge(parent_cls=parent))
    return out
