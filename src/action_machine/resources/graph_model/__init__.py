# src/action_machine/resources/graph_model/__init__.py
"""
Graph interchange nodes for the resources axis.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Exports :class:`~action_machine.graph_model.nodes.resource_graph_node.ResourceGraphNode`
and :class:`~action_machine.resources.graph_model.inspectors.resource_graph_node_inspector.ResourceGraphNodeInspector`
for coordinator / tooling without pulling the full ``action_machine.model`` graph stack.
"""

from __future__ import annotations

from action_machine.graph_model.nodes.resource_graph_node import ResourceGraphNode
from action_machine.resources.graph_model.inspectors.resource_graph_node_inspector import (
    ResourceGraphNodeInspector,
)

__all__ = ["ResourceGraphNode", "ResourceGraphNodeInspector"]
