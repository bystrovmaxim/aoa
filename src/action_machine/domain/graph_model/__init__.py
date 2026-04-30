# src/action_machine/domain/graph_model/__init__.py
"""Interchange graph node types for the domain axis."""

from .domain_graph_node import DomainGraphNode
from .entity_graph_node import EntityGraphNode
from .inspectors.domain_graph_node_inspector import DomainGraphNodeInspector
from .inspectors.entity_graph_node_inspector import EntityGraphNodeInspector

__all__ = [
    "DomainGraphNode",
    "DomainGraphNodeInspector",
    "EntityGraphNode",
    "EntityGraphNodeInspector",
]
