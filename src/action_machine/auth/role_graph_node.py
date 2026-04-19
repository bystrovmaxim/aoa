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
    RoleGraphNode.parse  ──>  frozen ``BaseGraphNode`` (id, node_type, label, properties, edges)

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- The role class is :attr:`~graph.base_graph_node.BaseGraphNode.obj`.
- ``node_type`` is ``"Role"`` (same convention as ``"Action"``, ``"Params"``, ``"Result"``, ``"Entity"``); ``label`` is the class ``__name__``; ``properties`` and ``edges`` are empty in ``parse``.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path::

    class OrderViewerRole(BaseRole): ...
    n = RoleGraphNode(OrderViewerRole)
    assert n.node_type == "Role" and n.label == "OrderViewerRole"

Edge case: same interchange shape for any concrete ``BaseRole`` subclass type passed in.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- No validation in ``parse``; concrete ``BaseRole`` subclasses are validated where declared.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Auth-scoped BaseGraphNode bridge for BaseRole subclasses.
CONTRACT: Construct from ``type[TRole]`` via ``parse``; ``node_type="Role"``; dotted-path ``id``; label = class name; empty properties and edges.
INVARIANTS: Immutable node; host class on ``BaseGraphNode.obj``.
FLOW: role class -> ``BaseGraphNode.__init__`` -> ``parse`` -> frozen BaseGraphNode fields.
EXTENSION POINTS: Other graph node specializations follow the same parse pattern.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar

from action_machine.auth.base_role import BaseRole
from action_machine.common import qualified_dotted_name
from graph.base_graph_node import BaseGraphNode, Payload

TRole = TypeVar("TRole", bound=BaseRole)


@dataclass(init=False, frozen=True)
class RoleGraphNode(BaseGraphNode[type[TRole]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for a ``BaseRole`` host class.
    CONTRACT: Built from ``type[TRole]``; ``node_type="Role"``; dotted ``id``, ``__name__`` label; empty ``properties`` and ``edges``.
    AI-CORE-END
    """

    @classmethod
    def parse(cls, role_cls: type[TRole]) -> Payload:
        return Payload(
            id=qualified_dotted_name(role_cls),
            node_type="Role",
            label=role_cls.__name__,
            properties={},
            edges=[],
        )
