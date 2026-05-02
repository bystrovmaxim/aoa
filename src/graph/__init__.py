# src/graph/__init__.py
"""
ActionMachine **graph** subpackage (coordinator, inspectors, graph model types).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide the shared graph-modeling surface for ActionMachine metadata: interchange
node/edge types and node-graph coordinators.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    decorators write class/method scratch
              │
              ▼
    graph_model node inspectors  →  NodeGraphCoordinator.build([…])
              │
              ▼
    rustworkx interchange graph + tooling reads
"""

from __future__ import annotations

from graph.base_graph_edge import BaseGraphEdge
from graph.base_graph_node import BaseGraphNode
from graph.base_graph_node_inspector import BaseGraphNodeInspector
from graph.edge_relationship import (
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
from graph.exclude_graph_model import exclude_graph_model, excluded_from_graph_model
from graph.graph_edge import GraphEdge
from graph.validation import require_non_empty_str, require_non_null

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
    "GraphEdge",
    "LineStyle",
    "exclude_graph_model",
    "excluded_from_graph_model",
    "require_non_empty_str",
    "require_non_null",
]
