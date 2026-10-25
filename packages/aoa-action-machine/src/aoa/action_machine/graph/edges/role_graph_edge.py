# packages/aoa-action-machine/src/aoa/action_machine/graph/edges/role_graph_edge.py
"""
RoleGraphEdge — ASSOCIATION from Action → Role interchange graph node (@check_roles).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Structural sibling to callable attachments (aspects): ``is_dag=False``, keyed by ``@check_roles``,
:class:`~aoa.action_machine.graph.core.association_graph_edge.AssociationGraphEdge` semantics (association to declared role classes),
materializing ``RoleGraphNode`` only after interchange resolution (targets start as stubs by ``target_node_id``).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    ActionGraphNode  ──@check_roles──►  RoleGraphNode  (wired by coordinator)

One edge per distinct declared role, in declaration order. ``@check_roles`` declares
roles only, so there is no per-role condition to store: the edge carries no runtime
callable and its exported ``properties`` are empty. The object rule, when an
operation has one, is a separate ``AccessDecideGraphEdge`` on the action node.
"""

from __future__ import annotations

from typing import Any

from aoa.action_machine.auth.base_role import BaseRole
from aoa.action_machine.graph.core.association_graph_edge import AssociationGraphEdge
from aoa.action_machine.intents.check_roles.check_roles_intent_resolver import CheckRolesIntentResolver
from aoa.action_machine.system_core.type_introspection import TypeIntrospection


class RoleGraphEdge(AssociationGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed association edge Action host → ``@check_roles`` role class graph node.
    CONTRACT: ``edge_name`` ``@check_roles``; ``target_node_id`` dotted role class path; coordinator wires ``target_node``.
    PROPERTIES: none — a role declaration carries no condition data; exported by :meth:`to_dict` as an empty map.
    INVARIANTS: Frozen via ``AssociationGraphEdge``; ``is_dag`` False.
    AI-CORE-END
    """

    def __init__(self, *, role_cls: type[BaseRole]) -> None:
        super().__init__(
            edge_name="@check_roles",
            is_dag=False,
            target_node_id=TypeIntrospection.full_qualname(role_cls),
            target_node=None,
            properties={},
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
    def get_role_edges(
        action_cls: type[Any],
    ) -> list[RoleGraphEdge]:
        """Return one association stub per distinct declared role, in declaration order."""
        spec = CheckRolesIntentResolver.resolve_check_roles(action_cls)
        roles = spec if isinstance(spec, tuple) else (spec,)
        seen: list[type[BaseRole]] = []
        for role in roles:
            if role not in seen:
                seen.append(role)
        return [RoleGraphEdge(role_cls=role) for role in seen]
