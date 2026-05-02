# src/graph/__init__.py
"""
ActionMachine **graph** subpackage (facet snapshots, coordinator, inspectors).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide the shared graph-modeling surface for ActionMachine metadata: facet payloads,
interchange types, DAG helpers, and node-graph coordinators.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    decorators write class/method scratch
              │
              ▼
    intent inspectors emit FacetVertex / interchange pairs
              │
              ▼
    projection + NodeGraphCoordinator.build([…])
              │
              ▼
    rustworkx interchange graph + tooling reads
"""

from __future__ import annotations

from graph.base_facet_snapshot import BaseFacetSnapshot
from graph.base_graph_edge import BaseGraphEdge
from graph.base_graph_node import BaseGraphNode
from graph.base_graph_node_inspector import BaseGraphNodeInspector
from graph.base_intent_inspector import (
    FacetInspectResult,
    InspectGraphPair,
)
from graph.constants import (
    DAG_EDGE_TYPES,
    INTERNAL_EDGE_TYPES,
    OWNERSHIP_EDGE_TYPES,
)
from graph.dag import (
    assert_dag_edges_acyclic,
    collect_dag_edge_pairs,
    dag_edge_pairs_from_rx,
    dag_subgraph_is_acyclic,
    dag_subgraph_is_acyclic_from_rx,
)
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
from graph.graph_builder import GraphBuilder, build_interchange_from_facet_vertices
from graph.graph_edge import GraphEdge
from graph.graph_vertex import GraphVertex, GraphVertexParseError, ParsedGraphVertex
from graph.validation import require_non_empty_str, require_non_null

__all__ = [
    "ACCESS",
    "AGGREGATION",
    "ASSIGNMENT",
    "ASSOCIATION",
    "COMPOSITION",
    "DAG_EDGE_TYPES",
    "FLOW",
    "GENERALIZATION",
    "INTERNAL_EDGE_TYPES",
    "OWNERSHIP_EDGE_TYPES",
    "REALIZATION",
    "SERVING",
    "SPECIALIZATION",
    "TRIGGERING",
    "BaseFacetSnapshot",
    "BaseGraphEdge",
    "BaseGraphNode",
    "BaseGraphNodeInspector",
    "EdgeRelationship",
    "EndpointAttachment",
    "FacetInspectResult",
    "GraphBuilder",
    "GraphEdge",
    "GraphVertex",
    "GraphVertexParseError",
    "InspectGraphPair",
    "LineStyle",
    "ParsedGraphVertex",
    "assert_dag_edges_acyclic",
    "build_interchange_from_facet_vertices",
    "collect_dag_edge_pairs",
    "dag_edge_pairs_from_rx",
    "dag_subgraph_is_acyclic",
    "dag_subgraph_is_acyclic_from_rx",
    "exclude_graph_model",
    "excluded_from_graph_model",
    "require_non_empty_str",
    "require_non_null",
]
