# packages/maxitor/front/src/maxitor/front/model/core/actions/load_aoa_service_action.py
"""
LoadAOAServiceAction — validate and load a remote AOA service graph into Maxitor.

════════════════════════════════════════════════════════════════════════════════
PURPOSE
════════════════════════════════════════════════════════════════════════════════

Five-aspect pipeline that accepts a user-supplied AOA service URL and loads
the coordinator graph into DuckDB.

Aspect sequence:
  1. validate_url — verify the input is a well-formed HTTP/HTTPS URL
  2. normalize_url — resolve to canonical ``/examples/model/graph-json`` endpoint path
  3. validate_service — download through ``GraphSourceGateway``; take the envelope's coordinator_json, or a bare graph
     (``nodes`` and ``edges`` at the top, as a graph file keeps it) as it is
  4. parse_service_graph — parse coordinator_json string, validate nodes/edges structure
  5. build_duckdb_graph (summary) — ingest service_graph_data into DuckDB, return counts
"""

from __future__ import annotations

import json
import re
from typing import Any, cast
from urllib.parse import urlparse

from maxitor.front.model.core.core_domain import CoreDomain
from maxitor.front.model.core.resources.graph_source_gateway import (
    GRAPH_SOURCE_CONNECTION_KEY,
    GraphSourceGateway,
    Unreachable,
)
from maxitor.front.model.core.source_label import label
from maxitor.front.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource
from pydantic import ConfigDict, Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.checkers import result_instance, result_string
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox

_DEFAULT_GRAPH_JSON_PATH = "/examples/model/graph-json"
_PORT_SUFFIX = re.compile(r":\d{1,5}$")


def _with_default_scheme(raw: str) -> str:
    """Give a bare authority a scheme: ``http`` when a port is present, ``https`` otherwise."""
    if "://" in raw:
        return raw
    authority = raw.split("/", 1)[0]
    scheme = "http" if _PORT_SUFFIX.search(authority) else "https"
    return f"{scheme}://{raw}"


class LoadAOAServiceParams(BaseParams):
    model_config = ConfigDict(str_strip_whitespace=True)

    service_url: str = Field(
        min_length=1,
        description=(
            "AOA service URL — with or without a scheme and with or without a port: "
            "``http://host:8001``, ``https://host``, ``host:8001`` (defaults to http) or "
            "``host`` (defaults to https). When a bare base URL is supplied (no path), the "
            "default AOA path is appended automatically; a URL with an explicit path is used as-is."
        ),
    )


class LoadAOAServiceResult(BaseResult):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    service_graph_json_url: str = Field(min_length=1, description="Resolved graph-json endpoint URL.")
    node_count: int = Field(ge=0, description="Number of nodes loaded into DuckDB.")
    edge_count: int = Field(ge=0, description="Number of edges loaded into DuckDB.")
    graph_resource: DuckDBGraphResource = Field(description="Populated DuckDB graph resource.")
    content_sha256: str = Field(min_length=64, max_length=64, description="SHA-256 of the graph-json body the graph was built from.")
    etag: str = Field(description="The service's ETag for that body; empty when it gave none.")
    last_modified: str = Field(description="The service's Last-Modified for that body; empty when it gave none.")
    graph_text: str = Field(min_length=1, description="The graph's JSON text as built: the envelope's coordinator_json, or the bare graph.")


