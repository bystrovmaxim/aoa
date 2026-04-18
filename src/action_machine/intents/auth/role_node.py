# src/action_machine/intents/auth/role_node.py
"""
RoleNode — interchange node for ``BaseRole`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provides a :class:`~action_machine.graph.base_graph_node.BaseGraphNode` view derived from
a role **class** object **without** retaining a reference to that class on the
node instance. All interchange data lives in ``id``, ``node_type``,
``label``, ``properties``, and ``links``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    type[TRole]   (``TRole`` bound to ``BaseRole``)
              │
              v
    RoleNode.parse  ──>  frozen ``BaseGraphNode`` (id, node_type, label, properties, links)

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- The role class is not stored on :class:`RoleNode` instances (only interchange fields).
- ``node_type`` is ``"role_class"``; ``label`` is the class ``__name__``; ``properties`` and ``links`` are empty in ``parse``.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path::

    class OrderViewerRole(BaseRole): ...
    n = RoleNode(OrderViewerRole)
    assert n.node_type == "role_class" and n.label == "OrderViewerRole"

Edge case: same interchange shape for any concrete ``BaseRole`` subclass type passed in.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- No validation in ``parse``; concrete ``BaseRole`` subclasses are validated where declared.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Auth-scoped BaseGraphNode bridge for BaseRole subclasses.
CONTRACT: Construct from ``type[TRole]`` via ``parse``; ``node_type="role_class"``; dotted-path ``id``; label = class name; empty properties and links.
INVARIANTS: Immutable node; no role type reference on the instance.
FLOW: role class -> ``BaseGraphNode.__init__`` -> ``parse`` -> frozen BaseGraphNode fields.
EXTENSION POINTS: Other graph node specializations follow the same parse pattern.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, TypeVar

from action_machine.common import qualified_dotted_name
from action_machine.graph.base_graph_node import BaseGraphNode
from action_machine.intents.auth.base_role import BaseRole

TRole = TypeVar("TRole", bound=BaseRole)


@dataclass(init=False, frozen=True)
class RoleNode(BaseGraphNode[type[TRole]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for a ``BaseRole`` host class.
    CONTRACT: Built from ``type[TRole]``; dotted ``id``, ``__name__`` label, empty ``properties`` and ``links``.
    AI-CORE-END
    """

    @classmethod
    def parse(cls, role_cls: type[TRole]) -> Any:
        return SimpleNamespace(
            id=qualified_dotted_name(role_cls),
            node_type="Role",
            label=role_cls.__name__,
            properties={},
            links=[],
        )
