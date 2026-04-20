# src/action_machine/auth/role_graph_node.py
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

Edge case: same interchange shape for any concrete ``BaseRole`` subclass type passed in.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar

from action_machine.auth.base_role import BaseRole
from graph.qualified_name import cls_qualified_dotted_id
from graph.base_graph_node import BaseGraphNode

TRole = TypeVar("TRole", bound=BaseRole)


@dataclass(init=False, frozen=True)
class RoleGraphNode(BaseGraphNode[type[TRole]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for a ``BaseRole`` host class.
    CONTRACT: Built from ``type[TRole]``; ``node_type="Role"``; dotted ``id``, ``__name__`` label; empty ``properties`` and ``edges``.
    AI-CORE-END
    """

    def __init__(self, role_cls: type[TRole]) -> None:
        super().__init__(
            node_id=cls_qualified_dotted_id(role_cls),
            node_type="Role",
            label=role_cls.__name__,
            properties={},
            edges=[],
            node_obj=role_cls,
        )
