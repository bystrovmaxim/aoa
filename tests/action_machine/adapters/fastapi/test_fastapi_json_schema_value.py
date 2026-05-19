# tests/action_machine/adapters/fastapi/test_fastapi_json_schema_value.py
"""
FastAPI adapter + OpenAPI for models using ``JsonSchemaValue`` fields.

PR-2: no FastAPI adapter code changes were required — Pydantic hooks on
``JsonSchemaValue`` types supply OpenAPI field schemas and raw JSON bodies.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from aoa.action_machine.integrations.fastapi.adapter import FastApiAdapter
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from tests.action_machine.adapters.json_schema_adapter_fixtures import (
    AdapterTestAction,
)


def _resolve_ref(openapi: dict[str, Any], node: dict[str, Any]) -> dict[str, Any]:
    ref = node.get("$ref")
    if not isinstance(ref, str) or not ref.startswith("#/components/schemas/"):
        return node
    key = ref.removeprefix("#/components/schemas/")
    return openapi["components"]["schemas"][key]


def _result_schema_from_openapi(openapi: dict[str, Any]) -> dict[str, Any]:
    """Resolve the 200 JSON response schema for POST ``/test`` to a concrete object schema."""
    post = openapi["paths"]["/test"]["post"]
    schema = post["responses"]["200"]["content"]["application/json"]["schema"]
    return _resolve_ref(openapi, schema)


@pytest.fixture
def adapter_and_client() -> tuple[FastApiAdapter, TestClient, ActionProductMachine]:
    machine = ActionProductMachine()
    auth = AsyncMock()
    auth.process.return_value = None
    adapter = FastApiAdapter(machine=machine, auth_coordinator=auth)
    adapter.post("/test", AdapterTestAction)
    app = adapter.build()
    return adapter, TestClient(app), machine


def test_openapi_response_schema_contains_graph_field_schema(
    adapter_and_client: tuple[FastApiAdapter, TestClient, ActionProductMachine],
) -> None:
    _, client, _ = adapter_and_client
    openapi = client.app.openapi()
    result_schema = _result_schema_from_openapi(openapi)
    graph_schema = result_schema["properties"]["graph"]
    graph_resolved = _resolve_ref(openapi, graph_schema)
    assert graph_resolved.get("type") == "object"
    assert "nodes" in graph_resolved["properties"]
    assert "edges" in graph_resolved["properties"]
    assert graph_resolved.get("required") == ["nodes", "edges"]


def test_endpoint_returns_raw_graph_dict(
    adapter_and_client: tuple[FastApiAdapter, TestClient, ActionProductMachine],
) -> None:
    _, client, machine = adapter_and_client
    machine.run = AsyncMock(
        return_value=AdapterTestAction.Result(
            domain="Billing",
            graph={"nodes": [], "edges": []},
        ),
    )
    response = client.post("/test", json={"label": "Billing"})
    assert response.status_code == 200
    body = response.json()
    assert body["graph"] == {"nodes": [], "edges": []}
    assert isinstance(body["graph"], dict)


def test_openapi_domain_field_has_description(
    adapter_and_client: tuple[FastApiAdapter, TestClient, ActionProductMachine],
) -> None:
    _, client, _ = adapter_and_client
    openapi = client.app.openapi()
    result_schema = _result_schema_from_openapi(openapi)
    assert result_schema["properties"]["domain"].get("description") == "Domain name"
