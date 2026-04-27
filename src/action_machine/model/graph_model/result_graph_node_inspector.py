# src/action_machine/model/graph_model/result_graph_node_inspector.py
"""
ResultGraphNodeInspector — graph-node contributor for ``BaseResult`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Walks the loaded ``BaseResult`` subclass tree and emits one :class:`ResultGraphNode` per
visited subtype plus that node's :class:`~graph.base_graph_node.BaseGraphNode.companion_nodes` (``FieldGraphNode`` rows).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseResult  (root axis)
              │
              v
    each loaded strict subclass ``cls``  ->  ``ResultGraphNode(cls)`` plus :attr:`~graph.base_graph_node.BaseGraphNode.companion_nodes` (field rows) in the flat list when ``issubclass(cls, BaseResult)``
"""

from __future__ import annotations

from typing import Any

from action_machine.model.base_result import BaseResult
from graph.base_graph_node import BaseGraphNode
from graph.base_graph_node_inspector import BaseGraphNodeInspector

from .result_graph_node import ResultGraphNode


class ResultGraphNodeInspector(BaseGraphNodeInspector[BaseResult]):
    """
    AI-CORE-BEGIN
    ROLE: Emit ``ResultGraphNode`` rows for visited ``BaseResult`` classes.
    CONTRACT: Root axis ``BaseResult`` from ``BaseGraphNodeInspector[BaseResult]``; one ``ResultGraphNode`` per visited strict subtype, then its ``companion_nodes`` in the same flat list.
    AI-CORE-END
    """

    def _get_type_nodes(self, cls: type) -> list[BaseGraphNode[Any]]:
        if isinstance(cls, type) and issubclass(cls, BaseResult):
            node = ResultGraphNode(cls)
            return [node, *node.companion_nodes]
        return []
