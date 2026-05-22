# packages/aoa-action-machine/src/aoa/action_machine/graph/inspectors/params_graph_node_inspector.py
"""
ParamsGraphNodeInspector — graph-node contributor for ``BaseParams`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Walks the loaded ``BaseParams`` strict subclass tree and emits one :class:`ParamsGraphNode` per
subtype that participates in interchange plus that node's :class:`~aoa.action_machine.graph.core.base_graph_node.BaseGraphNode.companion_nodes` (``FieldGraphNode`` rows); opt out with :class:`~aoa.action_machine.graph.core.exclude_graph_model.exclude_graph_model`.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseParams  (axis root — skipped when decorated with ``exclude_graph_model``)
              │
              v
    each loaded strict subclass ``cls``  ->  ``ParamsGraphNode(cls)`` plus :attr:`~aoa.action_machine.graph.core.base_graph_node.BaseGraphNode.companion_nodes` (field rows) in the flat list when ``issubclass(cls, BaseParams)``
"""

from __future__ import annotations

from typing import Any

from aoa.action_machine.graph.core.base_graph_node import BaseGraphNode
from aoa.action_machine.graph.core.base_graph_node_inspector import BaseGraphNodeInspector
from aoa.action_machine.model.base_params import BaseParams

from ..nodes.params_graph_node import ParamsGraphNode


class ParamsGraphNodeInspector(BaseGraphNodeInspector[BaseParams]):
    """
    AI-CORE-BEGIN
    ROLE: Emit ``ParamsGraphNode`` rows for visited ``BaseParams`` classes.
    CONTRACT: Root axis ``BaseParams`` from ``BaseGraphNodeInspector[BaseParams]``; one ``ParamsGraphNode`` per visited subtype.
    AI-CORE-END
    """

    def _get_node(self, cls: type) -> BaseGraphNode[Any] | None:
        return ParamsGraphNode(cls)
