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
items in one batch (PR 2), and reserved-path collisions. Deduplication's
internal accounting (``real_call_count``) is asserted directly against
``resolve_verdicts`` in ``test_fastapi_permissions_resolve_verdicts.py`` — this
file only checks what a real client actually observes over HTTP.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from aoa.action_machine.auth.guest_role import GuestRole
from aoa.action_machine.context.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.exceptions.access_denied_error import AccessDeniedError, AccessGate
from aoa.action_machine.intents.access_control import FailSecurityVerdict
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.resources.per_call_connection import PerCallConnection
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.fastapi.adapter import FastApiAdapter
from aoa.fastapi.reserved_route_path_error import ReservedRoutePathError

from .support import CRASHING_ORDER_ID, ArchiveOrderAction, CancelOrderAction, ManagerRole, PingAction, UserRole

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _make_client(*, context: Context | None) -> TestClient:
    """Build a real adapter+machine, register ``CancelOrderAction``/``PingAction``, and return a ``TestClient``."""
    machine = ActionProductMachine(loggers=[])
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
        """A manager resolving ``CancelOrderAction`` gets an honest ``kind: "AllowedVerdict"``."""
        client = _make_client(context=_manager_context())
        response = client.post(
            "/permissions/resolve",
            json={"version": 1, "items": [{"operation": "POST /actions/cancel-order", "params": {"order_id": 7}}]},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["version"] == 1
        result = body["results"][0]
        assert result["kind"] == "AllowedVerdict"
        assert "reason" not in result

    def test_wrong_role_denied_with_security_kind(self) -> None:
        """A non-manager resolving ``CancelOrderAction`` gets an honest ``kind: "FailSecurityVerdict"`` with a non-empty reason."""
        client = _make_client(context=_user_context())
        response = client.post(
            "/permissions/resolve",
            json={"version": 1, "items": [{"operation": "POST /actions/cancel-order", "params": {"order_id": 7}}]},
        )
        assert response.status_code == 200
        result = response.json()["results"][0]
        assert result["kind"] == "FailSecurityVerdict"
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
        assert all(r["kind"] == "AllowedVerdict" for r in results)

    def test_result_never_carries_action_over_the_wire(self) -> None:
        """resolve_verdicts() now returns real AllowedVerdict/FailSecurityVerdict/
        FailErrorVerdict instances directly (no to_wire() step, fix-audit finding
        7's follow-up) -- confirm the internal-only `action` field (a live Python
        class reference) never actually reaches JSON, for both a real cascade
        verdict and the synthetic ones (unknown endpoint)."""
        client = _make_client(context=_manager_context())
        response = client.post(
            "/permissions/resolve",
            json={
                "version": 1,
                "items": [
                    {"operation": "POST /actions/cancel-order", "params": {"order_id": 1}},
                    {"operation": "POST /nope", "params": {}},
                ],
            },
        )
        assert response.status_code == 200
        results = response.json()["results"]
        assert len(results) == 2
        assert set(results[0].keys()) == {"kind"}
        assert results[0]["kind"] == "AllowedVerdict"
        assert set(results[1].keys()) == {"kind", "reason"}


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
        assert result["kind"] == "AllowedVerdict"

    def test_guest_context_still_denied_for_manager_only_action(self) -> None:
        """A guest is still honestly denied for an action that requires a real role."""
        client = _make_client(context=_guest_context())
        response = client.post(
            "/permissions/resolve",
            json={"version": 1, "items": [{"operation": "POST /actions/cancel-order", "params": {"order_id": 7}}]},
        )
        assert response.status_code == 200
        result = response.json()["results"][0]
        assert result["kind"] == "FailSecurityVerdict"

    def test_process_returning_none_is_rejected_with_401(self) -> None:
        """When ``auth_coordinator.process()`` itself returns ``None``, the resolver never reaches the machine."""
        client = _make_client(context=None)
        response = client.post(
            "/permissions/resolve",
            json={"version": 1, "items": [{"operation": "GET /actions/ping", "params": {}}]},
        )
        assert response.status_code == 403  # AccessDeniedError -> 403 per this adapter's exception handler
        # Whole-request failure: no results array at all, not even a partial/empty one.
        assert "results" not in response.json()


# ─────────────────────────────────────────────────────────────────────────────
# Unknown operation and oversized batches
# ─────────────────────────────────────────────────────────────────────────────


class TestErrorMapping:
    """Per-item isolation (PR 2) vs. whole-request error mapping."""

    def test_unknown_operation_gets_a_per_item_check_error(self) -> None:
        """An operation with no registered endpoint is a ``200`` with ``kind: "FailErrorVerdict"``, not a 500/400."""
        client = _make_client(context=_manager_context())
        response = client.post(
            "/permissions/resolve",
            json={"version": 1, "items": [{"operation": "POST /nope", "params": {}}]},
        )
        assert response.status_code == 200
        result = response.json()["results"][0]
        assert result["kind"] == "FailErrorVerdict"
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
        assert results[0]["kind"] == "AllowedVerdict"
        assert results[1]["kind"] == "FailErrorVerdict"
        assert results[1]["reason"] == "UNKNOWN_ENDPOINT"
        assert results[2]["kind"] == "AllowedVerdict"

    def test_empty_items_is_422(self) -> None:
        """An empty ``items`` list fails pydantic validation (``min_length=1``) before the resolver runs."""
        client = _make_client(context=_manager_context())
        response = client.post("/permissions/resolve", json={"version": 1, "items": []})
        assert response.status_code == 422

    def test_known_endpoint_with_malformed_params_fails_the_whole_request_with_400(self) -> None:
        """Unlike an unknown operation (isolated to its own FailErrorVerdict), a KNOWN endpoint's
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


# ─────────────────────────────────────────────────────────────────────────────
# Object-level codes on the wire (audit-11 finding 9)
# ─────────────────────────────────────────────────────────────────────────────


class TestObjectLevelCodesOverHttp:
    """``FORBIDDEN_OBJECT`` and ``EVALUATION_FAILED`` as a real client sees them.

    Every other test of these two codes works either in-process (against
    ``machine.check_access_decide``) or against a hand-written fake ``fetch``. Nothing
    asserted that they survive serialization and arrive in the JSON body — so a
    regression such as losing ``SerializeAsAny`` on ``results`` (a pydantic trap
    ``permissions_schema.py`` already documents as having bitten once) would strip
    ``reason`` from the response while leaving every in-process test green.
    """

    def _archiving_client(self, *, context: Context | None) -> TestClient:
        machine = ActionProductMachine(loggers=[])
        auth = AsyncMock()
        auth.process.return_value = context
        adapter = FastApiAdapter(machine=machine, auth_coordinator=auth)
        adapter.post("/actions/archive-order", ArchiveOrderAction)
        return TestClient(adapter.build())

    def _resolve(self, client: TestClient, order_ids: list[int]) -> list[dict]:
        response = client.post(
            "/permissions/resolve",
            json={
                "version": 1,
                "items": [
                    {"operation": "POST /actions/archive-order", "params": {"order_id": oid}} for oid in order_ids
                ],
            },
        )
        assert response.status_code == 200
        return response.json()["results"]

    def test_missing_and_foreign_objects_are_byte_identical_in_the_json_body(self) -> None:
        """The oracle guarantee where it actually matters: in the bytes the client receives."""
        client = self._archiving_client(context=_manager_context())  # alice owns order 1
        own, foreign, missing = self._resolve(client, [1, 2, 404])

        assert own == {"kind": "AllowedVerdict"}
        assert foreign == {"kind": "FailSecurityVerdict", "reason": "FORBIDDEN_OBJECT"}
        assert missing == foreign  # whole dict, not just the reason

    def test_crashed_check_arrives_as_evaluation_failed_inside_a_200(self) -> None:
        """A crash is one item's honest error, not a denial and not a failed request."""
        client = self._archiving_client(context=_manager_context())
        (crashed,) = self._resolve(client, [CRASHING_ORDER_ID])

        assert crashed == {"kind": "FailErrorVerdict", "reason": "EVALUATION_FAILED"}

    def test_a_crash_does_not_disturb_the_other_items_in_the_batch(self) -> None:
        """Per-item isolation, asserted over HTTP rather than in-process."""
        client = self._archiving_client(context=_manager_context())
        results = self._resolve(client, [1, CRASHING_ORDER_ID, 2, 1])

        assert results == [
            {"kind": "AllowedVerdict"},
            {"kind": "FailErrorVerdict", "reason": "EVALUATION_FAILED"},
            {"kind": "FailSecurityVerdict", "reason": "FORBIDDEN_OBJECT"},
            {"kind": "AllowedVerdict"},  # deduplicated against item 0, same answer
        ]

    def test_the_crashing_exception_never_reaches_the_client(self) -> None:
        """The raised ConnectionError names the db and the order id; neither may appear."""
        client = self._archiving_client(context=_manager_context())
        response = client.post(
            "/permissions/resolve",
            json={
                "version": 1,
                "items": [
                    {"operation": "POST /actions/archive-order", "params": {"order_id": CRASHING_ORDER_ID}}
                ],
            },
        )
        body = response.text
        assert "ConnectionError" not in body
        assert "orders_db" not in body
        assert "unreachable" not in body

    def test_fail_error_reasons_on_the_wire_are_a_closed_set(self) -> None:
        """Pins permissions_schema.py's own claim (audit-11 finding 4): the resolver emits
        UNKNOWN_ENDPOINT or EVALUATION_FAILED, never anything else."""
        client = self._archiving_client(context=_manager_context())
        response = client.post(
            "/permissions/resolve",
            json={
                "version": 1,
                "items": [
                    {"operation": "POST /actions/archive-order", "params": {"order_id": CRASHING_ORDER_ID}},
                    {"operation": "POST /actions/no-such-route", "params": {}},
                ],
            },
        )
        assert response.status_code == 200
        reasons = {r["reason"] for r in response.json()["results"] if r["kind"] == "FailErrorVerdict"}
        assert reasons == {"EVALUATION_FAILED", "UNKNOWN_ENDPOINT"}


# ─────────────────────────────────────────────────────────────────────────────
# params_mapper failures stay per-item (audit-11 finding 11)
# ─────────────────────────────────────────────────────────────────────────────


class TestParamsMapperIsolation:
    """A route's ``params_mapper`` is app code and can fail like any other check step.

    Unprotected, its exception escaped ``resolve_verdicts`` entirely and became a
    whole-request 500 with no results -- one bad item sinking a batch of twenty, the
    exact outcome the per-item isolation contract rules out.
    """

    @staticmethod
    def _exploding_mapper(body: object) -> object:
        raise RuntimeError("mapper blew up: order 7 of customer bob@corp.com")

    def _client_with_broken_mapper(self) -> TestClient:
        machine = ActionProductMachine(loggers=[])
        auth = AsyncMock()
        auth.process.return_value = _manager_context()
        adapter = FastApiAdapter(machine=machine, auth_coordinator=auth)
        adapter.post("/actions/cancel-order", CancelOrderAction, params_mapper=self._exploding_mapper)
        adapter.get("/actions/ping", PingAction)
        return TestClient(adapter.build(), raise_server_exceptions=False)

    def test_a_failing_mapper_no_longer_sinks_the_whole_batch(self) -> None:
        response = self._client_with_broken_mapper().post(
            "/permissions/resolve",
            json={
                "version": 1,
                "items": [
                    {"operation": "GET /actions/ping", "params": {}},
                    {"operation": "POST /actions/cancel-order", "params": {"order_id": 7}},
                    {"operation": "GET /actions/ping", "params": {}},
                ],
            },
        )
        assert response.status_code == 200
        assert response.json()["results"] == [
            {"kind": "AllowedVerdict"},
            {"kind": "FailErrorVerdict", "reason": "EVALUATION_FAILED"},
            {"kind": "AllowedVerdict"},
        ]

    def test_a_mapper_that_denies_reports_its_denial_not_a_failure(self) -> None:
        """A mapper can *decide*, not only fail. One that resolves the caller's tenant may
        legitimately refuse. Left to the broad handler, that refusal comes back as "could
        not check", which the caller reads as "ask again" and shows the action as
        available. A failure is not a denial, and a denial is not a failure."""
        machine = ActionProductMachine(loggers=[])
        auth = AsyncMock()
        auth.process.return_value = _manager_context()
        adapter = FastApiAdapter(machine=machine, auth_coordinator=auth)

        def denying_mapper(body: object) -> object:
            raise AccessDeniedError(
                "wrong tenant", refused_by=AccessGate.ACCESS_DECIDE, verdict=FailSecurityVerdict("FORBIDDEN_TENANT")
            )

        adapter.post("/actions/cancel-order", CancelOrderAction, params_mapper=denying_mapper)
        client = TestClient(adapter.build(), raise_server_exceptions=False)

        response = client.post(
            "/permissions/resolve",
            json={"version": 1, "items": [{"operation": "POST /actions/cancel-order", "params": {"order_id": 7}}]},
        )

        assert response.status_code == 200
        assert response.json()["results"] == [{"kind": "FailSecurityVerdict", "reason": "FORBIDDEN_TENANT"}]

    def test_a_mapper_refusal_reports_its_reason_and_never_its_message(self) -> None:
        """The refusal is reported by its declared reason. The message is free-form text
        an application writes for a log -- here it names a customer -- and it must not
        cross the wire, however the refusal itself is answered."""
        machine = ActionProductMachine(loggers=[])
        auth = AsyncMock()
        auth.process.return_value = _manager_context()
        adapter = FastApiAdapter(machine=machine, auth_coordinator=auth)

        def bare_denying_mapper(body: object) -> object:
            raise AccessDeniedError(
                "tenant lookup failed for bob@corp.com",
                refused_by=AccessGate.ACCESS_DECIDE,
                verdict=FailSecurityVerdict("FORBIDDEN_OBJECT"),
            )

        adapter.post("/actions/cancel-order", CancelOrderAction, params_mapper=bare_denying_mapper)
        client = TestClient(adapter.build(), raise_server_exceptions=False)

        response = client.post(
            "/permissions/resolve",
            json={"version": 1, "items": [{"operation": "POST /actions/cancel-order", "params": {"order_id": 7}}]},
        )

        assert response.json()["results"] == [{"kind": "FailSecurityVerdict", "reason": "FORBIDDEN_OBJECT"}]
        assert "bob@corp.com" not in response.text

    def test_the_mapper_exception_text_never_reaches_the_client(self) -> None:
        """The raised message names an order and an e-mail; neither may cross the wire."""
        response = self._client_with_broken_mapper().post(
            "/permissions/resolve",
            json={
                "version": 1,
                "items": [{"operation": "POST /actions/cancel-order", "params": {"order_id": 7}}],
            },
        )
        assert response.status_code == 200
        assert "bob@corp.com" not in response.text
        assert "blew up" not in response.text
        assert "RuntimeError" not in response.text

    def test_a_working_mapper_is_untouched(self) -> None:
        """Regression guard: the happy path still maps and still resolves."""
        machine = ActionProductMachine(loggers=[])
        auth = AsyncMock()
        auth.process.return_value = _manager_context()
        adapter = FastApiAdapter(machine=machine, auth_coordinator=auth)
        adapter.post(
            "/actions/cancel-order",
            CancelOrderAction,
            params_mapper=lambda body: CancelOrderAction.Params(order_id=body.order_id + 1),
        )
        client = TestClient(adapter.build())

        response = client.post(
            "/permissions/resolve",
            json={"version": 1, "items": [{"operation": "POST /actions/cancel-order", "params": {"order_id": 7}}]},
        )
        assert response.status_code == 200
        assert response.json()["results"] == [{"kind": "AllowedVerdict"}]

    def test_params_validation_failure_is_still_a_400_for_the_whole_request(self) -> None:
        """Bad params are the *client's* error, not a check failure, and keep the existing
        whole-request 400 rather than becoming a per-item verdict.

        Note this input fails at ``model_validate``, *before* the mapper runs, so it
        passes with or without the mapper handler -- it pins the untouched path. The two
        tests below cover the path the handler actually changed (narrow-audit finding 8)."""
        response = self._client_with_broken_mapper().post(
            "/permissions/resolve",
            json={"version": 1, "items": [{"operation": "POST /actions/cancel-order", "params": {"order_id": "abc"}}]},
        )
        assert response.status_code == 400

    def test_a_mapper_raising_validationerror_is_a_400_not_a_per_item_failure(self) -> None:
        """narrow-audit finding 8: params that fail to validate *inside* the mapper are the
        same kind of problem as ones that fail outside it -- the client's request is
        malformed. Answering EVALUATION_FAILED would say "could not check, ask again",
        which no amount of asking again fixes."""
        machine = ActionProductMachine(loggers=[])
        auth = AsyncMock()
        auth.process.return_value = _manager_context()
        adapter = FastApiAdapter(machine=machine, auth_coordinator=auth)

        def validating_mapper(body: object) -> object:
            return CancelOrderAction.Params(order_id="not-an-int")  # type: ignore[arg-type]

        adapter.post("/actions/cancel-order", CancelOrderAction, params_mapper=validating_mapper)
        client = TestClient(adapter.build(), raise_server_exceptions=False)

        response = client.post(
            "/permissions/resolve",
            json={"version": 1, "items": [{"operation": "POST /actions/cancel-order", "params": {"order_id": 7}}]},
        )

        assert response.status_code == 400

    def test_a_mapper_raising_httpexception_dictates_the_response(self) -> None:
        """An HTTPException from app code is an explicit instruction about the response.
        Folding it into a per-item verdict would discard that signal."""
        machine = ActionProductMachine(loggers=[])
        auth = AsyncMock()
        auth.process.return_value = _manager_context()
        adapter = FastApiAdapter(machine=machine, auth_coordinator=auth)

        def refusing_mapper(body: object) -> object:
            raise HTTPException(status_code=400, detail="order_id must be positive")

        adapter.post("/actions/cancel-order", CancelOrderAction, params_mapper=refusing_mapper)
        client = TestClient(adapter.build(), raise_server_exceptions=False)

        response = client.post(
            "/permissions/resolve",
            json={"version": 1, "items": [{"operation": "POST /actions/cancel-order", "params": {"order_id": 7}}]},
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "order_id must be positive"


# ─────────────────────────────────────────────────────────────────────────────
# prepare() failures stay per-operation (narrow-audit finding 3)
# ─────────────────────────────────────────────────────────────────────────────


class TestPreparationIsolation:
    """``plan.prepare()`` runs app code too -- a route's own ``auth_coordinator`` and its
    connection factories -- and only ``AccessDeniedError`` was caught around it.

    Anything else escaped the resolver entirely and answered the whole request with a
    500 and no results, the same "one bad item sinks the batch" outcome the mapper
    handler was added to prevent one frame below.
    """

    _BATCH = {
        "version": 1,
        "items": [
            {"operation": "GET /actions/ping", "params": {}},
            {"operation": "POST /actions/cancel-order", "params": {"order_id": 7}},
            {"operation": "GET /actions/ping", "params": {}},
        ],
    }
    _ISOLATED = [
        {"kind": "AllowedVerdict"},
        {"kind": "FailErrorVerdict", "reason": "EVALUATION_FAILED"},
        {"kind": "AllowedVerdict"},
    ]

    def _client(self, **cancel_kwargs: object) -> TestClient:
        machine = ActionProductMachine(loggers=[])
        auth = AsyncMock()
        auth.process.return_value = _manager_context()
        adapter = FastApiAdapter(machine=machine, auth_coordinator=auth)
        adapter.post("/actions/cancel-order", CancelOrderAction, **cancel_kwargs)  # type: ignore[arg-type]
        adapter.get("/actions/ping", PingAction)
        return TestClient(adapter.build(), raise_server_exceptions=False)

    def test_a_route_auth_coordinator_that_crashes_does_not_sink_the_batch(self) -> None:
        exploding_auth = AsyncMock()
        exploding_auth.process.side_effect = RuntimeError("token service unreachable for bob@corp.com")
        response = self._client(auth_coordinator=exploding_auth).post("/permissions/resolve", json=self._BATCH)

        assert response.status_code == 200
        assert response.json()["results"] == self._ISOLATED
        assert "bob@corp.com" not in response.text
        assert "token service" not in response.text

    def test_a_connection_factory_that_crashes_does_not_sink_the_batch(self) -> None:
        def exploding_factory() -> BaseResource:
            raise ConnectionError("orders_db unreachable")

        response = self._client(connections={"orders_db": PerCallConnection(factory=exploding_factory)}).post(
            "/permissions/resolve", json=self._BATCH
        )

        assert response.status_code == 200
        assert response.json()["results"] == self._ISOLATED
        assert "orders_db" not in response.text

    def test_a_route_level_auth_rejection_is_still_a_denial_not_a_failure(self) -> None:
        """Regression guard: AccessDeniedError from prepare() keeps its own, distinct
        answer -- UNAUTHORIZED, a denial -- and must not be swallowed by the new broad
        handler sitting next to it."""
        rejecting_auth = AsyncMock()
        rejecting_auth.process.side_effect = AccessDeniedError(
            "Authentication required", refused_by=AccessGate.AUTH_COORDINATOR, verdict=FailSecurityVerdict("UNAUTHENTICATED")
        )
        response = self._client(auth_coordinator=rejecting_auth).post("/permissions/resolve", json=self._BATCH)

        assert response.status_code == 200
        assert response.json()["results"][1] == {"kind": "FailSecurityVerdict", "reason": "UNAUTHORIZED"}


class TestCancellationIsNotAVerdict:
    """A cancelled request must abort, never answer (chapter 12, #144).

    When a caller hangs up mid-request, the ASGI server cancels the handler task and
    ``asyncio.CancelledError`` is raised at whatever ``await`` the resolver is sitting
    on. The resolver is full of deliberately broad ``except Exception`` handlers, one at
    every step where app code runs, each turning a crash into a per-item
    ``EVALUATION_FAILED`` so that one bad item cannot sink a batch of twenty.

    If any of them ever caught cancellation too, the result would be worse than a hang:
    the resolver would work through the remaining items and produce a full,
    confident-looking ``200`` for a request nobody is listening to, with the cancelled
    item reported as "could not check" -- which a client reads as "ask again" and renders
    as available.

    This holds today, but not for a reason the source states anywhere: ``CancelledError``
    inherits from ``BaseException``, not ``Exception`` (changed in Python 3.8 precisely so
    broad handlers stop swallowing it). Turning a single ``except Exception`` into
    ``except BaseException`` -- which reads like harmless extra defensiveness -- silently
    reintroduces the whole problem. Each isolation point therefore gets its own case
    rather than one case standing in for all three.

    What is asserted is the invariant, not a status code: no per-item verdict is
    produced. The status code is deliberately left loose because the chain that
    produces it was easy to get wrong, and an earlier version of this docstring did:
    it claimed the ``500`` was a ``TestClient`` artifact and that a real ASGI server
    would simply have nobody left to answer.

    Traced instead of assumed, and it is neither. The ``500`` carries
    ``{"detail": "Internal server error"}`` -- the body of this adapter's own
    ``_CatchAllErrorsMiddleware`` -- and it appears with ``raise_server_exceptions``
    set either way, so ``TestClient`` is not what produces it. Our middleware
    catches ``Exception``, not ``BaseException``, so it does not see a
    ``CancelledError`` directly; what reaches it is what Starlette's
    ``BaseHTTPMiddleware`` hands over once the inner task has failed. The practical
    upshot for a real deployment is the same shape: the request ends as a
    whole-request error, not as an answer.

    Also worth stating plainly: these tests raise ``CancelledError`` from app code
    rather than cancelling a real task. That exercises the handler chain -- which is
    where the regression would live -- but it is not a real client disconnect, and
    nothing here claims to test one.
    """

    @staticmethod
    def _batch() -> dict[str, object]:
        return {
            "version": 1,
            "items": [
                {"operation": "GET /actions/ping", "params": {}},
                {"operation": "POST /actions/cancel-order", "params": {"order_id": 7}},
                {"operation": "GET /actions/ping", "params": {}},
            ],
        }

    @staticmethod
    def _assert_no_verdicts_were_produced(response: object) -> None:
        status = response.status_code  # type: ignore[attr-defined]
        assert status != 200, f"a cancelled request answered with {status}"
        assert "results" not in response.text  # type: ignore[attr-defined]

    def _adapter(self) -> FastApiAdapter:
        auth = AsyncMock()
        auth.process.return_value = _manager_context()
        return FastApiAdapter(machine=ActionProductMachine(loggers=[]), auth_coordinator=auth)

    def test_cancellation_inside_a_params_mapper_does_not_become_a_verdict(self) -> None:
        def cancelling_mapper(body: object) -> object:
            raise asyncio.CancelledError

        adapter = self._adapter()
        adapter.post("/actions/cancel-order", CancelOrderAction, params_mapper=cancelling_mapper)
        adapter.get("/actions/ping", PingAction)
        client = TestClient(adapter.build(), raise_server_exceptions=False)

        self._assert_no_verdicts_were_produced(client.post("/permissions/resolve", json=self._batch()))

    def test_cancellation_inside_a_route_auth_coordinator_does_not_become_a_verdict(self) -> None:
        route_auth = AsyncMock()
        route_auth.process.side_effect = asyncio.CancelledError

        adapter = self._adapter()
        adapter.post("/actions/cancel-order", CancelOrderAction, auth_coordinator=route_auth)
        adapter.get("/actions/ping", PingAction)
        client = TestClient(adapter.build(), raise_server_exceptions=False)

        self._assert_no_verdicts_were_produced(client.post("/permissions/resolve", json=self._batch()))

    def test_cancellation_inside_access_decide_does_not_become_a_verdict(self) -> None:
        """The deepest of the three: app code inside the check itself, wrapped by
        ``ActionProductMachine.check_access_decide``'s own ``except Exception``.
        """
        adapter = self._adapter()
        adapter.post("/actions/cancel-order", CancelOrderAction)
        adapter.get("/actions/ping", PingAction)
        client = TestClient(adapter.build(), raise_server_exceptions=False)

        async def cancelling_access_decide(*_args: object, **_kwargs: object) -> object:
            raise asyncio.CancelledError

        with patch.object(CancelOrderAction, "access_decide", cancelling_access_decide):
            self._assert_no_verdicts_were_produced(client.post("/permissions/resolve", json=self._batch()))

    def test_an_ordinary_crash_in_the_same_place_is_still_isolated(self) -> None:
        """The control case. Without it the three above would still pass against a
        resolver with no per-item isolation at all -- "nothing was answered" proves
        nothing unless an ordinary exception provably DOES get answered, in place,
        without disturbing its neighbours.
        """

        def exploding_mapper(body: object) -> object:
            raise RuntimeError("ordinary crash")

        adapter = self._adapter()
        adapter.post("/actions/cancel-order", CancelOrderAction, params_mapper=exploding_mapper)
        adapter.get("/actions/ping", PingAction)
        client = TestClient(adapter.build(), raise_server_exceptions=False)

        response = client.post("/permissions/resolve", json=self._batch())

        assert response.status_code == 200
        assert response.json()["results"] == [
            {"kind": "AllowedVerdict"},
            {"kind": "FailErrorVerdict", "reason": "EVALUATION_FAILED"},
            {"kind": "AllowedVerdict"},
        ]
