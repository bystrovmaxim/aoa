# packages/aoa-action-machine/src/aoa/action_machine/graph/core/__init__.py
"""Graph interchange primitives (nodes, edges, coordinators, inspectors ABC)."""

from __future__ import annotations

from aoa.action_machine.graph.core.base_graph_edge import BaseGraphEdge
from aoa.action_machine.graph.core.base_graph_node import BaseGraphNode
from aoa.action_machine.graph.core.base_graph_node_inspector import BaseGraphNodeInspector
from aoa.action_machine.graph.core.edge_relationship import (
    ACCESS,
    AGGREGATION,
    ASSIGNMENT,
    ASSOCIATION,
    COMPOSITION,
    FLOW,
    GENERALIZATION,
    REALIZATION,
    SERVING,
    SPECIALIZATION,
    TRIGGERING,
    EdgeRelationship,
    EndpointAttachment,
    LineStyle,
)
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model, excluded_from_graph_model
from aoa.action_machine.graph.core.generalization_graph_edge import GeneralizationGraphEdge
from aoa.action_machine.graph.core.graph_edge import GraphEdge
from aoa.action_machine.graph.core.validation import require_non_empty_str, require_non_null

__all__ = [
    "ACCESS",
    "AGGREGATION",
    "ASSIGNMENT",
    "ASSOCIATION",
    "COMPOSITION",
    "FLOW",
    "GENERALIZATION",
    "REALIZATION",
    "SERVING",
    "SPECIALIZATION",
    "TRIGGERING",
    "BaseGraphEdge",
    "BaseGraphNode",
    "BaseGraphNodeInspector",
    "EdgeRelationship",
    "EndpointAttachment",
    "GeneralizationGraphEdge",
    "GraphEdge",
    "LineStyle",
    "exclude_graph_model",
    "excluded_from_graph_model",
    "require_non_empty_str",
    "require_non_null",
]
