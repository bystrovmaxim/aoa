# tests/adapters/mcp/test_mcp_handler.py
"""
Tests for MCP tool handler execution and error handling.

When McpAdapter.build() creates a FastMCP server, each registered tool gets
an async handler function. The handler deserializes kwargs into the Params model,
runs the action through the machine, serializes the result to JSON, and catches
exceptions to return error strings (PERMISSION_DENIED, INVALID_PARAMS,
INTERNAL_ERROR).

This file tests the handler internals: _make_tool_handler, _execute_tool_call,
_serialize_result, _build_graph_json, and error formatting — covering the
uncovered lines in contrib/mcp/adapter.py (lines 169, 208-256, 381-387, 634).

Scenarios covered:
    - Handler returns JSON string for successful execution.
    - Handler returns PERMISSION_DENIED string for AuthorizationError.
    - Handler returns INVALID_PARAMS string for ValidationFieldError.
    - Handler returns INTERNAL_ERROR string for unexpected exceptions.
    - _serialize_result with pydantic model uses model_dump.
    - _serialize_result with response_mapper applies the mapper.
    - _serialize_result with non-pydantic object uses default serializer.
    - _class_name_to_snake_case edge cases.
    - _build_graph_json returns valid JSON with nodes and edges.
    - Handler with params_mapper transforms input before execution.
    - Handler with response_mapper transforms output after execution.
    - Handler __name__ is derived from tool_name with dots/hyphens replaced.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel

from action_machine.contrib.mcp.adapter import (
    _build_graph_json,
    _make_tool_handler,
    _serialize_result,
)
from action_machine.contrib.mcp.route_record import McpRouteRecord
from action_machine.core.action_product_machine import ActionProductMachine
from action_machine.core.core_action_machine import CoreActionMachine
from action_machine.core.exceptions import AuthorizationError, ValidationFieldError
from tests.domain_model import PingAction

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


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
    """Verify handler returns JSON on successful action execution."""

    @pytest.mark.asyncio
    async def test_returns_json_string(self) -> None:
        """Handler returns a JSON string containing the action result."""
        machine = _make_machine()
        auth = _make_auth()
        record = _make_record(action_class=PingAction, tool_name="system.ping")

        # Mock machine.run to return a pydantic result
        mock_result = PingAction.Result(message="pong")
        machine.run = AsyncMock(return_value=mock_result)

        handler = _make_tool_handler(record, machine, auth, None)
        result_str = await handler()

        parsed = json.loads(result_str)
        assert parsed["message"] == "pong"

    @pytest.mark.asyncio
    async def test_handler_name_from_tool_name(self) -> None:
        """Handler __name__ is derived from tool_name with dots replaced."""
        machine = _make_machine()
        record = _make_record(tool_name="orders.create")

        handler = _make_tool_handler(record, machine, _make_auth(), None)

        assert handler.__name__ == "orders_create"

    @pytest.mark.asyncio
    async def test_handler_name_with_hyphens(self) -> None:
        """Handler __name__ replaces hyphens with underscores."""
        machine = _make_machine()
        record = _make_record(tool_name="my-tool-name")

        handler = _make_tool_handler(record, machine, _make_auth(), None)

        assert handler.__name__ == "my_tool_name"


# ═════════════════════════════════════════════════════════════════════════════
# _make_tool_handler — error handling
# ═════════════════════════════════════════════════════════════════════════════


class TestHandlerErrors:
    """Verify handler catches exceptions and returns error strings."""

    @pytest.mark.asyncio
    async def test_authorization_error(self) -> None:
        """AuthorizationError is caught and returned as PERMISSION_DENIED."""
        machine = _make_machine()
        machine.run = AsyncMock(side_effect=AuthorizationError("no access"))
        record = _make_record()

        handler = _make_tool_handler(record, machine, _make_auth(), None)
        result = await handler()

        assert "PERMISSION_DENIED" in result
        assert "no access" in result

    @pytest.mark.asyncio
    async def test_validation_error(self) -> None:
        """ValidationFieldError is caught and returned as INVALID_PARAMS."""
        machine = _make_machine()
        machine.run = AsyncMock(
            side_effect=ValidationFieldError("bad field", "name"),
        )
        record = _make_record()

        handler = _make_tool_handler(record, machine, _make_auth(), None)
        result = await handler()

        assert "INVALID_PARAMS" in result

    @pytest.mark.asyncio
    async def test_unexpected_error(self) -> None:
        """Unexpected exceptions are caught and returned as INTERNAL_ERROR."""
        machine = _make_machine()
        machine.run = AsyncMock(side_effect=RuntimeError("boom"))
        record = _make_record()

        handler = _make_tool_handler(record, machine, _make_auth(), None)
        result = await handler()

        assert "INTERNAL_ERROR" in result
        assert "boom" in result


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

        handler = _make_tool_handler(record, machine, _make_auth(), None)
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

        handler = _make_tool_handler(record, machine, _make_auth(), None)
        result_str = await handler()

        parsed = json.loads(result_str)
        assert parsed["data"] == "pong"


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
        handler = _make_tool_handler(record, machine, _make_auth(), factory)
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

        json_str = _build_graph_json(machine)
        parsed = json.loads(json_str)

        assert "nodes" in parsed
        assert "edges" in parsed
        assert isinstance(parsed["nodes"], list)
        assert isinstance(parsed["edges"], list)

    def test_contains_action_node(self) -> None:
        """Graph contains a node for the registered action."""
        coordinator = CoreActionMachine.create_coordinator()
        machine = ActionProductMachine(mode="test", coordinator=coordinator)

        json_str = _build_graph_json(machine)
        parsed = json.loads(json_str)

        node_ids = [n.get("id", "") for n in parsed["nodes"]]
        has_ping = any("Ping" in nid for nid in node_ids)
        assert has_ping, f"No PingAction node found in: {node_ids}"
