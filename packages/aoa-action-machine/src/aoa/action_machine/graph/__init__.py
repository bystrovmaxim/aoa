# packages/aoa-action-machine/src/aoa/action_machine/graph/__init__.py
"""
ActionMachine interchange graph — core primitives and domain projection.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide graph modeling for ActionMachine metadata: generic interchange rows in
``core/``, domain-specific nodes/edges/inspectors at this package level.

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

from typing import Any

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
    "GRAPH_JSON_SCHEMA",
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
    "create_node_graph_coordinator",
    "exclude_graph_model",
    "excluded_from_graph_model",
    "require_non_empty_str",
    "require_non_null",
]


def __getattr__(name: str) -> Any:
    if name == "GRAPH_JSON_SCHEMA":
        from aoa.action_machine.graph.graph_json_schema import GRAPH_JSON_SCHEMA

        return GRAPH_JSON_SCHEMA
    if name == "create_node_graph_coordinator":
        from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator

        return create_node_graph_coordinator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
