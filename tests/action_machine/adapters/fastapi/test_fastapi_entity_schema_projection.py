# tests/action_machine/adapters/fastapi/test_fastapi_entity_schema_projection.py
"""
FastAPI adapter + OpenAPI for ``BaseResult`` fields using ``BaseEntity.schema(...)``.

PR-2: Pydantic hooks on ``EntitySchemaMarker`` supply field JSON Schema; adapter
code stays unchanged.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from aoa.action_machine.adapters.fastapi.adapter import FastApiAdapter
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from tests.action_machine.adapters.entity_projection_adapter_fixtures import (
    EntityProjectionAdapterTestAction,
)


def _resolve_ref(openapi: dict[str, Any], node: dict[str, Any]) -> dict[str, Any]:
    ref = node.get("$ref")
    if not isinstance(ref, str) or not ref.startswith("#/components/schemas/"):
        return node
    key = ref.removeprefix("#/components/schemas/")
    return openapi["components"]["schemas"][key]


def _result_schema_from_openapi(openapi: dict[str, Any]) -> dict[str, Any]:
    post = openapi["paths"]["/test"]["post"]
    schema = post["responses"]["200"]["content"]["application/json"]["schema"]
    return _resolve_ref(openapi, schema)


@pytest.fixture
def adapter_and_client() -> tuple[FastApiAdapter, TestClient, ActionProductMachine]:
    machine = ActionProductMachine()
    auth = AsyncMock()
    auth.process.return_value = None
    adapter = FastApiAdapter(machine=machine, auth_coordinator=auth)
    adapter.post("/test", EntityProjectionAdapterTestAction)
    app = adapter.build()
    return adapter, TestClient(app), machine


def test_openapi_builds_without_error(
    adapter_and_client: tuple[FastApiAdapter, TestClient, ActionProductMachine],
) -> None:
    _, client, _ = adapter_and_client
    openapi = client.app.openapi()
    assert "paths" in openapi


def test_openapi_order_field_matches_inline_projection_schema(
    adapter_and_client: tuple[FastApiAdapter, TestClient, ActionProductMachine],
) -> None:
    _, client, _ = adapter_and_client
    openapi = client.app.openapi()
    result_schema = _result_schema_from_openapi(openapi)
    order_schema = _resolve_ref(openapi, result_schema["properties"]["order"])
    assert order_schema.get("type") == "object"
    assert set(order_schema.get("required", [])) == {"id", "name"}
    assert order_schema["properties"]["id"] == {"type": "string"}
    assert order_schema["properties"]["name"] == {"type": "string"}
    assert order_schema.get("additionalProperties") is False


def test_endpoint_returns_raw_order_dict(
    adapter_and_client: tuple[FastApiAdapter, TestClient, ActionProductMachine],
) -> None:
    _, client, machine = adapter_and_client
    order = {"id": "e1", "name": "One"}
    machine.run = AsyncMock(
        return_value=EntityProjectionAdapterTestAction.Result(domain="Billing", order=order),
    )
    response = client.post("/test", json={"label": "Billing"})
    assert response.status_code == 200
    body = response.json()
    assert body["order"] == order
    assert isinstance(body["order"], dict)
