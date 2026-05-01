# src/action_machine/graph_model/inspectors/resource_graph_node_inspector.py
"""
ResourceGraphNodeInspector — graph-node contributor for ``BaseResource`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Walks the loaded ``BaseResource`` strict subclass tree and emits one
:class:`~action_machine.graph_model.nodes.resource_graph_node.ResourceGraphNode` per
visited **non-abstract** subtype; abstract ABC markers are omitted by :meth:`~graph.base_graph_node_inspector.BaseGraphNodeInspector.get_graph_nodes` before :meth:`~graph.base_graph_node_inspector.BaseGraphNodeInspector._get_node`.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseResource  (axis root — omitted when ABC / abstract)
              │
              v
    each strict subclass ``cls``  ->  ``[ResourceGraphNode(cls)]`` when ``issubclass(cls, BaseResource)``
"""

from __future__ import annotations

from typing import Any

from action_machine.graph_model.nodes.resource_graph_node import ResourceGraphNode
from action_machine.resources.base_resource import BaseResource
from graph.base_graph_node import BaseGraphNode
from graph.base_graph_node_inspector import BaseGraphNodeInspector


class ResourceGraphNodeInspector(BaseGraphNodeInspector[BaseResource]):
    """
    AI-CORE-BEGIN
    ROLE: Emit ``ResourceGraphNode`` rows for every loaded ``BaseResource`` subclass.
    CONTRACT: Root axis ``BaseResource`` from ``BaseGraphNodeInspector[BaseResource]``; one node per visited resource class.
    AI-CORE-END
    """

    def _get_node(self, cls: type) -> BaseGraphNode[Any] | None:
        if isinstance(cls, type) and issubclass(cls, BaseResource):
            return ResourceGraphNode(cls)
        return None
