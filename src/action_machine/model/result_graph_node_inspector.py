# src/action_machine/model/result_graph_node_inspector.py
"""
ResultGraphNodeInspector — graph-node contributor for ``BaseResult`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Walks the loaded ``BaseResult`` strict subclass tree and emits one :class:`ResultGraphNode` per
visited subtype. The ``BaseResult`` axis is excluded via
:meth:`~graph.base_graph_node_inspector.BaseGraphNodeInspector._graph_node_walk_excluded_types`.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseResult  (root axis, skipped in walk)
              │
              v
    each loaded strict subclass ``cls``  ->  ``[ResultGraphNode(cls)]`` when ``issubclass(cls, BaseResult)``
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
    ROLE: Emit ``ResultGraphNode`` rows for every loaded strict ``BaseResult`` subclass (not the root axis).
    CONTRACT: Root axis ``BaseResult`` from ``BaseGraphNodeInspector[BaseResult]``; one node per visited strict subtype.
    AI-CORE-END
    """

    def _graph_node_walk_excluded_types(self) -> frozenset[type]:
        return frozenset({BaseResult})

    def _get_type_nodes(self, cls: type) -> list[BaseGraphNode[Any]]:
        if isinstance(cls, type) and issubclass(cls, BaseResult):
            return [ResultGraphNode(cls)]
        return []
