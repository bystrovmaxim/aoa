# packages/aoa-maxitor/src/aoa/maxitor/model/core/resources/networkx_graph_resource.py
"""
NetworkXGraphResource — ``ExternalServiceResource`` built from example-model interchange JSON.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Standalone Maxitor resource: after construction, :attr:`.service` is a ``networkx.DiGraph``
rebuilt from interchange JSON fetched over HTTP from the examples API (no constructor arguments).
"""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import networkx as nx

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.external_service.external_service_resource import ExternalServiceResource
from aoa.maxitor.model.diagrams.diagrams_domain import DiagramsDomain

DEFAULT_EXAMPLE_GRAPH_JSON_URL = "http://127.0.0.1:8001/examples/model/graph-json"
ENV_EXAMPLE_GRAPH_JSON_URL = "MAXITOR_EXAMPLE_GRAPH_JSON_URL"

NETWORKX_GRAPH_CONNECTION_KEY = "NetworkXGraph"


@meta(
    description="NetworkX DiGraph rebuilt from example-model interchange JSON",
    domain=DiagramsDomain,
)
class NetworkXGraphResource(ExternalServiceResource[Any]):
    """
    AI-CORE-BEGIN
    ROLE: Expose a ``DiGraph`` built from the example-model interchange JSON export.
    CONTRACT: ``__init__`` builds the graph from :meth:`get_networkx_graph` then calls ``super().__init__(service)``.
    AI-CORE-END
    """

    def __init__(self) -> None:
        json_data = self.fetch_example_model_interchange_dict()
        service = self.get_networkx_graph(json_data)
        super().__init__(service)

    @staticmethod
    def fetch_example_model_interchange_dict() -> dict[str, Any]:
        """
        GET the examples ``graph-json`` envelope, then parse the inner ``coordinator_json`` string.

        URL: :envvar:`MAXITOR_EXAMPLE_GRAPH_JSON_URL` or ``http://127.0.0.1:8001/examples/model/graph-json``.
        """
        raw_url = os.environ.get(ENV_EXAMPLE_GRAPH_JSON_URL, DEFAULT_EXAMPLE_GRAPH_JSON_URL)
        url = (raw_url or "").strip() or DEFAULT_EXAMPLE_GRAPH_JSON_URL
        req = Request(url, method="GET")
        try:
            with urlopen(req, timeout=60) as resp:
                body = resp.read().decode("utf-8")
        except HTTPError as exc:
            msg = f"Example graph-json HTTP {exc.code} from {url!r}"
            raise RuntimeError(msg) from exc
        except URLError as exc:
            msg = f"Example graph-json request failed for {url!r}: {exc.reason!r}"
            raise RuntimeError(msg) from exc
        envelope: dict[str, Any] = json.loads(body)
        coordinator_raw = envelope.get("coordinator_json")
        if not isinstance(coordinator_raw, str):
            msg = f"Expected str coordinator_json in response from {url!r}, got {type(coordinator_raw).__name__}"
            raise TypeError(msg)
        return json.loads(coordinator_raw)


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
