# packages/aoa-action-machine/src/aoa/action_machine/graph/__init__.py
"""
ActionMachine interchange graph — core primitives and domain projection.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide graph modeling for ActionMachine metadata: generic interchange rows in
``core/``, domain-specific nodes/edges/inspectors at this package level.

Import ``create_node_graph_coordinator`` and ``GRAPH_JSON_SCHEMA`` from their leaf
modules (``node_graph_coordinator_factory``, ``graph_json_schema``).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    decorators write class/method scratch
              │
              ▼
    graph inspectors  →  NodeGraphCoordinator.build([…])
              │
              ▼
    dict[str, BaseGraphNode] + typed indexes + JSON export
"""

from __future__ import annotations

from aoa.action_machine.graph.core import (
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
    BaseGraphEdge,
    BaseGraphNode,
    BaseGraphNodeInspector,
    EdgeRelationship,
    EndpointAttachment,
    GeneralizationGraphEdge,
    GraphEdge,
    LineStyle,
    exclude_graph_model,
    excluded_from_graph_model,
    require_non_empty_str,
    require_non_null,
)

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
