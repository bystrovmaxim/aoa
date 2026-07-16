# packages/aoa-action-machine/src/aoa/action_machine/graph/nodes/role_graph_node.py
"""
RoleGraphNode — interchange node for ``BaseRole`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provides a :class:`~aoa.action_machine.graph.core.base_graph_node.BaseGraphNode` view derived from
a role **class** object. Interchange data lives in ``id``, ``node_type``,
``label``, ``properties``, and ``edges``; the class is :attr:`~aoa.action_machine.graph.core.base_graph_node.BaseGraphNode.node_obj`.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    type[TRole]   (``TRole`` bound to ``BaseRole``)
              │
              v
    RoleGraphNode(...)  ──>  frozen ``BaseGraphNode`` + aggregation to ``Application``

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path::

    class OrderViewerRole(BaseRole): ...
    n = RoleGraphNode(OrderViewerRole)
    assert n.node_type == "Role" and n.label == "OrderViewerRole"
    assert "role_mode" in n.properties

Edge case: same interchange shape for any concrete ``BaseRole`` subclass type passed in.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, TypeVar, cast

from aoa.action_machine.application.application import Application
from aoa.action_machine.auth.base_role import BaseRole
from aoa.action_machine.graph.core.base_graph_edge import BaseGraphEdge
from aoa.action_machine.graph.core.base_graph_node import BaseGraphNode
from aoa.action_machine.graph.edges.application_graph_edge import ApplicationGraphEdge
from aoa.action_machine.graph.edges.parent_role_graph_edge import ParentRoleGraphEdge, build_parent_role_edges
from aoa.action_machine.intents.check_roles.check_roles_intent_resolver import CheckRolesIntentResolver
from aoa.action_machine.system_core.type_introspection import TypeIntrospection

TRole = TypeVar("TRole", bound=BaseRole)


@dataclass(init=False, frozen=True)
class RoleGraphNode(BaseGraphNode[type[TRole]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for a ``BaseRole`` host class.
    CONTRACT: Built from ``type[TRole]``; :attr:`NODE_TYPE`; dotted ``id``, ``__name__`` label; ``properties`` include ``role_mode``. :attr:`application` aggregates to :class:`~aoa.action_machine.graph.nodes.application_graph_node.ApplicationGraphNode`; :meth:`get_all_edges` returns ``application`` then ``parent_role`` edges when present.
    INVARIANTS: Shared/deduplicated by ``node_id`` across every action referencing this role — the coordinator wires every matching :class:`~aoa.action_machine.graph.edges.role_graph_edge.RoleGraphEdge` from any number of actions to the *same* node instance. Never add per-action data here (e.g. ``@check_roles(grant(when=...))`` or ``guard=``): two actions requiring the same role with different conditions would silently clobber each other's value on this shared node. Per-action conditions belong on ``RoleGraphEdge`` (``when``, per grant) or ``ActionGraphNode`` (``guard``, per action) instead.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "Role"
    application: ApplicationGraphEdge = field(init=False, repr=False, compare=False)
    parent_roles: list[ParentRoleGraphEdge]

    def __init__(self, role_cls: type[TRole]) -> None:
        super().__init__(
            node_id=TypeIntrospection.full_qualname(role_cls),
            node_type=RoleGraphNode.NODE_TYPE,
            label=role_cls.__name__,
            properties={
                "role_mode": CheckRolesIntentResolver.resolve_role_mode(role_cls).value,
            },
            node_obj=role_cls,
        )
        object.__setattr__(self, "application", ApplicationGraphEdge(Application))
        object.__setattr__(self, "parent_roles", cast(list[ParentRoleGraphEdge], build_parent_role_edges(role_cls)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.node_id,
            "type": self.node_type,
            "label": self.label,
            "properties": {
                "role_mode": str(self.properties["role_mode"]),
            },
        }

    def get_all_edges(self) -> list[BaseGraphEdge]:
        """Return the application edge, then ``parent_role`` generalization edges (plan §I.6)."""
        return [self.application, *self.parent_roles]
