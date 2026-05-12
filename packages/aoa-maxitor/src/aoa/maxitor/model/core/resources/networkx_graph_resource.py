# packages/aoa-maxitor/src/aoa/maxitor/model/core/resources/networkx_graph_resource.py
"""
NetworkXGraphResource — ``ExternalServiceResource`` built from default coordinator export.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Standalone Maxitor resource: after construction, :attr:`.service` is a ``networkx.DiGraph``
rebuilt from ``json.loads(create_node_graph_coordinator().to_json())`` (no constructor arguments).
"""

from __future__ import annotations

import json
from typing import Any

import networkx as nx

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.external_service.external_service_resource import ExternalServiceResource
from aoa.maxitor.model.diagrams.diagrams_domain import DiagramsDomain

NETWORKX_GRAPH_CONNECTION_KEY = "NetworkXGraph"


@meta(
    description="NetworkX DiGraph rebuilt from default NodeGraphCoordinator JSON export",
    domain=DiagramsDomain,
)
class NetworkXGraphResource(ExternalServiceResource[Any]):
    """
    AI-CORE-BEGIN
    ROLE: Expose a ``DiGraph`` built from the production coordinator interchange JSON export.
    CONTRACT: ``__init__`` builds the graph from :meth:`get_networkx_graph` then calls ``super().__init__(service)``.
    AI-CORE-END
    """

    def __init__(self, coordinator_json: str) -> None:
        json_data: dict[str, Any] = json.loads(coordinator_json)
        service = self.get_networkx_graph(json_data)
        super().__init__(service)

    @staticmethod
    def get_networkx_graph(json_data: dict[str, Any]) -> Any:
        """Build a ``DiGraph`` from interchange ``nodes`` / ``edges`` (missing or empty → empty graph)."""
        nodes = json_data.get("nodes") or []
        edges = json_data.get("edges") or []
        graph: Any = nx.DiGraph()
        graph.graph["source_json"] = json_data
        for node in nodes:
            nid = node["id"]
            graph.add_node(nid, **node)
        for edge in edges:
            graph.add_edge(edge["source_node_id"], edge["target_node_id"], **edge)
        return graph
