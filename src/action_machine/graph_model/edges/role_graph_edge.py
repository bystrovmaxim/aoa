# src/action_machine/graph_model/edges/role_graph_edge.py
"""
RoleGraphEdge — COMPOSITION from Action → Role interchange vertex (@check_roles).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Analogue to :class:`~action_machine.graph_model.edges.regular_aspect_graph_edge.RegularAspectGraphEdge`:
``is_dag=False`` composition keyed by ``@requires_role``, materializing ``RoleGraphNode``
only after interchange resolution (targets start as stubs by ``target_node_id``).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    ActionGraphNode  ──@requires_role──►  RoleGraphNode  (wired by coordinator)
"""

from __future__ import annotations

from typing import Any

from action_machine.auth.any_role import AnyRole
from action_machine.auth.base_role import BaseRole
from action_machine.auth.none_role import NoneRole
from action_machine.model.base_action import BaseAction
from action_machine.system_core import TypeIntrospection
from graph.base_graph_node import BaseGraphNode
from graph.composition_graph_edge import CompositionGraphEdge


class RoleGraphEdge(CompositionGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed composition edge Action host → ``@check_roles`` role class vertex.
    CONTRACT: ``edge_name`` ``@requires_role``; ``target_node_id`` dotted role class path; coordinator wires ``target_node``.
    INVARIANTS: Frozen via ``CompositionGraphEdge``; ``is_dag`` False.
    AI-CORE-END
    """

    def __init__(
        self,
        *,
        source_node: BaseGraphNode[Any],
        role_cls: type[BaseRole],
    ) -> None:
        super().__init__(
            edge_name="@requires_role",
            is_dag=False,
            source_node_id=source_node.node_id,
            source_node=source_node,
            target_node_id=TypeIntrospection.full_qualname(role_cls),
            target_node=None,
        )

    @staticmethod
    def get_role_edges(
        source_node: BaseGraphNode[Any],
        action_cls: type[BaseAction[Any, Any]],
    ) -> list[RoleGraphEdge]:
        """Return one composition stub per declared ``@check_roles`` concrete role."""
        declared = RoleGraphEdge._declared_role_classes(action_cls)
        seen: set[str] = set()
        out: list[RoleGraphEdge] = []
        for role_cls in declared:
            nid = TypeIntrospection.full_qualname(role_cls)
            if nid in seen:
                continue
            seen.add(nid)
            out.append(RoleGraphEdge(source_node=source_node, role_cls=role_cls))
        return out

    @staticmethod
    def _declared_role_classes(action_cls: type) -> tuple[type[BaseRole], ...]:
        """Unpack ``cls._role_info['spec']`` into concrete ``BaseRole`` types (facet-aligned)."""

        raw = getattr(action_cls, "_role_info", None)
        if not isinstance(raw, dict):
            return ()
        spec = raw.get("spec")
        return RoleGraphEdge._role_types_from_check_roles_spec(spec)

    @staticmethod
    def _role_types_from_check_roles_spec(spec: object) -> tuple[type[BaseRole], ...]:
        if spec in (NoneRole, AnyRole):
            return ()
        if isinstance(spec, type) and issubclass(spec, BaseRole):
            return (spec,)
        if isinstance(spec, tuple):
            return tuple(r for r in spec if isinstance(r, type) and issubclass(r, BaseRole))
        return ()
