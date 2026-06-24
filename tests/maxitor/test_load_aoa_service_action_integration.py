# tests/maxitor/test_load_aoa_service_action_integration.py
# Integration test — skipped in CI.
# To run: uv run pytest tests/maxitor/test_load_aoa_service_action_integration.py -v -s
# Requires: uv run uvicorn aoa.examples.fastapi_mcp_services.app_fastapi_service:app --host 127.0.0.1 --port 8001

from __future__ import annotations

from typing import Any

import pytest

from aoa.action_machine.model import BaseState
from aoa.maxitor.model.core.actions.load_aoa_service_action import (
    LoadAOAServiceAction,
    LoadAOAServiceParams,
    LoadAOAServiceResult,
)

_ACTION = LoadAOAServiceAction()
_BASE_URL = "http://127.0.0.1:8001"


def _state(**kwargs: Any) -> BaseState:
    return BaseState(**kwargs)


@pytest.mark.skip(reason="integration: requires aoa-examples service running on http://127.0.0.1:8001")
@pytest.mark.asyncio
async def test_full_pipeline_against_real_service() -> None:
    params = LoadAOAServiceParams(service_url=_BASE_URL)

    # aspect 1
    r1 = await _ACTION.validate_url_aspect(params, _state(), None, {})  # type: ignore[arg-type]
    assert r1["service_graph_json_url"] == _BASE_URL

    # aspect 2
    r2 = await _ACTION.normalize_url_aspect(params, _state(**r1), None, {})  # type: ignore[arg-type]
    assert r2["service_graph_json_url"].endswith("/examples/model/graph-json")

    # aspect 3
    r3 = await _ACTION.validate_service_aspect(params, _state(**r2), None, {})  # type: ignore[arg-type]
    assert isinstance(r3["coordinator_json_raw"], str)

    # aspect 4
    r4 = await _ACTION.parse_service_graph_aspect(params, _state(**{**r2, **r3}), None, {})  # type: ignore[arg-type]
    graph_data = r4["service_graph_data"]
    assert "nodes" in graph_data and "edges" in graph_data
    print(f"\nnodes: {len(graph_data['nodes'])}, edges: {len(graph_data['edges'])}")

    # aspect 5 (summary)
    result = await _ACTION.build_duckdb_graph_summary(params, _state(**{**r2, **r4}), None, {})  # type: ignore[arg-type]
    assert isinstance(result, LoadAOAServiceResult)
    assert result.node_count == len(graph_data["nodes"])
    assert result.edge_count == len(graph_data["edges"])
    assert result.graph_resource is not None
    print(f"node_count={result.node_count}, edge_count={result.edge_count}")
    print(f"service_graph_json_url={result.service_graph_json_url}")
    print(f"graph_resource={result.graph_resource}")
