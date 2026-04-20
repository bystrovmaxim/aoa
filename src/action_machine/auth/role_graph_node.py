# src/action_machine/auth/role_graph_node.py
"""
RoleGraphNode — interchange node for ``BaseRole`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provides a :class:`~graph.base_graph_node.BaseGraphNode` view derived from
a role **class** object. Interchange data lives in ``id``, ``node_type``,
``label``, ``properties``, and ``edges``; the class is :attr:`~graph.base_graph_node.BaseGraphNode.obj`.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    type[TRole]   (``TRole`` bound to ``BaseRole``)
              │
              v
    RoleGraphNode(...)  ──>  frozen ``BaseGraphNode`` (id, node_type, label, properties, edges)

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path::

    class OrderViewerRole(BaseRole): ...
    n = RoleGraphNode(OrderViewerRole)
    assert n.node_type == "Role" and n.label == "OrderViewerRole"

Edge case: same interchange shape for any concrete ``BaseRole`` subclass type passed in.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Auth-scoped BaseGraphNode bridge for BaseRole subclasses.
CONTRACT: Construct from ``type[TRole]`` via ``__init__``; ``node_type="Role"``; dotted-path ``id``; label = class name; empty properties and edges.
INVARIANTS: Immutable node; host class on ``BaseGraphNode.obj``.
FLOW: role class -> ``RoleGraphNode.__init__`` -> frozen ``BaseGraphNode`` fields.
EXTENSION POINTS: Other graph node specializations follow the same constructor pattern.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
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
            id=cls_qualified_dotted_id(role_cls),
            node_type="Role",
            label=role_cls.__name__,
            properties={},
            edges=[],
            obj=role_cls,
        )
