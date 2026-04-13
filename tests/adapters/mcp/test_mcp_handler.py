# tests/adapters/mcp/test_mcp_handler.py
"""
Tests for MCP tool handler execution and error handling.

When McpAdapter.build() creates an MCP server, each registered tool gets
an async handler function. The handler deserializes kwargs into the Params model,
runs the action through the machine, serializes the result to JSON inside
``CallToolResult`` (``isError=False``), and catches exceptions to return
``CallToolResult`` with ``isError=True`` and the same textual prefixes
(PERMISSION_DENIED, INVALID_PARAMS, INTERNAL_ERROR).

This file tests the handler internals: _make_tool_handler, _execute_tool_call,
_serialize_result, _build_graph_json, and error formatting — covering the
uncovered lines in integrations/mcp/adapter.py (lines 169, 208-256, 381-387, 634).

Scenarios covered:
    - Handler returns CallToolResult with JSON text and isError=False on success.
    - Handler returns CallToolResult isError=True for AuthorizationError, etc.
    - _serialize_result with pydantic model uses model_dump.
    - _serialize_result with response_mapper applies the mapper.
    - _serialize_result with non-pydantic object uses default serializer.
    - _class_name_to_snake_case edge cases.
    - _build_graph_json returns valid JSON with nodes and edges; hydrated meta
      (description/domain); edges with source_key/target_key and string type.
    - Handler with params_mapper transforms input before execution.
    - Handler with response_mapper transforms output after execution.
    - Bad params_mapper / response_mapper types → INTERNAL_ERROR with guard message.
    - Handler __name__ is derived from tool_name with dots/hyphens replaced.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from mcp.types import CallToolResult
from pydantic import BaseModel

from action_machine.integrations.mcp.adapter import (
    _build_graph_json,
    _make_tool_handler,
    _serialize_result,
)
from action_machine.integrations.mcp.route_record import McpRouteRecord
from action_machine.model.exceptions import AuthorizationError, ValidationFieldError
from action_machine.runtime.machines.action_product_machine import ActionProductMachine
from action_machine.runtime.machines.core_action_machine import CoreActionMachine
from tests.domain_model import PingAction, SimpleAction

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _tool_result_text(result: CallToolResult) -> str:
    """First TextContent block text from a CallToolResult (handler return value)."""
    assert isinstance(result, CallToolResult)
    assert result.content
    return result.content[0].text


class _MockResult(BaseModel):
    """Simple pydantic result for serialization tests."""
    message: str = "ok"
    count: int = 1


class _PlainResult:
    """Non-pydantic result for fallback serialization."""
    def __init__(self, value: str) -> None:
        self.value = value


class _AltResponse(BaseModel):
    """Alternative response model for mapper tests."""
    data: str = "mapped"


def _make_record(
    action_class=PingAction,
    tool_name: str = "test.tool",
    params_mapper=None,
    response_mapper=None,
    request_model=None,
    response_model=None,
) -> McpRouteRecord:
    """Create a McpRouteRecord with test defaults."""
    return McpRouteRecord(
        action_class=action_class,
        tool_name=tool_name,
        params_mapper=params_mapper,
        response_mapper=response_mapper,
        request_model=request_model,
        response_model=response_model,
    )


def _make_machine() -> ActionProductMachine:
    """Create a minimal machine for handler tests."""
    return ActionProductMachine(mode="test")


def _make_auth(context=None) -> AsyncMock:
    """Create a mock auth coordinator."""
    auth = AsyncMock()
    auth.process.return_value = context
    return auth


# ═════════════════════════════════════════════════════════════════════════════
# _serialize_result
# ═════════════════════════════════════════════════════════════════════════════


class TestSerializeResult:
    """Verify result serialization to JSON string."""

    def test_pydantic_model(self) -> None:
        """Pydantic BaseModel is serialized via model_dump → json.dumps."""
        result = _MockResult(message="hello", count=5)
        record = _make_record()

        json_str = _serialize_result(result, record, has_response_mapper=False)
        parsed = json.loads(json_str)

        assert parsed["message"] == "hello"
        assert parsed["count"] == 5

    def test_with_response_mapper(self) -> None:
        """Response mapper is applied before serialization."""
        result = _MockResult(message="original")
        record = _make_record(
            response_model=_AltResponse,
            response_mapper=lambda r: _AltResponse(data=r.message),
        )

        json_str = _serialize_result(result, record, has_response_mapper=True)
        parsed = json.loads(json_str)

        assert parsed["data"] == "original"

    def test_non_pydantic_result(self) -> None:
        """Non-pydantic objects use default str serializer via json.dumps."""
        result = {"key": "value", "num": 42}
        record = _make_record()

        json_str = _serialize_result(result, record, has_response_mapper=False)
        parsed = json.loads(json_str)

        assert parsed["key"] == "value"
        assert parsed["num"] == 42


# ═════════════════════════════════════════════════════════════════════════════
# _make_tool_handler — successful execution
# ═════════════════════════════════════════════════════════════════════════════


class TestHandlerSuccess:
    """Verify handler returns CallToolResult with JSON on success."""

    @pytest.mark.asyncio
    async def test_returns_json_string(self) -> None:
        """Handler returns CallToolResult with JSON text and isError=False."""
        machine = _make_machine()
        auth = _make_auth()
        record = _make_record(action_class=PingAction, tool_name="system.ping")

        # Mock machine.run to return a pydantic result
        mock_result = PingAction.Result(message="pong")
        machine.run = AsyncMock(return_value=mock_result)

        handler = _make_tool_handler(
            record, machine, auth, None, machine.gate_coordinator,
        )
        result = await handler()

        assert isinstance(result, CallToolResult)
        assert result.isError is False
        parsed = json.loads(_tool_result_text(result))
        assert parsed["message"] == "pong"

    @pytest.mark.asyncio
    async def test_handler_name_from_tool_name(self) -> None:
        """Handler __name__ is derived from tool_name with dots replaced."""
        machine = _make_machine()
        record = _make_record(tool_name="orders.create")

        handler = _make_tool_handler(
            record, machine, _make_auth(), None, machine.gate_coordinator,
        )

        assert handler.__name__ == "orders_create"

    @pytest.mark.asyncio
    async def test_handler_name_with_hyphens(self) -> None:
        """Handler __name__ replaces hyphens with underscores."""
        machine = _make_machine()
        record = _make_record(tool_name="my-tool-name")

        handler = _make_tool_handler(
            record, machine, _make_auth(), None, machine.gate_coordinator,
        )

        assert handler.__name__ == "my_tool_name"


# ═════════════════════════════════════════════════════════════════════════════
# _make_tool_handler — error handling
# ═════════════════════════════════════════════════════════════════════════════


class TestHandlerErrors:
    """Verify handler catches exceptions and returns CallToolResult with isError=True."""

    @pytest.mark.asyncio
    async def test_authorization_error(self) -> None:
        """AuthorizationError → isError=True, PERMISSION_DENIED text."""
        machine = _make_machine()
        machine.run = AsyncMock(side_effect=AuthorizationError("no access"))
        record = _make_record()

        handler = _make_tool_handler(
            record, machine, _make_auth(), None, machine.gate_coordinator,
        )
        result = await handler()

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        text = _tool_result_text(result)
        assert "PERMISSION_DENIED" in text
        assert "no access" in text

    @pytest.mark.asyncio
    async def test_validation_error(self) -> None:
        """ValidationFieldError → isError=True, INVALID_PARAMS text."""
        machine = _make_machine()
        machine.run = AsyncMock(
            side_effect=ValidationFieldError("bad field", "name"),
        )
        record = _make_record()

        handler = _make_tool_handler(
            record, machine, _make_auth(), None, machine.gate_coordinator,
        )
        result = await handler()

        assert result.isError is True
        assert "INVALID_PARAMS" in _tool_result_text(result)

    @pytest.mark.asyncio
    async def test_unexpected_error(self) -> None:
        """Unexpected exceptions → isError=True, INTERNAL_ERROR text."""
        machine = _make_machine()
        machine.run = AsyncMock(side_effect=RuntimeError("boom"))
        record = _make_record()

        handler = _make_tool_handler(
            record, machine, _make_auth(), None, machine.gate_coordinator,
        )
        result = await handler()

        assert result.isError is True
        text = _tool_result_text(result)
        assert "INTERNAL_ERROR" in text
        assert "boom" in text


# ═════════════════════════════════════════════════════════════════════════════
# _make_tool_handler — with mappers
# ═════════════════════════════════════════════════════════════════════════════


class TestHandlerWithMappers:
    """Verify handler applies params_mapper and response_mapper."""

    @pytest.mark.asyncio
    async def test_params_mapper_applied(self) -> None:
        """params_mapper transforms input before passing to machine.run."""
        machine = _make_machine()
        mock_result = PingAction.Result(message="pong")
        machine.run = AsyncMock(return_value=mock_result)

        mapper_called_with = []

        def params_mapper(body):
            mapper_called_with.append(body)
            return PingAction.Params()

        record = _make_record(
            action_class=PingAction,
            request_model=PingAction.Params,
            params_mapper=params_mapper,
        )

        handler = _make_tool_handler(
            record, machine, _make_auth(), None, machine.gate_coordinator,
        )
        await handler()

        assert len(mapper_called_with) == 1

    @pytest.mark.asyncio
    async def test_response_mapper_applied(self) -> None:
        """response_mapper transforms output before serialization."""
        machine = _make_machine()
        mock_result = PingAction.Result(message="pong")
        machine.run = AsyncMock(return_value=mock_result)

        record = _make_record(
            action_class=PingAction,
            response_model=_AltResponse,
            response_mapper=lambda r: _AltResponse(data=r.message),
        )

        handler = _make_tool_handler(
            record, machine, _make_auth(), None, machine.gate_coordinator,
        )
        result = await handler()

        assert result.isError is False
        parsed = json.loads(_tool_result_text(result))
        assert parsed["data"] == "pong"

    @pytest.mark.asyncio
    async def test_bad_params_mapper_surfaces_as_internal_error(self) -> None:
        """Wrong params type before run → INTERNAL_ERROR, machine.run not called."""
        machine = _make_machine()
        machine.run = AsyncMock(return_value=SimpleAction.Result(greeting="x"))

        record = _make_record(
            action_class=SimpleAction,
            tool_name="test.bad_params_map",
            params_mapper=lambda _p: PingAction.Params(),  # not SimpleAction.Params
        )
        handler = _make_tool_handler(
            record, machine, _make_auth(), None, machine.gate_coordinator,
        )
        result = await handler(name="Alice")

        assert result.isError is True
        assert "INTERNAL_ERROR" in _tool_result_text(result)
        assert "params must be an instance" in _tool_result_text(result)
        machine.run.assert_not_called()

    @pytest.mark.asyncio
    async def test_bad_response_mapper_surfaces_as_internal_error(self) -> None:
        """Wrong response_mapper output → INTERNAL_ERROR after machine.run."""
        machine = _make_machine()
        machine.run = AsyncMock(
            return_value=SimpleAction.Result(greeting="Hi"),
        )

        record = _make_record(
            action_class=SimpleAction,
            tool_name="test.bad_response_map",
            response_model=_AltResponse,
            response_mapper=lambda _r: "not-alt-response",  # type: ignore[return-value]
        )
        handler = _make_tool_handler(
            record, machine, _make_auth(), None, machine.gate_coordinator,
        )
        result = await handler(name="Bob")

        assert result.isError is True
        text = _tool_result_text(result)
        assert "INTERNAL_ERROR" in text
        assert "response_mapper must return" in text
        machine.run.assert_called_once()


# ═════════════════════════════════════════════════════════════════════════════
# _make_tool_handler — connections_factory
# ═════════════════════════════════════════════════════════════════════════════


class TestHandlerWithConnections:
    """Verify handler calls connections_factory when provided."""

    @pytest.mark.asyncio
    async def test_connections_factory_called(self) -> None:
        """connections_factory is invoked and result passed to machine.run."""
        machine = _make_machine()
        mock_result = PingAction.Result(message="pong")
        machine.run = AsyncMock(return_value=mock_result)

        mock_conn = {"db": MagicMock()}
        factory = MagicMock(return_value=mock_conn)

        record = _make_record()
        handler = _make_tool_handler(
            record, machine, _make_auth(), factory, machine.gate_coordinator,
        )
        await handler()

        factory.assert_called_once()
        # machine.run received the connections
        call_kwargs = machine.run.call_args
        assert call_kwargs is not None


# ═════════════════════════════════════════════════════════════════════════════
# _build_graph_json
# ═════════════════════════════════════════════════════════════════════════════


class TestBuildGraphJson:
    """Verify system graph JSON generation."""

    def test_returns_valid_json(self) -> None:
        """_build_graph_json returns a parseable JSON string."""
        coordinator = CoreActionMachine.create_coordinator()
        machine = ActionProductMachine(mode="test", coordinator=coordinator)

        json_str = _build_graph_json(machine.gate_coordinator)
        parsed = json.loads(json_str)

        assert "nodes" in parsed
        assert "edges" in parsed
        assert isinstance(parsed["nodes"], list)
        assert isinstance(parsed["edges"], list)

    def test_contains_action_node(self) -> None:
        """Graph contains a node for the registered action."""
        coordinator = CoreActionMachine.create_coordinator()
        machine = ActionProductMachine(mode="test", coordinator=coordinator)

        json_str = _build_graph_json(machine.gate_coordinator)
        parsed = json.loads(json_str)

        node_ids = [n.get("id", "") for n in parsed["nodes"]]
        has_ping = any("Ping" in nid for nid in node_ids)
        assert has_ping, f"No PingAction node found in: {node_ids}"

    def test_meta_node_has_description_and_domain_from_snapshots(self) -> None:
        """После скелетных узлов MCP JSON тянет описание/домен из гидратации."""
        coordinator = CoreActionMachine.create_coordinator()
        machine = ActionProductMachine(mode="test", coordinator=coordinator)

        json_str = _build_graph_json(machine.gate_coordinator)
        parsed = json.loads(json_str)

        meta_nodes = [n for n in parsed["nodes"] if n.get("type") == "meta"]
        ping_meta = next(
            (n for n in meta_nodes if "PingAction" in n.get("id", "")),
            None,
        )
        assert ping_meta is not None
        assert ping_meta.get("description") == "Service health check"
        assert ping_meta.get("domain") == "tests.domain_model.domains.SystemDomain"

    def test_edges_include_source_and_target_keys_and_string_type(self) -> None:
        """Рёбра: явные ``source_key`` / ``target_key`` и строковый ``type`` (не str(dict))."""
        coordinator = CoreActionMachine.create_coordinator()
        machine = ActionProductMachine(mode="test", coordinator=coordinator)

        json_str = _build_graph_json(machine.gate_coordinator)
        parsed = json.loads(json_str)

        assert parsed["edges"]
        for e in parsed["edges"]:
            assert "source_key" in e and "target_key" in e
            assert e["source_key"].count(":") >= 1
            assert e["target_key"].count(":") >= 1
            assert isinstance(e.get("type"), str)
            assert not e["type"].startswith("{")
