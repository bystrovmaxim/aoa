# src/graph/__init__.py
"""
ActionMachine **graph** subpackage (facet snapshots, coordinator, inspectors).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide the shared graph-modeling surface for ActionMachine metadata:
typed facet snapshots and transactional graph assembly via ``GraphCoordinator``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    decorators write class/method scratch
              │
              ▼
    inspectors read declarations -> FacetVertex + optional Snapshot
              │
              ▼
    GraphCoordinator.build()
      (collect -> validate -> commit)
              │
              ▼
    graph topology + typed snapshot cache
"""

from __future__ import annotations

from graph.base_facet_snapshot import BaseFacetSnapshot
from graph.base_graph_edge import BaseGraphEdge
from graph.base_graph_node import BaseGraphNode
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
    INFLUENCE,
    REALIZATION,
    SERVING,
    SPECIALIZATION,
    TRIGGERING,
    EdgeRelationship,
    EndpointAttachment,
    LineStyle,
)
from graph.graph_builder import GraphBuilder, build_interchange_from_facet_vertices
from graph.graph_coordinator import GraphCoordinator
from graph.graph_edge import GraphEdge
from graph.graph_vertex import GraphVertex, GraphVertexParseError, ParsedGraphVertex
from graph.node_graph_coordinator import NodeGraphCoordinator
from graph.qualified_name import cls_qualified_dotted_id
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
    "INFLUENCE",
    "INTERNAL_EDGE_TYPES",
    "OWNERSHIP_EDGE_TYPES",
    "REALIZATION",
    "SERVING",
    "SPECIALIZATION",
    "TRIGGERING",
    "BaseFacetSnapshot",
    "BaseGraphEdge",
    "BaseGraphNode",
    "EdgeRelationship",
    "EndpointAttachment",
    "FacetInspectResult",
    "GraphBuilder",
    "GraphCoordinator",
    "GraphEdge",
    "GraphVertex",
    "GraphVertexParseError",
    "InspectGraphPair",
    "LineStyle",
    "NodeGraphCoordinator",
    "ParsedGraphVertex",
    "assert_dag_edges_acyclic",
    "build_interchange_from_facet_vertices",
    "cls_qualified_dotted_id",
    "collect_dag_edge_pairs",
    "dag_edge_pairs_from_rx",
    "dag_subgraph_is_acyclic",
    "dag_subgraph_is_acyclic_from_rx",
    "require_non_empty_str",
    "require_non_null",
]
