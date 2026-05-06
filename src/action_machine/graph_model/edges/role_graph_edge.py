# src/action_machine/graph_model/edges/role_graph_edge.py
"""
RoleGraphEdge — ASSOCIATION from Action → Role interchange vertex (@check_roles).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Structural sibling to callable attachments (aspects): ``is_dag=False``, keyed by ``@check_roles``,
:class:`~graph.association_graph_edge.AssociationGraphEdge` semantics (association to declared role classes),
materializing ``RoleGraphNode`` only after interchange resolution (targets start as stubs by ``target_node_id``).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    ActionGraphNode  ──@check_roles──►  RoleGraphNode  (wired by coordinator)
"""

from __future__ import annotations

from typing import Any

from action_machine.auth.base_role import BaseRole
from action_machine.intents.check_roles.check_roles_intent_resolver import CheckRolesIntentResolver
from action_machine.system_core.type_introspection import TypeIntrospection
from graph.association_graph_edge import AssociationGraphEdge


class RoleGraphEdge(AssociationGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed association edge Action host → ``@check_roles`` role class vertex.
    CONTRACT: ``edge_name`` ``@check_roles``; ``target_node_id`` dotted role class path; coordinator wires ``target_node``.
    INVARIANTS: Frozen via ``AssociationGraphEdge``; ``is_dag`` False.
    AI-CORE-END
    """

    def __init__(
        self,
        *,
        role_cls: type[BaseRole],
    ) -> None:
        super().__init__(
            edge_name="@check_roles",
            is_dag=False,
            target_node_id=TypeIntrospection.full_qualname(role_cls),
            target_node=None,
        )

    @staticmethod
    def get_role_edges(
        action_cls: type[Any],
    ) -> list[RoleGraphEdge]:
        """Return one association stub per declared ``@check_roles`` concrete role."""
        spec = CheckRolesIntentResolver.resolve_check_roles(action_cls)
        declared = spec if isinstance(spec, tuple) else (spec,)
        seen: set[str] = set()
        out: list[RoleGraphEdge] = []
        for role_cls in declared:
            nid = TypeIntrospection.full_qualname(role_cls)
            if nid in seen:
                continue
            seen.add(nid)
            out.append(RoleGraphEdge(role_cls=role_cls))
        return out
