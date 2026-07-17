# tests/test_fastapi_permissions_resolve.py
"""
End-to-end tests for ``POST /permissions/resolve`` (issue #130, PR 1 + PR 2).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Drives the real registration path (``FastApiAdapter.build()`` ->
``_register_permissions_endpoints``) against a real ``ActionProductMachine`` and
real ``@check_roles``-gated actions — only ``auth_coordinator`` is mocked, per
this package's adapter testing contract (see ``BaseAdapter`` module docstring).

Covers: role-gate allow/deny, guest (anonymous) access, truly-unauthenticated
rejection, unknown ``operation`` (per-item ``UNKNOWN_ACTION``, PR 2), duplicate
items in one batch (PR 2), reserved-path collisions, and the
``max_check_access_decide_batch_size`` -> HTTP 413 mapping. Deduplication's
internal accounting (``real_call_count``) is asserted directly against
``resolve_verdicts`` in ``test_fastapi_permissions_resolve_verdicts.py`` — this
file only checks what a real client actually observes over HTTP.
"""

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

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _make_client(*, context: Context | None, max_batch_size: int = 100) -> TestClient:
    """Build a real adapter+machine, register ``CancelOrderAction``/``PingAction``, and return a ``TestClient``."""
    machine = ActionProductMachine(loggers=[], max_check_access_decide_batch_size=max_batch_size)
    auth = AsyncMock()
    auth.process.return_value = context
    adapter = FastApiAdapter(machine=machine, auth_coordinator=auth)
    adapter.post("/actions/cancel-order", CancelOrderAction)
    adapter.get("/actions/ping", PingAction)
    return TestClient(adapter.build())


def _manager_context() -> Context:
    return Context(user=UserInfo(user_id="alice", roles=(ManagerRole,)))


def _user_context() -> Context:
    return Context(user=UserInfo(user_id="bob", roles=(UserRole,)))


def _guest_context() -> Context:
    return Context(user=UserInfo(roles=(GuestRole,)))


# ─────────────────────────────────────────────────────────────────────────────
# Reserved paths
# ─────────────────────────────────────────────────────────────────────────────


class TestReservedPaths:
    """Registering an app action on a bespoke-route path fails loudly, not silently."""

    def test_post_on_resolve_path_raises(self) -> None:
        """``.post("/permissions/resolve", ...)`` raises before ``build()`` is ever called."""
        machine = ActionProductMachine(loggers=[])
        auth = AsyncMock()
        adapter = FastApiAdapter(machine=machine, auth_coordinator=auth)
        with pytest.raises(ReservedRoutePathError, match="/permissions/resolve"):
            adapter.post("/permissions/resolve", CancelOrderAction)

    def test_get_on_health_path_raises(self) -> None:
        """``.get("/health", ...)`` raises the same way — the health-check path is reserved too."""
        machine = ActionProductMachine(loggers=[])
        auth = AsyncMock()
        adapter = FastApiAdapter(machine=machine, auth_coordinator=auth)
        with pytest.raises(ReservedRoutePathError, match="/health"):
            adapter.get("/health", PingAction)


# ─────────────────────────────────────────────────────────────────────────────
# Role-gate: allow / deny
# ─────────────────────────────────────────────────────────────────────────────


