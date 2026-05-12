# tests/action_machine/resources/test_resolve_connections.py
"""Tests for ``PerCallConnection``, ``validate_connection_entries``, ``resolve_connections``."""

import pytest

from aoa.action_machine.resources.per_call_connection import (
    PerCallConnection,
    resolve_connections,
    validate_connection_entries,
)
from tests.action_machine.resources.test_connections_dict import DummyResourceManager


def test_resolve_connections_none() -> None:
    assert resolve_connections(None) is None


def test_resolve_connections_empty_dict() -> None:
    assert resolve_connections({}) is None


def test_resolve_connections_ready_resource() -> None:
    res = DummyResourceManager()
    out = resolve_connections({"svc": res})
    assert out == {"svc": res}


def test_resolve_connections_per_call_invokes_factory_each_time() -> None:
    res = DummyResourceManager()
    calls: list[int] = []

    def factory() -> DummyResourceManager:
        calls.append(1)
        return res

    spec = {"svc": PerCallConnection(factory)}
    resolve_connections(spec)
    resolve_connections(spec)
    assert calls == [1, 1]


def test_validate_connection_entries_rejects_bad_key() -> None:
    res = DummyResourceManager()
    with pytest.raises(TypeError, match="non-empty string"):
        validate_connection_entries({"": res})


def test_validate_connection_entries_rejects_bad_value() -> None:
    with pytest.raises(TypeError, match="BaseResource or PerCallConnection"):
        validate_connection_entries({"svc": "not-a-resource"})  # type: ignore[arg-type]


def test_resolve_connections_factory_must_return_base_resource() -> None:
    with pytest.raises(TypeError, match="must return BaseResource"):
        resolve_connections({"svc": PerCallConnection(lambda: "bad")})  # type: ignore[arg-type,return-value]


def test_mcp_route_record_accepts_connections_field() -> None:
    from aoa.action_machine.integrations.mcp.route_record import McpRouteRecord
    from tests.action_machine.scenarios.domain_model import PingAction

    res = DummyResourceManager()
    record = McpRouteRecord(
        action_class=PingAction,
        tool_name="system.ping",
        connections={"db": res},
    )
    assert record.connections == {"db": res}


def test_fastapi_route_record_accepts_connections_field() -> None:
    from aoa.action_machine.integrations.fastapi.route_record import FastApiRouteRecord
    from tests.action_machine.scenarios.domain_model import PingAction

    res = DummyResourceManager()
    record = FastApiRouteRecord(
        action_class=PingAction,
        path="/ping",
        connections={"svc": res},
    )
    assert record.connections == {"svc": res}


def test_validate_connection_entries_rejects_non_callable_factory() -> None:
    bad = PerCallConnection(factory=123)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="callable"):
        validate_connection_entries({"svc": bad})
