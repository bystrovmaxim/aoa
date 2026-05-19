# packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/load_graph_action.py
"""
LoadGraphAction — materialize a NetworkX view of a coordinator graph.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Read-only action: accept a built :class:`~aoa.graph.node_graph_coordinator.NodeGraphCoordinator`
and expose a :class:`networkx.DiGraph` built from interchange nodes and outbound edges.
Not wired into the Flet shell yet; call explicitly from tests or future composition.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Params.graph
          |
          v
    regular aspect  ->  topology_nodes / topology_edges  (plain dicts, BaseState-safe)
          |
          v
    summary aspect  ->  Result.nx_graph (DiGraph) + counts; ``nx_graph.graph[MAXITOR_NX_GRAPH_COORDINATOR_KEY]`` holds Params.graph for ERD actions
"""

from __future__ import annotations

from typing import Any

import networkx as nx
from pydantic import ConfigDict, Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.checkers import result_instance
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.graph.base_graph_node import BaseGraphNode
from aoa.graph.node_graph_coordinator import NodeGraphCoordinator
from aoa.maxitor.model.core.core_domain import CoreDomain

# Populated on each ``LoadGraphAction`` result graph so downstream actions (e.g. ERD) can recover
# the built :class:`~aoa.graph.node_graph_coordinator.NodeGraphCoordinator` while accepting ``nx_graph`` only.
MAXITOR_NX_GRAPH_COORDINATOR_KEY = "_maxitor_node_graph_coordinator"


@meta(description="Load interchange graph into a NetworkX DiGraph (diagrams)", domain=CoreDomain)
@check_roles(NoneRole)
class LoadGraphAction(BaseAction["LoadGraphAction.Params", "LoadGraphAction.Result"]):
    """
    AI-CORE-BEGIN
    ROLE: Bridge NodeGraphCoordinator interchange rows to a NetworkX directed graph.
    CONTRACT: Params carry a built coordinator; regular aspect emits topology dict rows; Result holds nx.DiGraph plus counts.
    INVARIANTS: Only JSON-serializable structures on BaseState between aspects; DiGraph is built in the summary aspect.
    AI-CORE-END
    """

    class Params(BaseParams):
        graph: NodeGraphCoordinator = Field(description="Built coordinator whose nodes/edges are exported")

        model_config = ConfigDict(arbitrary_types_allowed=True)

    class Result(BaseResult):
        nx_graph: Any = Field(description="networkx.DiGraph over interchange node_id keys")
        node_count: int = Field(ge=0, description="Number of vertices in nx_graph")
        edge_count: int = Field(ge=0, description="Number of directed edges in nx_graph")

        model_config = ConfigDict(arbitrary_types_allowed=True)

    @regular_aspect("Extract graph topology for NetworkX materialization")
    @result_instance("topology_nodes", list, required=True)  # type: ignore[untyped-decorator]
    @result_instance("topology_edges", list, required=True)  # type: ignore[untyped-decorator]
    async def prepare_topology_aspect(
        self,
        params: LoadGraphAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> dict[str, Any]:
        nodes: tuple[BaseGraphNode[Any], ...] = params.graph.get_all_nodes()
        topology_nodes: list[dict[str, Any]] = [
            {"node_id": n.node_id, "node_type": n.node_type, "label": n.label} for n in nodes
        ]
        topology_edges: list[dict[str, Any]] = []
        for node in nodes:
            for edge in node.get_all_edges():
                topology_edges.append(
                    {
                        "source_id": node.node_id,
                        "target_id": edge.target_node_id,
                        "edge_name": edge.edge_name,
                        "is_dag": edge.is_dag,
                    },
                )
        return {
            "topology_nodes": topology_nodes,
            "topology_edges": topology_edges,
        }

    @summary_aspect("Build NetworkX graph")
    async def build_networkx_summary(
        self,
        params: LoadGraphAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> LoadGraphAction.Result:
        topology_nodes = list(getattr(state, "topology_nodes", []))
        topology_edges = list(getattr(state, "topology_edges", []))
        digraph: nx.DiGraph[Any] = nx.DiGraph()
        for row in topology_nodes:
            digraph.add_node(
                row["node_id"],
                node_type=row["node_type"],
                label=row["label"],
            )
        for row in topology_edges:
            digraph.add_edge(
                row["source_id"],
                row["target_id"],
                edge_name=row["edge_name"],
                is_dag=row["is_dag"],
            )
        digraph.graph[MAXITOR_NX_GRAPH_COORDINATOR_KEY] = params.graph
        return LoadGraphAction.Result(
            nx_graph=digraph,
            node_count=digraph.number_of_nodes(),
            edge_count=digraph.number_of_edges(),
        )
