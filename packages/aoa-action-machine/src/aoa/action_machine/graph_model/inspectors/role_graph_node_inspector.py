# packages/aoa-action-machine/src/aoa/action_machine/graph_model/inspectors/role_graph_node_inspector.py
"""
RoleGraphNodeInspector — graph-node contributor for ``BaseRole`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Walks the loaded strict ``BaseRole`` subclass tree and emits one :class:`RoleGraphNode` per
participating subtype. Classes opt out with
:class:`~aoa.graph.exclude_graph_model.exclude_graph_model` (see :meth:`~aoa.graph.base_graph_node_inspector.BaseGraphNodeInspector.get_graph_nodes`).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseRole  (axis root — skipped when decorated with ``exclude_graph_model``)
              │
              v
    each visited ``cls``  ->  ``RoleGraphNode(cls)`` when ``issubclass(cls, BaseRole)``
"""

from __future__ import annotations

from typing import Any

from aoa.action_machine.auth.base_role import BaseRole
from aoa.graph.base_graph_node import BaseGraphNode
from aoa.graph.base_graph_node_inspector import BaseGraphNodeInspector

from ..nodes.role_graph_node import RoleGraphNode


class RoleGraphNodeInspector(BaseGraphNodeInspector[BaseRole]):
    """
    AI-CORE-BEGIN
    ROLE: Emit ``RoleGraphNode`` rows for visited ``BaseRole`` classes.
    CONTRACT: Root axis ``BaseRole`` from ``BaseGraphNodeInspector[BaseRole]``; one ``RoleGraphNode`` per visited subtype after ``exclude_graph_model`` filtering.
    AI-CORE-END
    """

    def _get_node(self, cls: type) -> BaseGraphNode[Any] | None:
        return RoleGraphNode(cls)