class TestRoleGate:
    """The resolver's role-gate (levels 1/2) against a real ``ActionProductMachine``."""

    def test_manager_role_allowed(self) -> None:
        """A manager resolving ``CancelOrderAction`` gets an honest ``allowed: true``."""
        client = _make_client(context=_manager_context())
        response = client.post(
            "/permissions/resolve",
            json={"protocol": 1, "items": [{"operation": "CancelOrderAction", "params": {"order_id": 7}}]},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["protocol"] == 1
        verdict = body["verdicts"][0]
        assert verdict["allowed"] is True
        assert verdict["scope"] is None
        assert verdict["level"] is None

    def test_wrong_role_denied_with_role_scope(self) -> None:
        """A non-manager resolving ``CancelOrderAction`` gets an honest ``allowed: false``, ``scope: "role"``."""
        client = _make_client(context=_user_context())
        response = client.post(
            "/permissions/resolve",
            json={"protocol": 1, "items": [{"operation": "CancelOrderAction", "params": {"order_id": 7}}]},
        )
        assert response.status_code == 200
        verdict = response.json()["verdicts"][0]
        assert verdict["allowed"] is False
        assert verdict["scope"] == "role"
        assert verdict["level"] in (1, 2)
        # PR 1 never surfaces entities/reason_code for real yet.
        assert verdict["entities"] == []
        assert verdict["reason_code"] is None

    def test_batch_of_many_preserves_order(self) -> None:
        """Two different questions in one batch come back as two verdicts, in the same order."""
        client = _make_client(context=_manager_context())
        response = client.post(
            "/permissions/resolve",
            json={
                "protocol": 1,
                "items": [
                    {"operation": "CancelOrderAction", "params": {"order_id": 1}},
                    {"operation": "CancelOrderAction", "params": {"order_id": 2}},
                ],
            },
        )
        assert response.status_code == 200
        verdicts = response.json()["verdicts"]
        assert len(verdicts) == 2
        assert all(v["allowed"] is True for v in verdicts)


# ─────────────────────────────────────────────────────────────────────────────
# Deduplication (PR 2): observable client-side behavior only
# ─────────────────────────────────────────────────────────────────────────────


class TestDeduplication:
    """The client sees the same length/order/content whether or not the server deduplicated."""

    def test_duplicate_items_return_identical_verdicts_at_both_positions(self) -> None:
        """Two identical items in one batch still get two verdicts back, and they match."""
        client = _make_client(context=_manager_context())
        response = client.post(
            "/permissions/resolve",
            json={
                "protocol": 1,
                "items": [
                    {"operation": "CancelOrderAction", "params": {"order_id": 7}},
                    {"operation": "CancelOrderAction", "params": {"order_id": 7}},
                ],
            },
        )
        assert response.status_code == 200
        verdicts = response.json()["verdicts"]
        assert len(verdicts) == 2
        assert verdicts[0] == verdicts[1]

    def test_batch_of_five_two_duplicates_preserves_length_and_order(self) -> None:
        """Book example (chapter 2): positions 0 and 4 repeat the same question; response stays length 5."""
        client = _make_client(context=_manager_context())
        response = client.post(
            "/permissions/resolve",
            json={
                "protocol": 1,
                "items": [
                    {"operation": "CancelOrderAction", "params": {"order_id": 1}},
                    {"operation": "CancelOrderAction", "params": {"order_id": 2}},
                    {"operation": "CancelOrderAction", "params": {"order_id": 3}},
                    {"operation": "CancelOrderAction", "params": {"order_id": 4}},
                    {"operation": "CancelOrderAction", "params": {"order_id": 1}},
                ],
            },
        )
        assert response.status_code == 200
        verdicts = response.json()["verdicts"]
        assert len(verdicts) == 5
        assert verdicts[0] == verdicts[4]


# ─────────────────────────────────────────────────────────────────────────────
# Guest role vs. genuinely rejected anonymous access
# ─────────────────────────────────────────────────────────────────────────────


class TestGuestAndAnonymous:
    """``GuestRole`` is a real, honest verdict — not a resolver-level special case."""

    def test_guest_context_gets_real_allowed_true(self) -> None:
        """A resolved (anonymous) guest ``Context`` — not ``None`` — resolves ``PingAction`` (``@check_roles(GuestRole)``) normally."""
        client = _make_client(context=_guest_context())
        response = client.post(
            "/permissions/resolve",
            json={"protocol": 1, "items": [{"operation": "PingAction", "params": {}}]},
        )
        assert response.status_code == 200
        verdict = response.json()["verdicts"][0]
        assert verdict["allowed"] is True

    def test_guest_context_still_denied_for_manager_only_action(self) -> None:
        """A guest is still honestly denied for an action that requires a real role."""
        client = _make_client(context=_guest_context())
        response = client.post(
            "/permissions/resolve",
            json={"protocol": 1, "items": [{"operation": "CancelOrderAction", "params": {"order_id": 7}}]},
        )
        assert response.status_code == 200
        verdict = response.json()["verdicts"][0]
        assert verdict["allowed"] is False

    def test_process_returning_none_is_rejected_with_401(self) -> None:
        """When ``auth_coordinator.process()`` itself returns ``None``, the resolver never reaches the machine."""
        client = _make_client(context=None)
        response = client.post(
            "/permissions/resolve",
            json={"protocol": 1, "items": [{"operation": "PingAction", "params": {}}]},
        )
        assert response.status_code == 403  # AuthorizationError -> 403 per this adapter's exception handler


# ─────────────────────────────────────────────────────────────────────────────
# Unknown operation and oversized batches
# ─────────────────────────────────────────────────────────────────────────────


class TestErrorMapping:
    """Per-item isolation (PR 2) vs. whole-request error mapping."""

    def test_unknown_operation_gets_a_per_item_reason_code(self) -> None:
        """An operation name with no registered action is a ``200`` with ``reason_code: UNKNOWN_ACTION``, not a 500/400."""
        client = _make_client(context=_manager_context())
        response = client.post(
            "/permissions/resolve",
            json={"protocol": 1, "items": [{"operation": "NoSuchAction", "params": {}}]},
        )
        assert response.status_code == 200
        verdict = response.json()["verdicts"][0]
        assert verdict["allowed"] is False
        assert verdict["reason_code"] == "UNKNOWN_ACTION"

    def test_unknown_operation_in_the_middle_does_not_affect_other_items(self) -> None:
        """A batch of three, with the middle item unknown, still answers the other two normally."""
        client = _make_client(context=_manager_context())
        response = client.post(
            "/permissions/resolve",
            json={
                "protocol": 1,
                "items": [
                    {"operation": "CancelOrderAction", "params": {"order_id": 1}},
                    {"operation": "NoSuchAction", "params": {}},
                    {"operation": "CancelOrderAction", "params": {"order_id": 2}},
                ],
            },
        )
        assert response.status_code == 200
        verdicts = response.json()["verdicts"]
        assert len(verdicts) == 3
        assert verdicts[0]["allowed"] is True
        assert verdicts[1]["allowed"] is False
        assert verdicts[1]["reason_code"] == "UNKNOWN_ACTION"
        assert verdicts[2]["allowed"] is True

    def test_batch_larger_than_machine_limit_is_413(self) -> None:
        """A batch over ``max_check_access_decide_batch_size`` fails the whole request with 413."""
        client = _make_client(context=_manager_context(), max_batch_size=1)
        response = client.post(
            "/permissions/resolve",
            json={
                "protocol": 1,
                "items": [
                    {"operation": "CancelOrderAction", "params": {"order_id": 1}},
                    {"operation": "CancelOrderAction", "params": {"order_id": 2}},
                ],
            },
        )
        assert response.status_code == 413

    def test_empty_items_is_422(self) -> None:
        """An empty ``items`` list fails pydantic validation (``min_length=1``) before the resolver runs."""
        client = _make_client(context=_manager_context())
        response = client.post("/permissions/resolve", json={"protocol": 1, "items": []})
        assert response.status_code == 422
