# tests/adapters/mcp/test_mcp_handler.py
"""
MCP tool handlers: execution, serialization, graph JSON, and error surfaces.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Exercise ``_make_tool_handler``, ``_execute_tool_call``, ``_serialize_result``,
``_build_graph_json``, and error formatting: successful ``CallToolResult`` JSON,
``isError`` paths (permissions, validation, internal), mapper transforms, guard
failures for bad mapper outputs, ``__name__`` derivation from ``tool_name``, and
graph JSON topology (nodes, edges, hydrated meta).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    MCP kwargs / mock context
              |
              v
    _make_tool_handler -> _execute_tool_call -> machine.run
              |
              +--> _serialize_result -> CallToolResult (text JSON)
              |
              v
    Exceptions -> CallToolResult(isError=True) with stable prefixes

    _build_graph_json(coordinator) -> JSON string for ``system://graph``-style use

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Error text prefixes (e.g. PERMISSION_DENIED) must stay aligned with adapter code.
- Graph JSON must include string-typed edge ``type`` and ``source_key``/``target_key``.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    uv run pytest tests/adapters/mcp/test_mcp_handler.py -q

Edge case: wrong ``params_mapper`` return type surfaces as internal error with
guard message substring.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Line-number references to ``adapter.py`` in historical comments drift on edits;
  behavior is what these tests lock, not exact source lines.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: MCP handler and graph JSON regression tests.
CONTRACT: CallToolResult shape; exception mapping; serialization and graph keys.
INVARIANTS: Mocks for machine/auth; scenario actions + ``AdminRole`` where needed.
═══════════════════════════════════════════════════════════════════════════════
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
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
from action_machine.intents.context.user_info import UserInfo
from action_machine.model.exceptions import AuthorizationError, ValidationFieldError
from action_machine.runtime.machines.action_product_machine import ActionProductMachine
from action_machine.runtime.machines.core_action_machine import CoreActionMachine
from tests.scenarios.domain_model import PingAction, SimpleAction
from tests.scenarios.domain_model.roles import AdminRole

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


class _UserEnvelope(BaseModel):
    """Envelope with UserInfo payload for JSON serialization tests."""

    user: UserInfo


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

    def test_user_info_roles_are_json_safe_without_mapper(self) -> None:
        """UserInfo.roles serializes to role names (no class objects in JSON)."""
        result = _UserEnvelope(
            user=UserInfo(user_id="u1", roles=(AdminRole,)),
        )
        record = _make_record()

        json_str = _serialize_result(result, record, has_response_mapper=False)
        parsed = json.loads(json_str)

        assert parsed["user"]["user_id"] == "u1"
        assert parsed["user"]["roles"] == [AdminRole.name]

    def test_user_info_roles_are_json_safe_with_mapper(self) -> None:
        """Mapped pydantic response with UserInfo also remains JSON-safe."""
        result = _MockResult(message="ok")
        record = _make_record(
            response_model=_UserEnvelope,
            response_mapper=lambda _r: _UserEnvelope(
                user=UserInfo(user_id="u2", roles=(AdminRole,)),
            ),
        )

        json_str = _serialize_result(result, record, has_response_mapper=True)
        parsed = json.loads(json_str)

        assert parsed["user"]["user_id"] == "u2"
        assert parsed["user"]["roles"] == [AdminRole.name]


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
        """After skeleton nodes, graph JSON carries description/domain from hydration."""
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
        assert ping_meta.get("domain") == "tests.scenarios.domain_model.domains.SystemDomain"

    def test_edges_include_source_and_target_keys_and_string_type(self) -> None:
        """Edges expose ``source_key`` / ``target_key`` and a string ``type`` (not a dict repr)."""
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
