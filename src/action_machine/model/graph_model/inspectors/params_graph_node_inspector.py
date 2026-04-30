# src/action_machine/model/graph_model/inspectors/params_graph_node_inspector.py
"""
ParamsGraphNodeInspector — graph-node contributor for ``BaseParams`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Walks the loaded ``BaseParams`` subclass tree and emits one :class:`ParamsGraphNode` per
visited subtype plus that node's :class:`~graph.base_graph_node.BaseGraphNode.companion_nodes` (``FieldGraphNode`` rows).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseParams  (root axis)
              │
              v
    each loaded strict subclass ``cls``  ->  ``ParamsGraphNode(cls)`` plus :attr:`~graph.base_graph_node.BaseGraphNode.companion_nodes` (field rows) in the flat list when ``issubclass(cls, BaseParams)``
"""

from __future__ import annotations

from typing import Any

from action_machine.model.base_params import BaseParams
from graph.base_graph_node import BaseGraphNode
from graph.base_graph_node_inspector import BaseGraphNodeInspector

from ..params_graph_node import ParamsGraphNode


class ParamsGraphNodeInspector(BaseGraphNodeInspector[BaseParams]):
    """
    AI-CORE-BEGIN
    ROLE: Emit ``ParamsGraphNode`` rows for visited ``BaseParams`` classes.
    CONTRACT: Root axis ``BaseParams`` from ``BaseGraphNodeInspector[BaseParams]``; one ``ParamsGraphNode`` per visited subtype.
    AI-CORE-END
    """

    def _get_node(self, cls: type) -> BaseGraphNode[Any] | None:
        return ParamsGraphNode(cls)
