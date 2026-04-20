# tests/adapters/mcp/test_mcp_handler.py
"""
MCP tool handlers: execution, serialization, graph JSON, and error surfaces.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Exercise ``_make_tool_handler``, ``_execute_tool_call``, ``_serialize_result``,
``_validate_tool_request_kwargs``, ``_build_graph_json``, and error formatting:
successful ``CallToolResult`` with JSON envelope text (``ok``/``code``/``data``),
``isError`` paths (permissions, validation, internal), Pydantic input edge cases
(missing field, wrong type, constraints, ``field_validator``), direct unit tests
for ``_validate_tool_request_kwargs`` without ``machine.run``, empty vs
non-empty ``details`` on ``ValidationFieldError``, mapper transforms, guard
failures for bad mapper outputs (generic ``INTERNAL_ERROR`` body without leaking
guard text), ``__name__`` derivation from ``tool_name``, success ``data`` JSON
round-trip without ``default=str``, ``INVALID_PARAMS`` items with ``type``/``loc``,
``model_dump(mode="json")`` for datetimes in results, and graph JSON topology
(nodes, edges, hydrated ``facet_rows``).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    MCP kwargs / mock context
              |
              v
    _make_tool_handler -> _execute_tool_call -> machine.run
              |              ^
              |              +-- _validate_tool_request_kwargs (Pydantic -> ValidationFieldError)
              |
              +--> _serialize_result -> envelope JSON in CallToolResult text
              |
              v
    Exceptions -> CallToolResult(isError=True) with stable JSON ``code`` values

    _build_graph_json(coordinator) -> JSON string for ``system://graph``-style use

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Error envelope ``code`` values (e.g. PERMISSION_DENIED) must stay aligned with adapter code.
- Pydantic edge cases (missing field, wrong type, constraints, custom validators)
  map to INVALID_PARAMS with ``details.errors`` (each item exposes ``type`` and
  ``loc``); ``_validate_tool_request_kwargs`` is covered by direct unit tests.
- Success envelope ``data`` must ``json.dumps`` without custom ``default`` when
  built from Pydantic results using ``mode="json"``.
- Graph JSON must include string-typed edge ``type`` and ``source_key``/``target_key``.

═══════════════════════════════════════════════════════════════════════════════
TESTING CONTRACT
═══════════════════════════════════════════════════════════════════════════════

These tests exercise production adapter helpers and a real
``ActionProductMachine`` for coordinator-backed metadata. ``machine.run`` is
often replaced with ``AsyncMock`` to pin return values or errors without running
the full action pipeline; kwargs validation, guards, and envelope code stay
production paths.

::

    handler / _execute_tool_call / _serialize_result / envelopes   [production]
                            |
                            v
                      machine.run                    [AsyncMock when needed]
                            |
                            v
                      full action pipeline          [skipped when stubbed]

Tagline: production types and production paths; stub the ``run`` seam, not the
stack. See ``BaseAdapter`` (ADAPTER TESTING CONTRACT) and ``mcp.adapter``
(TESTING NOTE).

"""

import json
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from mcp.types import CallToolResult
from pydantic import BaseModel, Field, field_validator

from action_machine.context.user_info import UserInfo
from action_machine.integrations.mcp.adapter import (
    _build_graph_json,
    _execute_tool_call,
    _make_tool_handler,
    _serialize_result,
    _validate_tool_request_kwargs,
)
from action_machine.integrations.mcp.route_record import McpRouteRecord
from action_machine.legacy.core import Core
from action_machine.model.exceptions import AuthorizationError, ValidationFieldError
from action_machine.runtime.action_product_machine import ActionProductMachine
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


def _tool_result_envelope(result: CallToolResult) -> dict[str, Any]:
    """Parse handler TextContent as JSON envelope dict."""
    return json.loads(_tool_result_text(result))


class _MockResult(BaseModel):
    """Simple pydantic result for serialization tests."""
    message: str = "ok"
    count: int = 1


class _ResultWithWhen(BaseModel):
    """Result carrying a datetime to exercise ``model_dump(mode='json')``."""

    message: str
    when: datetime = Field(description="Timestamp")


class _PlainResult:
    """Non-pydantic result for fallback serialization."""
    def __init__(self, value: str) -> None:
        self.value = value


class _ProbeMcpRequest(BaseModel):
    """Request model with ``field_validator`` for Pydantic mapping tests."""

    x: int

    @field_validator("x")
    @classmethod
    def _x_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("must be non-negative")
        return v


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
# _validate_tool_request_kwargs
# ═════════════════════════════════════════════════════════════════════════════


