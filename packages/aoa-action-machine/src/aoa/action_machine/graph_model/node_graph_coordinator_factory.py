# packages/aoa-action-machine/src/aoa/action_machine/graph_model/node_graph_coordinator_factory.py
"""
NodeGraphCoordinator factory — default ActionMachine inspector wiring.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Build :class:`~aoa.graph.node_graph_coordinator.NodeGraphCoordinator` with the
standard interchange inspectors under ``aoa.action_machine.graph_model``. This module
belongs to ``action_machine`` so the ``graph`` package does not import ``action_machine``.
"""

from __future__ import annotations

from typing import Any

from aoa.action_machine.graph_model.inspectors.action_graph_node_inspector import ActionGraphNodeInspector
from aoa.action_machine.graph_model.inspectors.application_graph_node_inspector import (
    ApplicationGraphNodeInspector,
)
from aoa.action_machine.graph_model.inspectors.domain_graph_node_inspector import DomainGraphNodeInspector
from aoa.action_machine.graph_model.inspectors.entity_graph_node_inspector import EntityGraphNodeInspector
from aoa.action_machine.graph_model.inspectors.params_graph_node_inspector import ParamsGraphNodeInspector
from aoa.action_machine.graph_model.inspectors.resource_graph_node_inspector import ResourceGraphNodeInspector
from aoa.action_machine.graph_model.inspectors.result_graph_node_inspector import ResultGraphNodeInspector
from aoa.action_machine.graph_model.inspectors.role_graph_node_inspector import RoleGraphNodeInspector
from aoa.graph.base_graph_node_inspector import BaseGraphNodeInspector
from aoa.graph.node_graph_coordinator import NodeGraphCoordinator


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
    """Create and build the default ``NodeGraphCoordinator`` (production inspector set)."""
    coordinator = NodeGraphCoordinator()
    coordinator.build(all_axis_graph_node_inspectors())
    return coordinator
