# src/action_machine/graph_model/inspectors/result_graph_node_inspector.py
"""
ResultGraphNodeInspector — graph-node contributor for ``BaseResult`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Walks the loaded ``BaseResult`` strict subclass tree and emits one :class:`ResultGraphNode` per
subtype that participates in interchange plus that node's :class:`~graph.base_graph_node.BaseGraphNode.companion_nodes` (``FieldGraphNode`` rows); opt out with :class:`~graph.exclude_graph_model.exclude_graph_model`.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseResult  (axis root — skipped when decorated with ``exclude_graph_model``)
              │
              v
    each loaded strict subclass ``cls``  ->  ``ResultGraphNode(cls)`` plus :attr:`~graph.base_graph_node.BaseGraphNode.companion_nodes` (field rows) in the flat list when ``issubclass(cls, BaseResult)``
"""

from __future__ import annotations

from typing import Any

from action_machine.model.base_result import BaseResult
from graph.base_graph_node import BaseGraphNode
from graph.base_graph_node_inspector import BaseGraphNodeInspector

from ..nodes.result_graph_node import ResultGraphNode


class ResultGraphNodeInspector(BaseGraphNodeInspector[BaseResult]):
    """
    AI-CORE-BEGIN
    ROLE: Emit ``ResultGraphNode`` rows for visited ``BaseResult`` classes.
    CONTRACT: Root axis ``BaseResult`` from ``BaseGraphNodeInspector[BaseResult]``; one ``ResultGraphNode`` per visited subtype.
    AI-CORE-END
    """

    def _get_node(self, cls: type) -> BaseGraphNode[Any] | None:
        return ResultGraphNode(cls)
