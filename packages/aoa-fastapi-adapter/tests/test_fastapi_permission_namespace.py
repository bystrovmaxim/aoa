"""
Integration tests for ``GET /permissions/namespace`` — ``PermissionNamespace``/
``cache_partition`` (issue #130, chapter 3.5, implementation task 4).

Drives the real ``FastApiAdapter.build()`` registration path; only
``auth_coordinator`` is mocked, per this package's adapter testing contract
(see the ``BaseAdapter`` module docstring). ``compute_cache_partition`` itself
is unit tested in ``aoa-action-machine``; here we cover only the wiring: the
route exists, honours auth exactly like the resolver/manifest, and delivers a
label that actually varies with identity.
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

from .support import CancelOrderAction, ManagerRole, PingAction, UserRole


def _make_client(*, context: Context | None) -> TestClient:
    """Build a real adapter+machine registering two actions; mock only auth."""
    machine = ActionProductMachine(loggers=[])
    auth = AsyncMock()
    auth.process.return_value = context
    adapter = FastApiAdapter(machine=machine, auth_coordinator=auth)
    adapter.post("/actions/cancel-order", CancelOrderAction)
    adapter.get("/actions/ping", PingAction)
    return TestClient(adapter.build())


def _manager_context(user_id: str = "alice") -> Context:
    return Context(user=UserInfo(user_id=user_id, roles=(ManagerRole,)))


def _guest_context() -> Context:
    return Context(user=UserInfo(roles=(GuestRole,)))


class TestPermissionNamespaceEndpoint:
    """The route derives an opaque cache_partition from the caller's identity."""

    def test_authenticated_caller_gets_a_cache_partition(self) -> None:
        client = _make_client(context=_manager_context())

        response = client.get("/permissions/namespace")

        assert response.status_code == 200
        body = response.json()
        assert set(body) == {"cache_partition"}
        assert isinstance(body["cache_partition"], str) and body["cache_partition"]

    def test_same_identity_yields_the_same_partition_every_call(self) -> None:
        client = _make_client(context=_manager_context())

        first = client.get("/permissions/namespace").json()["cache_partition"]
        second = client.get("/permissions/namespace").json()["cache_partition"]

        assert first == second

    def test_different_user_id_yields_a_different_partition(self) -> None:
        alice = _make_client(context=_manager_context("alice")).get("/permissions/namespace").json()
        bob = _make_client(context=_manager_context("bob")).get("/permissions/namespace").json()

        assert alice["cache_partition"] != bob["cache_partition"]

    def test_different_roles_yields_a_different_partition_for_the_same_user_id(self) -> None:
        manager = Context(user=UserInfo(user_id="alice", roles=(ManagerRole,)))
        as_manager = _make_client(context=manager).get("/permissions/namespace").json()

        user = Context(user=UserInfo(user_id="alice", roles=(UserRole,)))
        as_user = _make_client(context=user).get("/permissions/namespace").json()

        assert as_manager["cache_partition"] != as_user["cache_partition"]

    def test_bespoke_route_is_not_listed_in_the_manifest(self) -> None:
        client = _make_client(context=_manager_context())

        operations = [e["operation"] for e in client.get("/client-manifest.json").json()["endpoints"]]

        assert "GET /permissions/namespace" not in operations


class TestPermissionNamespaceAuth:
    """Auth behaves exactly like the resolver/manifest: 403 only when process() returns None."""

    def test_missing_authentication_returns_403(self) -> None:
        client = _make_client(context=None)

        response = client.get("/permissions/namespace")

        assert response.status_code == 403

    def test_guest_still_gets_a_real_partition(self) -> None:
        """A resolved (anonymous) guest Context — not None — still gets a well-defined label."""
        client = _make_client(context=_guest_context())

        response = client.get("/permissions/namespace")

        assert response.status_code == 200
        assert response.json()["cache_partition"]


class TestReservedPermissionNamespacePath:
    """Registering an app action on the namespace path fails fast, not silently."""

    def test_registering_an_action_on_the_namespace_path_raises(self) -> None:
        adapter = FastApiAdapter(machine=ActionProductMachine(loggers=[]), auth_coordinator=AsyncMock())

        with pytest.raises(ReservedRoutePathError):
            adapter.get("/permissions/namespace", PingAction)
