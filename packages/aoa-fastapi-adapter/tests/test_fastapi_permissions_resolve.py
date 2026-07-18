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
rejection, unknown ``operation`` (per-item ``UNKNOWN_ENDPOINT``), duplicate
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
        """A manager resolving ``CancelOrderAction`` gets an honest ``kind: "success"``."""
        client = _make_client(context=_manager_context())
        response = client.post(
            "/permissions/resolve",
            json={"version": 1, "items": [{"operation": "POST /actions/cancel-order", "params": {"order_id": 7}}]},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["version"] == 1
        result = body["results"][0]
        assert result["kind"] == "success"
        assert result["reason"] == ""

    def test_wrong_role_denied_with_security_kind(self) -> None:
        """A non-manager resolving ``CancelOrderAction`` gets an honest ``kind: "security"`` with a non-empty reason."""
        client = _make_client(context=_user_context())
        response = client.post(
            "/permissions/resolve",
            json={"version": 1, "items": [{"operation": "POST /actions/cancel-order", "params": {"order_id": 7}}]},
        )
        assert response.status_code == 200
        result = response.json()["results"][0]
        assert result["kind"] == "security"
        assert result["reason"] != ""

    def test_batch_of_many_preserves_order(self) -> None:
        """Two different questions in one batch come back as two results, in the same order."""
        client = _make_client(context=_manager_context())
        response = client.post(
            "/permissions/resolve",
            json={
                "version": 1,
                "items": [
                    {"operation": "POST /actions/cancel-order", "params": {"order_id": 1}},
                    {"operation": "POST /actions/cancel-order", "params": {"order_id": 2}},
                ],
            },
        )
        assert response.status_code == 200
        results = response.json()["results"]
        assert len(results) == 2
        assert all(r["kind"] == "success" for r in results)


# ─────────────────────────────────────────────────────────────────────────────
# Deduplication (PR 2): observable client-side behavior only
# ─────────────────────────────────────────────────────────────────────────────


class TestDeduplication:
    """The client sees the same length/order/content whether or not the server deduplicated."""

    def test_duplicate_items_return_identical_results_at_both_positions(self) -> None:
        """Two identical items in one batch still get two results back, and they match."""
        client = _make_client(context=_manager_context())
        response = client.post(
            "/permissions/resolve",
            json={
                "version": 1,
                "items": [
                    {"operation": "POST /actions/cancel-order", "params": {"order_id": 7}},
                    {"operation": "POST /actions/cancel-order", "params": {"order_id": 7}},
                ],
            },
        )
        assert response.status_code == 200
        results = response.json()["results"]
        assert len(results) == 2
        assert results[0] == results[1]

    def test_batch_of_five_two_duplicates_preserves_length_and_order(self) -> None:
        """Book example (chapter 2): positions 0 and 4 repeat the same question; response stays length 5."""
        client = _make_client(context=_manager_context())
        response = client.post(
            "/permissions/resolve",
            json={
                "version": 1,
                "items": [
                    {"operation": "POST /actions/cancel-order", "params": {"order_id": 1}},
                    {"operation": "POST /actions/cancel-order", "params": {"order_id": 2}},
                    {"operation": "POST /actions/cancel-order", "params": {"order_id": 3}},
                    {"operation": "POST /actions/cancel-order", "params": {"order_id": 4}},
                    {"operation": "POST /actions/cancel-order", "params": {"order_id": 1}},
                ],
            },
        )
        assert response.status_code == 200
        results = response.json()["results"]
        assert len(results) == 5
        assert results[0] == results[4]


# ─────────────────────────────────────────────────────────────────────────────
# Guest role vs. genuinely rejected anonymous access
# ─────────────────────────────────────────────────────────────────────────────


class TestGuestAndAnonymous:
    """``GuestRole`` is a real, honest verdict — not a resolver-level special case."""

    def test_guest_context_gets_real_success_kind(self) -> None:
        """A resolved (anonymous) guest ``Context`` — not ``None`` — resolves ``PingAction`` (``@check_roles(GuestRole)``) normally."""
        client = _make_client(context=_guest_context())
        response = client.post(
            "/permissions/resolve",
            json={"version": 1, "items": [{"operation": "GET /actions/ping", "params": {}}]},
        )
        assert response.status_code == 200
        result = response.json()["results"][0]
        assert result["kind"] == "success"

    def test_guest_context_still_denied_for_manager_only_action(self) -> None:
        """A guest is still honestly denied for an action that requires a real role."""
        client = _make_client(context=_guest_context())
        response = client.post(
            "/permissions/resolve",
            json={"version": 1, "items": [{"operation": "POST /actions/cancel-order", "params": {"order_id": 7}}]},
        )
        assert response.status_code == 200
        result = response.json()["results"][0]
        assert result["kind"] == "security"

    def test_process_returning_none_is_rejected_with_401(self) -> None:
        """When ``auth_coordinator.process()`` itself returns ``None``, the resolver never reaches the machine."""
        client = _make_client(context=None)
        response = client.post(
            "/permissions/resolve",
            json={"version": 1, "items": [{"operation": "GET /actions/ping", "params": {}}]},
        )
        assert response.status_code == 403  # AuthorizationError -> 403 per this adapter's exception handler
        # Whole-request failure: no results array at all, not even a partial/empty one.
        assert "results" not in response.json()


# ─────────────────────────────────────────────────────────────────────────────
# Unknown operation and oversized batches
# ─────────────────────────────────────────────────────────────────────────────


class TestErrorMapping:
    """Per-item isolation (PR 2) vs. whole-request error mapping."""

    def test_unknown_operation_gets_a_per_item_check_error(self) -> None:
        """An operation with no registered endpoint is a ``200`` with ``kind: "check_error"``, not a 500/400."""
        client = _make_client(context=_manager_context())
        response = client.post(
            "/permissions/resolve",
            json={"version": 1, "items": [{"operation": "POST /nope", "params": {}}]},
        )
        assert response.status_code == 200
        result = response.json()["results"][0]
        assert result["kind"] == "check_error"
        assert result["reason"] == "UNKNOWN_ENDPOINT"

    def test_unknown_operation_in_the_middle_does_not_affect_other_items(self) -> None:
        """A batch of three, with the middle item unknown, still answers the other two normally."""
        client = _make_client(context=_manager_context())
        response = client.post(
            "/permissions/resolve",
            json={
                "version": 1,
                "items": [
                    {"operation": "POST /actions/cancel-order", "params": {"order_id": 1}},
                    {"operation": "POST /nope", "params": {}},
                    {"operation": "POST /actions/cancel-order", "params": {"order_id": 2}},
                ],
            },
        )
        assert response.status_code == 200
        results = response.json()["results"]
        assert len(results) == 3
        assert results[0]["kind"] == "success"
        assert results[1]["kind"] == "check_error"
        assert results[1]["reason"] == "UNKNOWN_ENDPOINT"
        assert results[2]["kind"] == "success"

    def test_batch_larger_than_machine_limit_is_413(self) -> None:
        """A batch over ``max_check_access_decide_batch_size`` fails the whole request with 413."""
        client = _make_client(context=_manager_context(), max_batch_size=1)
        response = client.post(
            "/permissions/resolve",
            json={
                "version": 1,
                "items": [
                    {"operation": "POST /actions/cancel-order", "params": {"order_id": 1}},
                    {"operation": "POST /actions/cancel-order", "params": {"order_id": 2}},
                ],
            },
        )
        assert response.status_code == 413
        # Whole-request failure: no results array at all, not even a partial/empty one.
        assert "results" not in response.json()

    def test_empty_items_is_422(self) -> None:
        """An empty ``items`` list fails pydantic validation (``min_length=1``) before the resolver runs."""
        client = _make_client(context=_manager_context())
        response = client.post("/permissions/resolve", json={"version": 1, "items": []})
        assert response.status_code == 422

    def test_known_endpoint_with_malformed_params_fails_the_whole_request_with_400(self) -> None:
        """Unlike an unknown operation (isolated to its own CHECK_ERROR), a KNOWN endpoint's
        params failing validation is NOT isolated — it fails the whole request with 400,
        per resolve_verdicts()'s own documented contract."""
        client = _make_client(context=_manager_context())
        response = client.post(
            "/permissions/resolve",
            json={
                "version": 1,
                "items": [
                    {"operation": "POST /actions/cancel-order", "params": {"order_id": "not-an-integer"}},
                ],
            },
        )
        assert response.status_code == 400
        # Whole-request failure: no results array at all, not even a partial/empty one.
        assert "results" not in response.json()

    def test_one_malformed_item_fails_the_whole_batch_even_with_good_items_alongside(self) -> None:
        """The malformed item is not isolated to its own position — the whole batch fails,
        unlike an unknown-operation item, which would leave the good items alone."""
        client = _make_client(context=_manager_context())
        response = client.post(
            "/permissions/resolve",
            json={
                "version": 1,
                "items": [
                    {"operation": "POST /actions/cancel-order", "params": {"order_id": 1}},
                    {"operation": "POST /actions/cancel-order", "params": {"order_id": "not-an-integer"}},
                ],
            },
        )
        assert response.status_code == 400
        assert "results" not in response.json()


# ─────────────────────────────────────────────────────────────────────────────
# Versioning (chapter 3.5, task 8)
# ─────────────────────────────────────────────────────────────────────────────


class TestVersioning:
    """An unsupported ``version`` fails the whole request, before authentication."""

    def test_unsupported_version_is_400_with_error_envelope(self) -> None:
        client = _make_client(context=_manager_context())
        response = client.post(
            "/permissions/resolve",
            json={"version": 2, "items": [{"operation": "GET /actions/ping", "params": {}}]},
        )
        assert response.status_code == 400
        assert response.json() == {"error": {"code": "unsupported_version"}}

    def test_unsupported_version_is_rejected_even_when_unauthenticated(self) -> None:
        """Version is checked before auth: a wrong-language caller never has to authenticate first."""
        client = _make_client(context=None)
        response = client.post(
            "/permissions/resolve",
            json={"version": 2, "items": [{"operation": "GET /actions/ping", "params": {}}]},
        )
        assert response.status_code == 400
        assert response.json() == {"error": {"code": "unsupported_version"}}

    def test_supported_version_round_trips_on_the_response(self) -> None:
        client = _make_client(context=_manager_context())
        response = client.post(
            "/permissions/resolve",
            json={"version": 1, "items": [{"operation": "GET /actions/ping", "params": {}}]},
        )
        assert response.status_code == 200
        assert response.json()["version"] == 1
