# src/action_machine/auth/graph_model/__init__.py
"""Interchange graph node types for the auth axis."""

from .inspectors.role_graph_node_inspector import RoleGraphNodeInspector
from .role_graph_node import RoleGraphNode

__all__ = ["RoleGraphNode", "RoleGraphNodeInspector"]
