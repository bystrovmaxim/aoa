# src/action_machine/graph_model/nodes/role_graph_node.py
"""
RoleGraphNode — interchange node for ``BaseRole`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provides a :class:`~graph.base_graph_node.BaseGraphNode` view derived from
a role **class** object. Interchange data lives in ``id``, ``node_type``,
``label``, ``properties``, and ``edges``; the class is :attr:`~graph.base_graph_node.BaseGraphNode.node_obj`.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    type[TRole]   (``TRole`` bound to ``BaseRole``)
              │
              v
    RoleGraphNode(...)  ──>  frozen ``BaseGraphNode`` (node_id, node_type, label, properties, edges)

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

from dataclasses import dataclass
from typing import ClassVar, TypeVar

from action_machine.auth.base_role import BaseRole
from action_machine.intents.check_roles.check_roles_intent_resolver import (
    CheckRolesIntentResolver,
)
from action_machine.system_core import TypeIntrospection
from graph.base_graph_node import BaseGraphNode

TRole = TypeVar("TRole", bound=BaseRole)


@dataclass(init=False, frozen=True)
class RoleGraphNode(BaseGraphNode[type[TRole]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for a ``BaseRole`` host class.
    CONTRACT: Built from ``type[TRole]``; :attr:`NODE_TYPE` for ``node_type``; dotted ``id``, ``__name__`` label; ``properties`` include ``role_mode`` (``RoleMode.value``); ``edges`` empty until wired.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "Role"

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
