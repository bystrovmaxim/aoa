# src/action_machine/auth/role_graph_node_inspector.py
"""
RoleGraphNodeInspector — graph-node contributor for ``BaseRole`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Walks the loaded ``BaseRole`` subclass tree and emits one :class:`RoleGraphNode` per
visited class (including the ``BaseRole`` axis when :meth:`~graph.base_graph_node_inspector.BaseGraphNodeInspector.get_graph_nodes` calls the root).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseRole  (root)  ->  ``[RoleGraphNode(BaseRole)]`` when included in the walk
              │
              v
    each loaded subclass ``cls``  ->  ``[RoleGraphNode(cls)]`` when ``issubclass(cls, BaseRole)``
"""

from __future__ import annotations

from typing import Any

from action_machine.auth.base_role import BaseRole
from action_machine.auth.role_graph_node import RoleGraphNode
from graph.base_graph_node import BaseGraphNode
from graph.base_graph_node_inspector import BaseGraphNodeInspector


class RoleGraphNodeInspector(BaseGraphNodeInspector[BaseRole]):
    """
    AI-CORE-BEGIN
    ROLE: Emit ``RoleGraphNode`` rows for every loaded ``BaseRole`` subclass.
    CONTRACT: Root axis ``BaseRole`` from ``BaseGraphNodeInspector[BaseRole]``; one node per visited subtype.
    AI-CORE-END
    """

    def _get_type_nodes(self, cls: type) -> list[BaseGraphNode[Any]]:
        if isinstance(cls, type) and issubclass(cls, BaseRole):
            return [RoleGraphNode(cls)]
        return []
