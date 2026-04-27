# src/action_machine/resources/graph_model/resource_graph_node_inspector.py
"""
ResourceGraphNodeInspector — graph-node contributor for ``BaseResource`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Walks the loaded ``BaseResource`` strict subclass tree and emits one
:class:`~action_machine.resources.graph_model.resource_graph_node.ResourceGraphNode` per
visited concrete or abstract resource class.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseResource  (root axis)
              │
              v
    each strict subclass ``cls``  ->  ``[ResourceGraphNode(cls)]`` when ``issubclass(cls, BaseResource)``
"""

from __future__ import annotations

from typing import Any

from action_machine.resources.base_resource import BaseResource
from graph.base_graph_node import BaseGraphNode
from graph.base_graph_node_inspector import BaseGraphNodeInspector

from .resource_graph_node import ResourceGraphNode


class ResourceGraphNodeInspector(BaseGraphNodeInspector[BaseResource]):
    """
    AI-CORE-BEGIN
    ROLE: Emit ``ResourceGraphNode`` rows for every loaded ``BaseResource`` subclass.
    CONTRACT: Root axis ``BaseResource`` from ``BaseGraphNodeInspector[BaseResource]``; one node per visited resource class.
    AI-CORE-END
    """

    def _get_type_nodes(self, cls: type) -> list[BaseGraphNode[Any]]:
        if isinstance(cls, type) and issubclass(cls, BaseResource):
            return [ResourceGraphNode(cls)]
        return []
