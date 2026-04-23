# src/action_machine/resources/graph_model/__init__.py
"""
Graph interchange nodes for the resources axis.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Exports :class:`~action_machine.resources.graph_model.resource_graph_node.ResourceGraphNode`
for coordinator / tooling without pulling the full ``action_machine.model`` graph stack.
"""

from __future__ import annotations

from action_machine.resources.graph_model.resource_graph_node import ResourceGraphNode

__all__ = ["ResourceGraphNode"]
