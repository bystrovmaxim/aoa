# tests/action_machine/adapters/mcp/test_mcp_entity_schema_projection.py
"""
MCP adapter behavior for ``BaseEntity.schema(...)`` on ``Result`` and ``Params``.

PR-2/PR-3: ``inputSchema`` comes from Pydantic ``model_json_schema`` only; entity
wire fields emit plain JSON Schema objects; serialization stays JSON-safe.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock

import pytest

from aoa.action_machine.adapters.mcp.adapter import McpAdapter, _serialize_result
from aoa.action_machine.adapters.mcp.route_record import McpRouteRecord
from aoa.action_machine.context.context import Context
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from tests.action_machine.adapters.entity_projection_adapter_fixtures import (
    EntityProjectionAdapterTestAction,
    EntityProjectionParamsMcpTestAction,
)


def _make_adapter() -> McpAdapter:
    machine = ActionProductMachine(loggers=[])
    auth = AsyncMock()
    auth.process.return_value = Context()
    return McpAdapter(machine=machine, auth_coordinator=auth)


def _assert_json_value_tree(obj: Any) -> None:
    """Fail on types that cannot appear in a strict JSON document (no ``default=str``)."""
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return
    if isinstance(obj, list):
        for item in obj:
            _assert_json_value_tree(item)
        return
    if isinstance(obj, dict):
        for key, val in obj.items():
            assert isinstance(key, str)
            _assert_json_value_tree(val)
        return
    raise AssertionError(f"Non-JSON value type in MCP schema tree: {type(obj)!r}")


@pytest.mark.asyncio
async def test_mcp_build_does_not_raise() -> None:
    adapter = _make_adapter()
    adapter.tool("entity_projection_adapter_test", EntityProjectionAdapterTestAction)
    server = adapter.build()
    assert server is not None


@pytest.mark.asyncio
async def test_mcp_tool_input_schema_unchanged() -> None:
    adapter = _make_adapter()
    adapter.tool("entity_projection_adapter_test", EntityProjectionAdapterTestAction)
    server = adapter.build()
    tools = await server.list_tools()
    tool = next(t for t in tools if t.name == "entity_projection_adapter_test")
    props = (tool.inputSchema or {}).get("properties") or {}
    assert "label" in props
    assert "order" not in props
    assert "domain" not in props


@pytest.mark.asyncio
async def test_mcp_params_entity_projection_input_schema() -> None:
    adapter = _make_adapter()
    adapter.tool("entity_projection_params_mcp", EntityProjectionParamsMcpTestAction)
    server = adapter.build()
    tools = await server.list_tools()
    tool = next(t for t in tools if t.name == "entity_projection_params_mcp")
    schema = tool.inputSchema or {}
    props = schema.get("properties") or {}
    assert "label" in props
    assert "order" in props
    order_prop = props["order"]
    assert order_prop.get("type") == "object"
    assert set(order_prop.get("required", [])) == {"id", "name"}
    assert order_prop["properties"]["id"] == {"type": "string"}
    assert order_prop["properties"]["name"] == {"type": "string"}
    assert order_prop.get("additionalProperties") is False
    json.dumps(schema, ensure_ascii=False)


@pytest.mark.asyncio
async def test_mcp_input_schemas_strict_json_value_trees() -> None:
    adapter = _make_adapter()
    adapter.tool("entity_projection_adapter_test", EntityProjectionAdapterTestAction)
    adapter.tool("entity_projection_params_mcp", EntityProjectionParamsMcpTestAction)
    server = adapter.build()
    for tool in await server.list_tools():
        inp = tool.inputSchema
        _assert_json_value_tree(inp)
        json.dumps(inp, ensure_ascii=False)


@pytest.mark.asyncio
async def test_mcp_input_schema_dump_has_no_python_marker_tokens() -> None:
    adapter = _make_adapter()
    adapter.tool("entity_projection_params_mcp", EntityProjectionParamsMcpTestAction)
    adapter.tool("entity_projection_adapter_test", EntityProjectionAdapterTestAction)
    server = adapter.build()
    blob = json.dumps([t.inputSchema for t in await server.list_tools()], ensure_ascii=False)
    assert "EntitySchemaMarker" not in blob
    assert "entity_schema_marker" not in blob


def test_mcp_serialize_result_raw_order_dict() -> None:
    record = McpRouteRecord(
        action_class=EntityProjectionAdapterTestAction,
        tool_name="entity_projection_adapter_test",
    )
    order = {"id": "e1", "name": "One"}
    result = EntityProjectionAdapterTestAction.Result(domain="Billing", order=order)
    payload = _serialize_result(result, record, has_response_mapper=False)
    assert payload["order"] == order
    assert isinstance(payload["order"], dict)
    json.dumps(payload)