@meta(description="Validate and load a remote AOA service graph into Maxitor.", domain=CoreDomain)
@check_roles(GuestRole)
@connection(GraphSourceGateway, key=GRAPH_SOURCE_CONNECTION_KEY, description="Downloads the service's graph-json")
class LoadAOAServiceAction(BaseAction[LoadAOAServiceParams, LoadAOAServiceResult]):
    """
    AI-CORE-BEGIN
    ROLE: Five-aspect pipeline — validate URL format, normalize to endpoint path, validate service reachability, parse graph data, build DuckDB graph.
    CONTRACT: Params.service_url accepts both a bare base URL (http://host:8001) and a full graph-json endpoint (http://host:8001/examples/model/graph-json); Result.graph_resource holds the populated DuckDB resource ready for catalog queries.
    INVARIANTS: Only one download is made, through ``connections[GraphSource]`` in validate_service_aspect; subsequent aspects read from state without re-fetching; the body's SHA-256, validators and the graph's text travel to the result.
    AI-CORE-END
    """

    Params = LoadAOAServiceParams
    Result = LoadAOAServiceResult

    # ─── Aspect 1 ────────────────────────────────────────────────────────────

    @result_string("service_graph_json_url", required=True, not_empty=True)  # type: ignore[untyped-decorator]
    @regular_aspect("Validate that service_url is a well-formed HTTP or HTTPS URL.")
    async def validate_url_aspect(
        self,
        params: LoadAOAServiceParams,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> dict[str, Any]:
        _ = (state, box, connections)
        url = _with_default_scheme(params.service_url)
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(
                f"service_url must be an HTTP or HTTPS URL, got: {label(params.service_url)}. "
                "Examples: http://127.0.0.1:8001, demo:8100, dev.demo.aoa.run"
            )
        if not parsed.netloc:
            raise ValueError(
                f"service_url has no host: {label(params.service_url)}. "
                "Examples: http://127.0.0.1:8001, demo:8100, dev.demo.aoa.run"
            )
        return {"service_graph_json_url": url}

    # ─── Aspect 2 ────────────────────────────────────────────────────────────

    @result_string("service_graph_json_url", required=True, not_empty=True)  # type: ignore[untyped-decorator]
    @regular_aspect("Normalize URL: append default graph-json path only when no explicit path is given.")
    async def normalize_url_aspect(
        self,
        params: LoadAOAServiceParams,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> dict[str, Any]:
        _ = (params, box, connections)
        url = cast(str, state["service_graph_json_url"]).rstrip("/")
        parsed = urlparse(url)
        if not parsed.path or parsed.path == "/":
            url = f"{url}{_DEFAULT_GRAPH_JSON_PATH}"
        return {"service_graph_json_url": url}

    # ─── Aspect 3 ────────────────────────────────────────────────────────────

    @result_string("service_graph_json_url", required=True, not_empty=True)  # type: ignore[untyped-decorator]
    @result_string("coordinator_json_raw", required=True, not_empty=True)  # type: ignore[untyped-decorator]
    @result_instance("source_identity", dict, required=True)  # type: ignore[untyped-decorator]
    @regular_aspect("Validate the AOA service: check HTTP reachability and verify coordinator_json field is present.")
    async def validate_service_aspect(
        self,
        params: LoadAOAServiceParams,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> dict[str, Any]:
        _ = (params, box)
        url = cast(str, state["service_graph_json_url"])

        gateway = cast(GraphSourceGateway, connections[GRAPH_SOURCE_CONNECTION_KEY])
        answer = await gateway.fetch(url)
        if isinstance(answer, Unreachable):
            if answer.status is not None:
                raise ValueError(
                    f"AOA service returned HTTP {answer.status} at {label(url)}. "
                    "Check that the service is running and the URL is correct."
                )
            raise ValueError(
                f"Cannot reach AOA service at {label(url)}: {answer.reason}. "
                "Check that the host and port are correct."
            )

        try:
            envelope = json.loads(answer.body)
        except Exception as exc:
            raise ValueError(f"Response from {label(url)} is not valid JSON: {exc}") from exc

        if not isinstance(envelope, dict):
            raise ValueError(f"Expected a JSON object from {label(url)}, got {type(envelope).__name__}.")

        coordinator_json_raw = envelope.get("coordinator_json")
        if coordinator_json_raw is None and isinstance(envelope.get("nodes"), list) and isinstance(envelope.get("edges"), list):
            # A bare graph — a graph file as a repository keeps it, a history's version — is the graph itself.
            coordinator_json_raw = answer.body.decode("utf-8")
        if not isinstance(coordinator_json_raw, str):
            raise ValueError(
                f"Response from {label(url)} is neither a graph nor an envelope with a 'coordinator_json' string field. "
                "Ensure the endpoint is a valid AOA graph-json endpoint."
            )

        return {
            "service_graph_json_url": url,
            "coordinator_json_raw": coordinator_json_raw,
            "source_identity": {
                "sha256": answer.sha256,
                "etag": answer.etag or "",
                "last_modified": answer.last_modified or "",
            },
        }

    # ─── Aspect 4 ────────────────────────────────────────────────────────────

    @result_string("service_graph_json_url", required=True, not_empty=True)  # type: ignore[untyped-decorator]
    @result_instance("service_graph_data", dict, required=True)  # type: ignore[untyped-decorator]
    @result_instance("source_identity", dict, required=True)  # type: ignore[untyped-decorator]
    @result_string("coordinator_json_raw", required=True, not_empty=True)  # type: ignore[untyped-decorator]
    @regular_aspect("Parse coordinator_json string and validate the graph structure contains nodes and edges.")
    async def parse_service_graph_aspect(
        self,
        params: LoadAOAServiceParams,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> dict[str, Any]:
        _ = (params, box, connections)
        url = cast(str, state["service_graph_json_url"])
        coordinator_json_raw = cast(str, state["coordinator_json_raw"])

        try:
            service_graph_data = cast(dict[str, Any], json.loads(coordinator_json_raw))
        except json.JSONDecodeError as exc:
            raise ValueError(f"'coordinator_json' from {label(url)} is not valid JSON: {exc}") from exc

        if not isinstance(service_graph_data, dict):
            raise ValueError(
                f"'coordinator_json' from {label(url)} decoded to {type(service_graph_data).__name__}, expected object."
            )
        if "nodes" not in service_graph_data or "edges" not in service_graph_data:
            raise ValueError(
                f"Coordinator JSON from {label(url)} is missing 'nodes' or 'edges'. "
                "The service may be running an incompatible version."
            )

        return {
            "service_graph_json_url": url,
            "service_graph_data": service_graph_data,
            "source_identity": state["source_identity"],
            "coordinator_json_raw": coordinator_json_raw,
        }

    # ─── Aspect 5 (summary) ──────────────────────────────────────────────────

    @summary_aspect("Build DuckDB graph from service graph data and return load statistics.")
    async def build_duckdb_graph_summary(
        self,
        params: LoadAOAServiceParams,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> LoadAOAServiceResult:
        _ = (params, box, connections)
        url = cast(str, state["service_graph_json_url"])
        service_graph_data = cast(dict[str, Any], state["service_graph_data"])
        identity = cast(dict[str, str], state["source_identity"])

        graph_resource = DuckDBGraphResource.build_from_json(service_graph_data)

        node_count = len(list(service_graph_data.get("nodes") or []))
        edge_count = len(list(service_graph_data.get("edges") or []))

        return LoadAOAServiceResult(
            service_graph_json_url=url,
            node_count=node_count,
            edge_count=edge_count,
            graph_resource=graph_resource,
            content_sha256=identity["sha256"],
            etag=identity["etag"],
            last_modified=identity["last_modified"],
            graph_text=cast(str, state["coordinator_json_raw"]),
        )
