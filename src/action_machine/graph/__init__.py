# src/action_machine/graph/__init__.py
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

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``GraphCoordinator`` is the single graph assembly and validation entry point.
- Snapshot storage keys are inspector-defined but coordinator-managed.
- Read APIs require an explicitly built coordinator instance.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- This package root exports contracts; concrete behavior lives in submodules.
- Graph integrity failures surface during coordinator build phases.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Public namespace for graph core contracts.
CONTRACT: Export ``BaseFacetSnapshot`` and ``GraphCoordinator`` as graph-layer API.
INVARIANTS: Inspectors populate facet vertices/snapshots; coordinator owns transactional build semantics.
FLOW: declaration scratch -> inspector extraction -> coordinator validation/commit -> graph read APIs.
FAILURES: Build/read lifecycle errors and graph validation exceptions are raised by coordinator internals.
EXTENSION POINTS: Add inspector modules and snapshot types without changing package root API.
AI-CORE-END
"""

from __future__ import annotations

from action_machine.graph.base_facet_snapshot import BaseFacetSnapshot
from action_machine.graph.base_graph_edge import BaseGraphEdge
from action_machine.graph.base_intent_inspector import (
    FacetInspectResult,
    InspectGraphPair,
)
from action_machine.graph.constants import (
    DAG_EDGE_TYPES,
    INTERNAL_EDGE_TYPES,
    OWNERSHIP_EDGE_TYPES,
)
from action_machine.graph.dag import (
    assert_dag_edges_acyclic,
    collect_dag_edge_pairs,
    dag_edge_pairs_from_rx,
    dag_subgraph_is_acyclic,
    dag_subgraph_is_acyclic_from_rx,
)
from action_machine.graph.graph_builder import GraphBuilder, build_interchange_from_facet_vertices
from action_machine.graph.graph_coordinator import GraphCoordinator
from action_machine.graph.node_graph_coordinator import GraphNodeSource, NodeGraphCoordinator
from action_machine.graph.graph_edge import GraphEdge
from action_machine.graph.base_graph_node import (
    BaseGraphNode,
    BaseGraphNodeParseError,
    Payload,
)
from action_machine.graph.graph_vertex import GraphVertex, GraphVertexParseError, ParsedGraphVertex

__all__ = [
    "DAG_EDGE_TYPES",
    "INTERNAL_EDGE_TYPES",
    "OWNERSHIP_EDGE_TYPES",
    "BaseFacetSnapshot",
    "BaseGraphEdge",
    "FacetInspectResult",
    "InspectGraphPair",
    "GraphBuilder",
    "GraphCoordinator",
    "GraphNodeSource",
    "NodeGraphCoordinator",
    "GraphEdge",
    "BaseGraphNode",
    "BaseGraphNodeParseError",
    "Payload",
    "GraphVertex",
    "GraphVertexParseError",
    "ParsedGraphVertex",
    "assert_dag_edges_acyclic",
    "build_interchange_from_facet_vertices",
    "collect_dag_edge_pairs",
    "dag_edge_pairs_from_rx",
    "dag_subgraph_is_acyclic",
    "dag_subgraph_is_acyclic_from_rx",
]
