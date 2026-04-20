# src/action_machine/model/result_graph_node_inspector.py
"""
ResultGraphNodeInspector — graph-node contributor for ``BaseResult`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Walks the loaded ``BaseResult`` subclass tree and emits one :class:`ResultGraphNode` per
visited class (including the ``BaseResult`` axis when :meth:`~graph.base_graph_node_inspector.BaseGraphNodeInspector.get_graph_nodes` calls the root).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseResult  (root)  ->  ``[ResultGraphNode(BaseResult)]`` when included in the walk
              │
              v
    each loaded subclass ``cls``  ->  ``[ResultGraphNode(cls)]`` when ``issubclass(cls, BaseResult)``
"""

from __future__ import annotations

from typing import Any

from action_machine.model.base_result import BaseResult
from action_machine.model.result_graph_node import ResultGraphNode
from graph.base_graph_node import BaseGraphNode
from graph.base_graph_node_inspector import BaseGraphNodeInspector


class ResultGraphNodeInspector(BaseGraphNodeInspector[BaseResult]):
    """
    AI-CORE-BEGIN
    ROLE: Emit ``ResultGraphNode`` rows for every loaded ``BaseResult`` subclass.
    CONTRACT: Root axis ``BaseResult`` from ``BaseGraphNodeInspector[BaseResult]``; one node per visited subtype.
    AI-CORE-END
    """

    def _get_type_nodes(self, cls: type) -> list[BaseGraphNode[Any]]:
        if isinstance(cls, type) and issubclass(cls, BaseResult):
            return [ResultGraphNode(cls)]
        return []
