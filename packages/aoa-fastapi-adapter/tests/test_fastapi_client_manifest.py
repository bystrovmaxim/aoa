"""
Integration tests for ``GET /client-manifest.json`` — the endpoint catalog
(issue #130, chapter 3, implementation task 2).

Drives the real ``FastApiAdapter.build()`` registration path; only
``auth_coordinator`` is mocked, per this package's adapter testing contract
(see the ``BaseAdapter`` module docstring). ``build_manifest`` itself is unit
tested in ``test_manifest.py`` — here we cover only the wiring: the route
exists, honours auth exactly like the resolver, and is role-independent.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from aoa.action_machine.auth.guest_role import GuestRole
from aoa.action_machine.context.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.fastapi.adapter import FastApiAdapter
from aoa.fastapi.reserved_route_path_error import ReservedRoutePathError

from .support import CancelOrderAction, ManagerRole, PingAction


def _make_client(*, context: Context | None) -> TestClient:
    """Build a real adapter+machine registering two actions; mock only auth."""
    machine = ActionProductMachine(loggers=[])
    auth = AsyncMock()
    auth.process.return_value = context
    adapter = FastApiAdapter(machine=machine, auth_coordinator=auth)
    adapter.post("/actions/cancel-order", CancelOrderAction)
    adapter.get("/actions/ping", PingAction)
    return TestClient(adapter.build())


def _manager_context() -> Context:
    return Context(user=UserInfo(user_id="alice", roles=(ManagerRole,)))


def _guest_context() -> Context:
    return Context(user=UserInfo(roles=(GuestRole,)))


class TestClientManifestEndpoint:
    """The route projects registered routes into a manifest body."""

    def test_authenticated_caller_gets_manifest(self) -> None:
        client = _make_client(context=_manager_context())

        response = client.get("/client-manifest.json")

        assert response.status_code == 200
        body = response.json()
        assert body["protocol"] == 1
        assert body["manifest_version"].startswith("sha256:")
        operations = [endpoint["operation"] for endpoint in body["endpoints"]]
        assert operations == ["POST /actions/cancel-order", "GET /actions/ping"]

    def test_entry_carries_operation_meta_and_schemas(self) -> None:
        client = _make_client(context=_manager_context())

        body = client.get("/client-manifest.json").json()
        entry = next(e for e in body["endpoints"] if e["operation"] == "POST /actions/cancel-order")

        assert entry["name"] == "CancelOrderAction"
        assert entry["domain"] == "OrdersDomain"
        assert entry["route"] == {"method": "POST", "path": "/actions/cancel-order"}
        assert entry["params_schema"]["properties"]["order_id"]["type"] == "integer"
        assert "result_schema" in entry

    def test_bespoke_routes_are_not_listed(self) -> None:
        client = _make_client(context=_manager_context())

        operations = [e["operation"] for e in client.get("/client-manifest.json").json()["endpoints"]]

        # System/permissions routes live directly on the app, not in self._routes.
        assert "GET /health" not in operations
        assert "POST /permissions/resolve" not in operations
        assert "GET /client-manifest.json" not in operations


class TestClientManifestAuth:
    """Auth behaves exactly like the resolver: 403 only when process() returns None."""

    def test_missing_authentication_returns_403(self) -> None:
        client = _make_client(context=None)

        response = client.get("/client-manifest.json")

        assert response.status_code == 403

    def test_guest_gets_the_same_manifest_as_a_user(self) -> None:
        manager_body = _make_client(context=_manager_context()).get("/client-manifest.json").json()
        guest_body = _make_client(context=_guest_context()).get("/client-manifest.json").json()

        # Role-independent: identical version and endpoints for both callers.
        assert guest_body == manager_body


class TestReservedManifestPath:
    """Registering an app action on the catalog path fails fast, not silently."""

    def test_registering_an_action_on_the_manifest_path_raises(self) -> None:
        adapter = FastApiAdapter(machine=ActionProductMachine(loggers=[]), auth_coordinator=AsyncMock())

        # Without the reserved-path guard this would silently shadow the catalog
        # (or be shadowed by it) instead of failing at registration.
        with pytest.raises(ReservedRoutePathError):
            adapter.get("/client-manifest.json", PingAction)