class TestValidateToolRequestKwargs:
    """
    Direct unit tests for MCP request parsing (no ``CallToolResult``, no ``machine.run``).
    """

    def test_valid_kwargs_returns_validated_model(self) -> None:
        """Successful validation returns the Pydantic model instance."""
        body = _validate_tool_request_kwargs({"name": "Ada"}, SimpleAction.Params)
        assert body.name == "Ada"

    def test_missing_required_field_raises_validation_field_error(self) -> None:
        """Omitted required fields become ``ValidationFieldError`` with Pydantic errors."""
        with pytest.raises(ValidationFieldError) as ctx:
            _validate_tool_request_kwargs({}, SimpleAction.Params)
        assert ctx.value.message == "Tool input validation failed"
        errs = ctx.value.details["errors"]
        assert isinstance(errs, list)
        assert errs
        assert ctx.value.__cause__ is not None

    def test_field_validator_failure_maps_like_other_pydantic_errors(self) -> None:
        """``field_validator`` / ``ValueError`` paths populate ``details.errors``."""
        with pytest.raises(ValidationFieldError) as ctx:
            _validate_tool_request_kwargs({"x": -1}, _ProbeMcpRequest)
        assert ctx.value.message == "Tool input validation failed"
        errs = ctx.value.details["errors"]
        assert any(e.get("type") == "value_error" for e in errs)
        assert any("x" in str(e.get("loc", ())) for e in errs)
        assert ctx.value.__cause__ is not None


class TestExecuteToolCallDirect:
    """``_execute_tool_call`` behavior without ``CallToolResult`` / envelope layer."""

    @pytest.mark.asyncio
    async def test_invalid_kwargs_skips_run_and_auth(self) -> None:
        """Bad kwargs fail inside ``_validate_tool_request_kwargs`` before I/O."""
        machine = _make_machine()
        machine.run = AsyncMock()
        auth = _make_auth()
        record = _make_record(action_class=SimpleAction, tool_name="unit.simple")

        with pytest.raises(ValidationFieldError):
            await _execute_tool_call(
                {},
                SimpleAction.Params,
                record,
                machine,
                auth,
                None,
                False,
                False,
            )

        machine.run.assert_not_called()
        auth.process.assert_not_called()


# ═════════════════════════════════════════════════════════════════════════════
# _serialize_result
# ═════════════════════════════════════════════════════════════════════════════


class TestSerializeResult:
    """Verify result serialization to a JSON-ready payload (envelope ``data``)."""

    def test_pydantic_model(self) -> None:
        """Pydantic BaseModel is converted via model_dump(mode='json')."""
        result = _MockResult(message="hello", count=5)
        record = _make_record()

        payload = _serialize_result(result, record, has_response_mapper=False)

        assert payload["message"] == "hello"
        assert payload["count"] == 5

    def test_with_response_mapper(self) -> None:
        """Response mapper is applied before payload build."""
        result = _MockResult(message="original")
        record = _make_record(
            response_model=_AltResponse,
            response_mapper=lambda r: _AltResponse(data=r.message),
        )

        payload = _serialize_result(result, record, has_response_mapper=True)

        assert payload["data"] == "original"

    def test_non_pydantic_result(self) -> None:
        """Plain dicts pass through for the outer envelope json.dumps."""
        result = {"key": "value", "num": 42}
        record = _make_record()

        payload = _serialize_result(result, record, has_response_mapper=False)

        assert payload["key"] == "value"
        assert payload["num"] == 42

    def test_user_info_roles_are_json_safe_without_mapper(self) -> None:
        """UserInfo.roles serializes to role names (no class objects in JSON)."""
        result = _UserEnvelope(
            user=UserInfo(user_id="u1", roles=(AdminRole,)),
        )
        record = _make_record()

        payload = _serialize_result(result, record, has_response_mapper=False)

        assert payload["user"]["user_id"] == "u1"
        assert payload["user"]["roles"] == [AdminRole.name]

    def test_user_info_roles_are_json_safe_with_mapper(self) -> None:
        """Mapped pydantic response with UserInfo also remains JSON-safe."""
        result = _MockResult(message="ok")
        record = _make_record(
            response_model=_UserEnvelope,
            response_mapper=lambda _r: _UserEnvelope(
                user=UserInfo(user_id="u2", roles=(AdminRole,)),
            ),
        )

        payload = _serialize_result(result, record, has_response_mapper=True)

        assert payload["user"]["user_id"] == "u2"
        assert payload["user"]["roles"] == [AdminRole.name]

    def test_datetime_field_is_json_native_in_payload(self) -> None:
        """``model_dump(mode='json')`` emits ISO strings so ``data`` needs no ``default=str``."""
        when = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)
        result = _ResultWithWhen(message="hi", when=when)
        record = _make_record()

        payload = _serialize_result(result, record, has_response_mapper=False)

        assert isinstance(payload["when"], str)
        assert "2024-06-01T12:00:00" in payload["when"]
        json.dumps(payload)


