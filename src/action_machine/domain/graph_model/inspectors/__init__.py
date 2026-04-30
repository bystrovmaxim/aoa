# src/action_machine/domain/graph_model/inspectors/__init__.py
"""Backward-compatible re-export; inspectors live under :mod:`action_machine.graph_model.inspectors`."""

from action_machine.graph_model.inspectors.domain_graph_node_inspector import (
    DomainGraphNodeInspector,
)
from action_machine.graph_model.inspectors.entity_graph_node_inspector import (
    EntityGraphNodeInspector,
)

__all__ = ["DomainGraphNodeInspector", "EntityGraphNodeInspector"]
