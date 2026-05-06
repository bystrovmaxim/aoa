# src/graph/create_node_graph_coordinator.py
"""
Factory for the default ``NodeGraphCoordinator`` instance.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Create and build a ``NodeGraphCoordinator`` using the current node-graph
inspector set that is already used by viz2.
"""

from __future__ import annotations

from typing import Any

from action_machine.graph_model.inspectors.action_graph_node_inspector import ActionGraphNodeInspector
from action_machine.graph_model.inspectors.application_graph_node_inspector import (
    ApplicationGraphNodeInspector,
)
from action_machine.graph_model.inspectors.domain_graph_node_inspector import DomainGraphNodeInspector
from action_machine.graph_model.inspectors.entity_graph_node_inspector import EntityGraphNodeInspector
from action_machine.graph_model.inspectors.params_graph_node_inspector import ParamsGraphNodeInspector
from action_machine.graph_model.inspectors.resource_graph_node_inspector import ResourceGraphNodeInspector
from action_machine.graph_model.inspectors.result_graph_node_inspector import ResultGraphNodeInspector
from action_machine.graph_model.inspectors.role_graph_node_inspector import RoleGraphNodeInspector
from graph.base_graph_node_inspector import BaseGraphNodeInspector
from graph.node_graph_coordinator import NodeGraphCoordinator


def all_axis_graph_node_inspectors() -> list[BaseGraphNodeInspector[Any]]:
    """Return the default inspector instances for ``NodeGraphCoordinator``."""
    return [
        ParamsGraphNodeInspector(),
        ResultGraphNodeInspector(),
        RoleGraphNodeInspector(),
        DomainGraphNodeInspector(),
        ApplicationGraphNodeInspector(),
        ResourceGraphNodeInspector(),
        EntityGraphNodeInspector(),
        ActionGraphNodeInspector(),
    ]


def create_node_graph_coordinator() -> NodeGraphCoordinator:
    """Create and build the default ``NodeGraphCoordinator`` used by viz2."""
    coordinator = NodeGraphCoordinator()
    coordinator.build(all_axis_graph_node_inspectors())
    return coordinator
