# src/action_machine/domain/graph_model/__init__.py
"""Interchange graph node types for the domain axis."""

from action_machine.graph_model.inspectors.domain_graph_node_inspector import (
    DomainGraphNodeInspector,
)
from action_machine.graph_model.inspectors.entity_graph_node_inspector import (
    EntityGraphNodeInspector,
)
from action_machine.graph_model.nodes.domain_graph_node import DomainGraphNode
from action_machine.graph_model.nodes.entity_graph_node import EntityGraphNode

__all__ = [
    "DomainGraphNode",
    "DomainGraphNodeInspector",
    "EntityGraphNode",
    "EntityGraphNodeInspector",
]
