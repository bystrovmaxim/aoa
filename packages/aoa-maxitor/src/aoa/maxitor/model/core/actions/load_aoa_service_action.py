# packages/aoa-maxitor/src/aoa/maxitor/model/core/actions/load_aoa_service_action.py
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
  3. validate_service — verify HTTP reachability and presence of coordinator_json field
  4. parse_service_graph — parse coordinator_json string, validate nodes/edges structure
  5. build_duckdb_graph (summary) — ingest service_graph_data into DuckDB, return counts
"""

from __future__ import annotations

import json
from typing import Any, cast
from urllib.parse import urlparse

import httpx
from pydantic import ConfigDict, Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.checkers import result_instance, result_string
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.maxitor.model.core.core_domain import CoreDomain
from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource

_GRAPH_JSON_PATH = "/examples/model/graph-json"


class LoadAOAServiceParams(BaseParams):
    model_config = ConfigDict(str_strip_whitespace=True)

    service_url: str = Field(
        min_length=1,
        description=(
            "AOA service URL — bare base URL (http://host:8001) or full graph-json endpoint "
            "(http://host:8001/examples/model/graph-json). "
            "The correct path is appended automatically when a base URL is supplied."
        ),
    )


class LoadAOAServiceResult(BaseResult):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    service_graph_json_url: str = Field(min_length=1, description="Resolved graph-json endpoint URL.")
    node_count: int = Field(ge=0, description="Number of nodes loaded into DuckDB.")
    edge_count: int = Field(ge=0, description="Number of edges loaded into DuckDB.")
    graph_resource: DuckDBGraphResource = Field(description="Populated DuckDB graph resource.")


@meta(description="Validate and load a remote AOA service graph into Maxitor.", domain=CoreDomain)
@check_roles(GuestRole)
class LoadAOAServiceAction(BaseAction[LoadAOAServiceParams, LoadAOAServiceResult]):
    """
    AI-CORE-BEGIN
    ROLE: Five-aspect pipeline — validate URL format, normalize to endpoint path, validate service reachability, parse graph data, build DuckDB graph.
    CONTRACT: Params.service_url accepts both a bare base URL (http://host:8001) and a full graph-json endpoint (http://host:8001/examples/model/graph-json); Result.graph_resource holds the populated DuckDB resource ready for catalog queries.
    INVARIANTS: Only one HTTP GET is made (in validate_service_aspect); subsequent aspects read from state without re-fetching.
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
        connections: dict[str, BaseResource],
    ) -> dict[str, Any]:
        _ = (state, box, connections)
        parsed = urlparse(params.service_url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(
                f"service_url must be an HTTP or HTTPS URL, got: {params.service_url!r}. "
                "Example: http://127.0.0.1:8001"
            )
        if not parsed.netloc:
            raise ValueError(
                f"service_url has no host: {params.service_url!r}. "
                "Example: http://127.0.0.1:8001"
            )
        return {"service_graph_json_url": params.service_url}

    # ─── Aspect 2 ────────────────────────────────────────────────────────────

    @result_string("service_graph_json_url", required=True, not_empty=True)  # type: ignore[untyped-decorator]
    @regular_aspect("Normalize the validated URL to the canonical graph-json endpoint path.")
    async def normalize_url_aspect(
        self,
        params: LoadAOAServiceParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> dict[str, Any]:
        _ = (params, box, connections)
        url = cast(str, state["service_graph_json_url"]).rstrip("/")
        if not url.endswith(_GRAPH_JSON_PATH):
            url = f"{url}{_GRAPH_JSON_PATH}"
        return {"service_graph_json_url": url}

    # ─── Aspect 3 ────────────────────────────────────────────────────────────

    @result_string("service_graph_json_url", required=True, not_empty=True)  # type: ignore[untyped-decorator]
    @result_string("coordinator_json_raw", required=True, not_empty=True)  # type: ignore[untyped-decorator]
    @regular_aspect("Validate the AOA service: check HTTP reachability and verify coordinator_json field is present.")
    async def validate_service_aspect(
        self,
        params: LoadAOAServiceParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> dict[str, Any]:
        _ = (params, box, connections)
        url = cast(str, state["service_graph_json_url"])

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=15.0)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ValueError(
                f"AOA service returned HTTP {exc.response.status_code} at {url!r}. "
                "Check that the service is running and the URL is correct."
            ) from exc
        except httpx.RequestError as exc:
            raise ValueError(
                f"Cannot reach AOA service at {url!r}: {exc}. "
                "Check that the host and port are correct."
            ) from exc

        try:
            envelope = response.json()
        except Exception as exc:
            raise ValueError(f"Response from {url!r} is not valid JSON: {exc}") from exc

        if not isinstance(envelope, dict):
            raise ValueError(f"Expected a JSON object from {url!r}, got {type(envelope).__name__}.")

        coordinator_json_raw = envelope.get("coordinator_json")
        if not isinstance(coordinator_json_raw, str):
            raise ValueError(
                f"Response from {url!r} is missing 'coordinator_json' string field. "
                "Ensure the endpoint is a valid AOA graph-json endpoint."
            )

        return {"service_graph_json_url": url, "coordinator_json_raw": coordinator_json_raw}

    # ─── Aspect 4 ────────────────────────────────────────────────────────────

    @result_string("service_graph_json_url", required=True, not_empty=True)  # type: ignore[untyped-decorator]
    @result_instance("service_graph_data", dict, required=True)  # type: ignore[untyped-decorator]
    @regular_aspect("Parse coordinator_json string and validate the graph structure contains nodes and edges.")
    async def parse_service_graph_aspect(
        self,
        params: LoadAOAServiceParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> dict[str, Any]:
        _ = (params, box, connections)
        url = cast(str, state["service_graph_json_url"])
        coordinator_json_raw = cast(str, state["coordinator_json_raw"])

        try:
            service_graph_data = cast(dict[str, Any], json.loads(coordinator_json_raw))
        except json.JSONDecodeError as exc:
            raise ValueError(f"'coordinator_json' from {url!r} is not valid JSON: {exc}") from exc

        if not isinstance(service_graph_data, dict):
            raise ValueError(
                f"'coordinator_json' from {url!r} decoded to {type(service_graph_data).__name__}, expected object."
            )
        if "nodes" not in service_graph_data or "edges" not in service_graph_data:
            raise ValueError(
                f"Coordinator JSON from {url!r} is missing 'nodes' or 'edges'. "
                "The service may be running an incompatible version."
            )

        return {"service_graph_json_url": url, "service_graph_data": service_graph_data}

    # ─── Aspect 5 (summary) ──────────────────────────────────────────────────

    @summary_aspect("Build DuckDB graph from service graph data and return load statistics.")
    async def build_duckdb_graph_summary(
        self,
        params: LoadAOAServiceParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> LoadAOAServiceResult:
        _ = (params, box, connections)
        url = cast(str, state["service_graph_json_url"])
        service_graph_data = cast(dict[str, Any], state["service_graph_data"])

        graph_resource = DuckDBGraphResource.build_from_json(service_graph_data)

        node_count = len(list(service_graph_data.get("nodes") or []))
        edge_count = len(list(service_graph_data.get("edges") or []))

        return LoadAOAServiceResult(
            service_graph_json_url=url,
            node_count=node_count,
            edge_count=edge_count,
            graph_resource=graph_resource,
        )
