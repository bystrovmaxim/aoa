# src/action_machine/auth/graph_model/inspectors/__init__.py
"""Backward-compatible re-export; inspectors live under :mod:`action_machine.graph_model.inspectors`."""

from action_machine.graph_model.inspectors.role_graph_node_inspector import (
    RoleGraphNodeInspector,
)

__all__ = ["RoleGraphNodeInspector"]
