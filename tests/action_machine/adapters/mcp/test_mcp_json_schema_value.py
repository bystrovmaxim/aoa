# tests/action_machine/adapters/mcp/test_mcp_json_schema_value.py
"""
MCP adapter behavior when action ``Result`` contains a ``JsonSchemaValue`` field.

PR-2: ``_mcp_argument_model`` assigns a unique dynamic ``McpArgs`` type name so
repeated ``build()`` / multiple machines do not collide in the Params graph;
``model_dump(mode=\"json\")`` still serializes ``graph`` as a plain dict.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from aoa.action_machine.context.context import Context
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.mcp.adapter import McpAdapter, _serialize_result
from aoa.mcp.route_record import McpRouteRecord
from tests.action_machine.adapters.json_schema_adapter_fixtures import AdapterTestAction


def _make_adapter() -> McpAdapter:
    machine = ActionProductMachine(loggers=[])
    auth = AsyncMock()
    auth.process.return_value = Context()
    return McpAdapter(machine=machine, auth_coordinator=auth)


@pytest.mark.asyncio
async def test_mcp_build_does_not_raise() -> None:
    adapter = _make_adapter()
    adapter.tool("adapter_test", AdapterTestAction)
    server = adapter.build()
    assert server is not None


@pytest.mark.asyncio
async def test_mcp_tool_input_schema_unchanged() -> None:
    """``inputSchema`` reflects Params only; Result ``JsonSchemaValue`` fields stay off input."""
    adapter = _make_adapter()
    adapter.tool("adapter_test", AdapterTestAction)
    server = adapter.build()
    tools = await server.list_tools()
    tool = next(t for t in tools if t.name == "adapter_test")
    props = (tool.inputSchema or {}).get("properties") or {}
    assert "label" in props
    assert "graph" not in props
    assert "domain" not in props


def test_mcp_serialize_result_raw_graph_dict() -> None:
    """``_serialize_result`` emits a plain dict for ``graph`` (no wrapper type)."""
    record = McpRouteRecord(action_class=AdapterTestAction, tool_name="adapter_test")
    graph = {"nodes": [], "edges": []}
    result = AdapterTestAction.Result(domain="Billing", graph=graph)
    payload = _serialize_result(result, record, has_response_mapper=False)
    assert payload["graph"] == graph
    assert isinstance(payload["graph"], dict)
    json.dumps(payload)


def test_second_machine_after_mcp_build_no_duplicate_graph_nodes() -> None:
    """Regression: dynamic MCP arg types must not reuse the same Params graph node id."""
    _make_adapter().tool("adapter_test_dup", AdapterTestAction).build()
    ActionProductMachine(loggers=[])