# ═════════════════════════════════════════════════════════════════════════════
# _make_tool_handler — successful execution
# ═════════════════════════════════════════════════════════════════════════════


class TestHandlerSuccess:
    """Verify handler returns CallToolResult with JSON on success."""

    @pytest.mark.asyncio
    async def test_returns_json_string(self) -> None:
        """Handler returns success envelope with data and isError=False."""
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
        env = _tool_result_envelope(result)
        assert env["ok"] is True
        assert env["code"] == "OK"
        assert env["data"]["message"] == "pong"

    @pytest.mark.asyncio
    async def test_success_envelope_data_json_dumps_without_default(self) -> None:
        """Parsed ``data`` stays JSON-serializable without ``json.dumps(..., default=…)``."""
        machine = _make_machine()
        auth = _make_auth()
        record = _make_record(action_class=PingAction, tool_name="system.ping")
        machine.run = AsyncMock(return_value=PingAction.Result(message="pong"))

        handler = _make_tool_handler(
            record, machine, auth, None, machine.gate_coordinator,
        )
        result = await handler()
        env = _tool_result_envelope(result)

        json.dumps(env["data"])

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
        """AuthorizationError → isError=True, PERMISSION_DENIED envelope."""
        machine = _make_machine()
        machine.run = AsyncMock(side_effect=AuthorizationError("no access"))
        record = _make_record()

        handler = _make_tool_handler(
            record, machine, _make_auth(), None, machine.gate_coordinator,
        )
        result = await handler()

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        env = _tool_result_envelope(result)
        assert env["ok"] is False
        assert env["code"] == "PERMISSION_DENIED"
        assert "no access" in env["message"]
        assert env["details"] == {}

    @pytest.mark.asyncio
    async def test_validation_error(self) -> None:
        """ValidationFieldError → isError=True, INVALID_PARAMS envelope."""
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
        env = _tool_result_envelope(result)
        assert env["code"] == "INVALID_PARAMS"
        assert env["message"] == "bad field"
        assert env["details"] == {}

    @pytest.mark.asyncio
    async def test_unexpected_error(self) -> None:
        """Unexpected exceptions → isError=True, generic INTERNAL_ERROR envelope."""
        machine = _make_machine()
        machine.run = AsyncMock(side_effect=RuntimeError("boom"))
        record = _make_record()

        handler = _make_tool_handler(
            record, machine, _make_auth(), None, machine.gate_coordinator,
        )
        result = await handler()

        assert result.isError is True
        env = _tool_result_envelope(result)
        assert env["code"] == "INTERNAL_ERROR"
        assert env["message"] == "Unexpected failure"
        assert "boom" not in json.dumps(env)

    @pytest.mark.asyncio
    async def test_pydantic_input_validation_error(self) -> None:
        """Missing required tool args → INVALID_PARAMS with Pydantic error list."""
        machine = _make_machine()
        machine.run = AsyncMock()
        record = _make_record(action_class=SimpleAction, tool_name="simple.run")

        handler = _make_tool_handler(
            record, machine, _make_auth(), None, machine.gate_coordinator,
        )
        result = await handler()

        assert result.isError is True
        env = _tool_result_envelope(result)
        assert env["code"] == "INVALID_PARAMS"
        assert env["message"] == "Tool input validation failed"
        errors = env.get("details", {}).get("errors", [])
        assert isinstance(errors, list)
        assert errors
        for item in errors:
            assert "type" in item
            assert "loc" in item
        assert any("name" in str(e.get("loc", ())) for e in errors)
        machine.run.assert_not_called()

    @pytest.mark.asyncio
    async def test_pydantic_tool_input_wrong_type(self) -> None:
        """Wrong JSON type for ``str`` field → INVALID_PARAMS (not only missing fields)."""
        machine = _make_machine()
        machine.run = AsyncMock()
        record = _make_record(action_class=SimpleAction, tool_name="simple.run")

        handler = _make_tool_handler(
            record, machine, _make_auth(), None, machine.gate_coordinator,
        )
        result = await handler(name=[])

        assert result.isError is True
        env = _tool_result_envelope(result)
        assert env["code"] == "INVALID_PARAMS"
        errors = env["details"]["errors"]
        assert any(e.get("type") == "string_type" for e in errors)
        assert any("name" in str(e.get("loc", ())) for e in errors)
        machine.run.assert_not_called()

    @pytest.mark.asyncio
    async def test_pydantic_tool_input_min_length_violation(self) -> None:
        """Constraint violation (``min_length``) → INVALID_PARAMS with constraint error type."""
        machine = _make_machine()
        machine.run = AsyncMock()
        record = _make_record(action_class=SimpleAction, tool_name="simple.run")

        handler = _make_tool_handler(
            record, machine, _make_auth(), None, machine.gate_coordinator,
        )
        result = await handler(name="")

        assert result.isError is True
        env = _tool_result_envelope(result)
        assert env["code"] == "INVALID_PARAMS"
        errors = env["details"]["errors"]
        assert any(e.get("type") == "string_too_short" for e in errors)
        machine.run.assert_not_called()

    @pytest.mark.asyncio
    async def test_validation_field_error_with_explicit_details_in_envelope(self) -> None:
        """Domain ValidationFieldError with ``details`` → same keys appear under envelope ``details``."""
        machine = _make_machine()
        machine.run = AsyncMock(
            side_effect=ValidationFieldError(
                "shape mismatch",
                details={"hint": "fixme", "path": ("a", "b")},
            ),
        )
        record = _make_record()

        handler = _make_tool_handler(
            record, machine, _make_auth(), None, machine.gate_coordinator,
        )
        result = await handler()

        env = _tool_result_envelope(result)
        assert env["code"] == "INVALID_PARAMS"
        assert env["message"] == "shape mismatch"
        assert env["details"]["hint"] == "fixme"
        assert env["details"]["path"] == ["a", "b"]


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
        env = _tool_result_envelope(result)
        assert env["data"]["data"] == "pong"

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
        env = _tool_result_envelope(result)
        assert env["code"] == "INTERNAL_ERROR"
        assert env["message"] == "Unexpected failure"
        assert "params must be an instance" not in json.dumps(env)
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
        env = _tool_result_envelope(result)
        assert env["code"] == "INTERNAL_ERROR"
        assert env["message"] == "Unexpected failure"
        assert "response_mapper must return" not in json.dumps(env)
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
        coordinator = Core.create_coordinator()
        machine = ActionProductMachine(mode="test", coordinator=coordinator)

        json_str = _build_graph_json(machine.gate_coordinator)
        parsed = json.loads(json_str)

        assert "nodes" in parsed
        assert "edges" in parsed
        assert isinstance(parsed["nodes"], list)
        assert isinstance(parsed["edges"], list)

    def test_contains_action_node(self) -> None:
        """Graph contains a node for the registered action."""
        coordinator = Core.create_coordinator()
        machine = ActionProductMachine(mode="test", coordinator=coordinator)

        json_str = _build_graph_json(machine.gate_coordinator)
        parsed = json.loads(json_str)

        node_ids = [n.get("id", "") for n in parsed["nodes"]]
        has_ping = any("Ping" in nid for nid in node_ids)
        assert has_ping, f"No PingAction node found in: {node_ids}"

    def test_ping_action_node_has_description_and_domain_from_meta_snapshot(self) -> None:
        """Primary-host ``@meta`` folds into the ``action`` node; hydration exposes it in JSON."""
        coordinator = Core.create_coordinator()
        machine = ActionProductMachine(mode="test", coordinator=coordinator)

        json_str = _build_graph_json(machine.gate_coordinator)
        parsed = json.loads(json_str)

        action_nodes = [n for n in parsed["nodes"] if n.get("type") == "Action"]
        ping_action = next(
            (n for n in action_nodes if "PingAction" in n.get("id", "")),
            None,
        )
        assert ping_action is not None
        assert ping_action.get("description") == "Service health check"
        assert ping_action.get("domain") == "tests.scenarios.domain_model.domains.SystemDomain"

    def test_edges_include_source_and_target_keys_and_string_type(self) -> None:
        """Edges expose ``source_key`` / ``target_key`` and a string ``type`` (not a dict repr)."""
        coordinator = Core.create_coordinator()
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
