# src/action_machine/model/params_graph_node_inspector.py
"""
ParamsGraphNodeInspector — graph-node contributor for ``BaseParams`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Walks the loaded ``BaseParams`` subclass tree and emits one :class:`ParamsGraphNode` per
visited class (including the ``BaseParams`` axis when :meth:`~graph.base_graph_node_inspector.BaseGraphNodeInspector.get_graph_nodes` calls the root).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseParams  (root)  ->  ``[ParamsGraphNode(BaseParams)]`` when included in the walk
              │
              v
    each loaded subclass ``cls``  ->  ``[ParamsGraphNode(cls)]`` when ``issubclass(cls, BaseParams)``
"""

from __future__ import annotations

from typing import Any

from action_machine.model.base_params import BaseParams
from action_machine.model.params_graph_node import ParamsGraphNode
from graph.base_graph_node import BaseGraphNode
from graph.base_graph_node_inspector import BaseGraphNodeInspector


class ParamsGraphNodeInspector(BaseGraphNodeInspector[BaseParams]):
    """
    AI-CORE-BEGIN
    ROLE: Emit ``ParamsGraphNode`` rows for every loaded ``BaseParams`` subclass.
    CONTRACT: Root axis ``BaseParams`` from ``BaseGraphNodeInspector[BaseParams]``; one node per visited subtype.
    AI-CORE-END
    """

    def _get_type_nodes(self, cls: type) -> list[BaseGraphNode[Any]]:
        if isinstance(cls, type) and issubclass(cls, BaseParams):
            return [ParamsGraphNode(cls)]
        return []
