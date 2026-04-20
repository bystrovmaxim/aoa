# src/action_machine/model/graph_model/action_graph_node_inspector.py
"""
ActionGraphNodeInspector — graph-node contributor for ``BaseAction`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Walks the loaded ``BaseAction`` strict subclass tree and emits one :class:`ActionGraphNode` per
visited concrete/abstract subtype. The ``BaseAction`` axis itself is excluded via
:meth:`~graph.base_graph_node_inspector.BaseGraphNodeInspector._graph_node_walk_excluded_types`
so the abstract root does not emit an interchange row.
Aspects / compensators / etc. are not separate :class:`~graph.base_graph_node.BaseGraphNode`
types yet, so they are omitted until modeled.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseAction  (root axis, skipped in walk)
              │
              v
    each loaded strict subclass ``cls``  ->  ``[ActionGraphNode(cls)]`` when ``issubclass(cls, BaseAction)``
"""

from __future__ import annotations

from typing import Any

from action_machine.model.base_action import BaseAction
from graph.base_graph_node import BaseGraphNode
from graph.base_graph_node_inspector import BaseGraphNodeInspector

from .action_graph_node import ActionGraphNode


class ActionGraphNodeInspector(BaseGraphNodeInspector[BaseAction[Any, Any]]):
    """
    AI-CORE-BEGIN
    ROLE: Emit ``ActionGraphNode`` rows for every loaded strict ``BaseAction`` subclass (not the root axis).
    CONTRACT: Root axis ``BaseAction`` from ``BaseGraphNodeInspector[BaseAction[Any, Any]]``; one ``ActionGraphNode`` per visited strict ``BaseAction`` subtype (root excluded).
    INVARIANTS: No interchange nodes for aspects until they have their own node types.
    AI-CORE-END
    """

    def _graph_node_walk_excluded_types(self) -> frozenset[type]:
        return frozenset({BaseAction})

    def _get_type_nodes(self, cls: type) -> list[BaseGraphNode[Any]]:
        if isinstance(cls, type) and issubclass(cls, BaseAction):
            return [ActionGraphNode(cls)]
        return []
