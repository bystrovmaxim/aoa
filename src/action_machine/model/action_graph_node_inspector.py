# src/action_machine/model/action_graph_node_inspector.py
"""
ActionGraphNodeInspector — graph-node contributor for ``BaseAction`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Walks the loaded ``BaseAction`` subclass tree and emits one :class:`ActionGraphNode` per
visited class (including the ``BaseAction`` axis when :meth:`~graph.base_graph_node_inspector.BaseGraphNodeInspector.get_graph_nodes` calls the root).
Aspects / compensators / etc. are not separate :class:`~graph.base_graph_node.BaseGraphNode`
types yet, so they are omitted until modeled.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseAction  (root)  ->  ``[ActionGraphNode(BaseAction)]`` when included in the walk
              │
              v
    each loaded subclass ``cls``  ->  ``[ActionGraphNode(cls)]`` when ``issubclass(cls, BaseAction)``
"""

from __future__ import annotations

from typing import Any

from action_machine.model.action_graph_node import ActionGraphNode
from action_machine.model.base_action import BaseAction
from graph.base_graph_node import BaseGraphNode
from graph.base_graph_node_inspector import BaseGraphNodeInspector


class ActionGraphNodeInspector(BaseGraphNodeInspector[BaseAction[Any, Any]]):
    """
    AI-CORE-BEGIN
    ROLE: Emit ``ActionGraphNode`` rows for every loaded ``BaseAction`` subclass.
    CONTRACT: Root axis ``BaseAction`` comes from ``BaseGraphNodeInspector[BaseAction[Any, Any]]``; one ``ActionGraphNode`` per visited ``BaseAction`` subtype.
    INVARIANTS: No interchange nodes for aspects until they have their own node types.
    AI-CORE-END
    """

    def _get_type_nodes(self, cls: type) -> list[BaseGraphNode[Any]]:
        if isinstance(cls, type) and issubclass(cls, BaseAction):
            return [ActionGraphNode(cls)]
        return []
