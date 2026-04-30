# src/action_machine/graph_model/inspectors/role_graph_node_inspector.py
"""
RoleGraphNodeInspector — graph-node contributor for ``BaseRole`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Walks the loaded ``BaseRole`` subclass tree and emits one :class:`RoleGraphNode` per
visited class.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseRole
              │
              v
    each visited ``cls``  ->  ``[RoleGraphNode(cls)]`` when ``issubclass(cls, BaseRole)``
"""

from __future__ import annotations

from typing import Any

from action_machine.auth.base_role import BaseRole
from graph.base_graph_node import BaseGraphNode
from graph.base_graph_node_inspector import BaseGraphNodeInspector

from ..nodes.role_graph_node import RoleGraphNode


class RoleGraphNodeInspector(BaseGraphNodeInspector[BaseRole]):
    """
    AI-CORE-BEGIN
    ROLE: Emit ``RoleGraphNode`` rows for visited ``BaseRole`` classes.
    CONTRACT: Root axis ``BaseRole`` from ``BaseGraphNodeInspector[BaseRole]``; one node per visited role class.
    AI-CORE-END
    """

    def _get_node(self, cls: type) -> BaseGraphNode[Any] | None:
        if isinstance(cls, type) and issubclass(cls, BaseRole):
            return RoleGraphNode(cls)
        return None
