# src/action_machine/model/graph_model/params_graph_node_inspector.py
"""
ParamsGraphNodeInspector — graph-node contributor for ``BaseParams`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Walks the loaded ``BaseParams`` strict subclass tree and emits one :class:`ParamsGraphNode` per
visited subtype. The ``BaseParams`` axis is excluded via
:meth:`~graph.base_graph_node_inspector.BaseGraphNodeInspector._graph_node_walk_excluded_types`.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseParams  (root axis, skipped in walk)
              │
              v
    each loaded strict subclass ``cls``  ->  ``[ParamsGraphNode(cls)]`` when ``issubclass(cls, BaseParams)``
"""

from __future__ import annotations

from typing import Any

from action_machine.model.base_params import BaseParams
from graph.base_graph_node import BaseGraphNode
from graph.base_graph_node_inspector import BaseGraphNodeInspector

from .params_graph_node import ParamsGraphNode


class ParamsGraphNodeInspector(BaseGraphNodeInspector[BaseParams]):
    """
    AI-CORE-BEGIN
    ROLE: Emit ``ParamsGraphNode`` rows for every loaded strict ``BaseParams`` subclass (not the root axis).
    CONTRACT: Root axis ``BaseParams`` from ``BaseGraphNodeInspector[BaseParams]``; one node per visited strict subtype.
    AI-CORE-END
    """

    def _graph_node_walk_excluded_types(self) -> frozenset[type]:
        return frozenset({BaseParams})

    def _get_type_nodes(self, cls: type) -> list[BaseGraphNode[Any]]:
        if isinstance(cls, type) and issubclass(cls, BaseParams):
            return [ParamsGraphNode(cls)]
        return []
