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

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from starlette.middleware.gzip import GZipMiddleware

from aoa.action_machine.auth.guest_role import GuestRole
from aoa.action_machine.context.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.fastapi.adapter import FastApiAdapter
from aoa.fastapi.manifest import Manifest
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
        assert body["version"] == 1
        assert body["manifest_schema_version"] == 2
        assert body["manifest_version"].startswith("sha256:")
        assert set(body["schemas"].keys()) == {
            "ResolveRequest",
            "ResolveResponse",
            "BaseVerdict",
            "ErrorEnvelope",
            "Manifest",
        }
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


class TestClientManifestHttpContract:
    """ETag/Cache-Control headers and If-None-Match conditional GET (chapter 3.5, task 6)."""

    def test_etag_is_the_quoted_manifest_version(self) -> None:
        client = _make_client(context=_manager_context())

        response = client.get("/client-manifest.json")

        assert response.headers["etag"] == f'"{response.json()["manifest_version"]}"'

    def test_cache_control_is_private_no_cache(self) -> None:
        client = _make_client(context=_manager_context())

        response = client.get("/client-manifest.json")

        assert response.headers["cache-control"] == "private, no-cache"

    def test_matching_if_none_match_returns_304_with_no_body(self) -> None:
        client = _make_client(context=_manager_context())
        etag = client.get("/client-manifest.json").headers["etag"]

        response = client.get("/client-manifest.json", headers={"If-None-Match": etag})

        assert response.status_code == 304
        assert response.content == b""
        assert response.headers["etag"] == etag

    def test_wildcard_if_none_match_returns_304(self) -> None:
        client = _make_client(context=_manager_context())

        response = client.get("/client-manifest.json", headers={"If-None-Match": "*"})

        assert response.status_code == 304

    def test_non_matching_if_none_match_returns_200_with_body(self) -> None:
        client = _make_client(context=_manager_context())

        response = client.get("/client-manifest.json", headers={"If-None-Match": '"sha256:stale"'})

        assert response.status_code == 200
        assert response.json()["manifest_version"].startswith("sha256:")

    def test_absent_if_none_match_returns_200(self) -> None:
        client = _make_client(context=_manager_context())

        response = client.get("/client-manifest.json")

        assert response.status_code == 200

    def test_200_to_304_to_200_round_trip_across_a_real_content_change(self) -> None:
        """A real ETag from a real manifest; a real content change moves it; the stale one gets 200 again."""
        auth = AsyncMock()
        auth.process.return_value = _manager_context()

        before_adapter = FastApiAdapter(machine=ActionProductMachine(loggers=[]), auth_coordinator=auth)
        before_adapter.get("/actions/ping", PingAction)
        before_client = TestClient(before_adapter.build())

        first = before_client.get("/client-manifest.json")
        assert first.status_code == 200
        first_etag = first.headers["etag"]

        # Same client, same ETag: still fresh -> 304.
        still_fresh = before_client.get("/client-manifest.json", headers={"If-None-Match": first_etag})
        assert still_fresh.status_code == 304

        # A real deploy that changes the registered routes -> a genuinely different manifest.
        after_adapter = FastApiAdapter(machine=ActionProductMachine(loggers=[]), auth_coordinator=auth)
        after_adapter.get("/actions/ping", PingAction)
        after_adapter.post("/actions/cancel-order", CancelOrderAction)
        after_client = TestClient(after_adapter.build())

        second = after_client.get("/client-manifest.json")
        assert second.status_code == 200
        second_etag = second.headers["etag"]
        assert second_etag != first_etag

        # The old, now-stale ETag no longer matches the new manifest -> 200, not 304.
        stale_now = after_client.get("/client-manifest.json", headers={"If-None-Match": first_etag})
        assert stale_now.status_code == 200
        assert stale_now.headers["etag"] == second_etag

        # The new ETag is fresh against the new manifest -> 304.
        fresh_now = after_client.get("/client-manifest.json", headers={"If-None-Match": second_etag})
        assert fresh_now.status_code == 304


class TestClientManifestPrecomputed:
    """Audit finding 8: the response body is serialized once at build(), not per request."""

    def test_model_dump_runs_once_at_build_not_per_request(self) -> None:
        auth = AsyncMock()
        auth.process.return_value = _manager_context()
        adapter = FastApiAdapter(machine=ActionProductMachine(loggers=[]), auth_coordinator=auth)
        adapter.get("/actions/ping", PingAction)

        with patch.object(Manifest, "model_dump", side_effect=Manifest.model_dump, autospec=True) as spy:
            app = adapter.build()
            assert spy.call_count == 1  # the precomputed JSONResponse is built here

            client = TestClient(app)
            for _ in range(3):
                response = client.get("/client-manifest.json")
                assert response.status_code == 200

            assert spy.call_count == 1  # unchanged -- no request re-serialized the catalog

    def test_repeated_requests_return_identical_content(self) -> None:
        """The precomputed JSON bytes are reused verbatim, not re-serialized per request --
        but each request gets its own Response object (audit finding 2, see the class below)."""
        client = _make_client(context=_manager_context())

        first = client.get("/client-manifest.json")
        second = client.get("/client-manifest.json")

        assert first.content == second.content
        assert first.headers["etag"] == second.headers["etag"]


class TestClientManifestNotSharedAcrossRequests:
    """Audit finding 2: a Response object must never be reused across requests.

    ``Response.raw_headers`` is a plain mutable list, and ``Response.__call__``
    hands that exact list, by reference, into the ASGI ``"http.response.start"``
    message. Middleware that rewrites headers in place (``GZipMiddleware``, via
    ``MutableHeaders(raw=message["headers"])`` aliasing that same list) would
    permanently mutate a shared instance's headers -- for every future request,
    not just the one being compressed. This reproduces exactly that scenario.
    """

    def test_gzip_middleware_does_not_leak_content_encoding_to_later_requests(self) -> None:
        auth = AsyncMock()
        auth.process.return_value = _manager_context()
        adapter = FastApiAdapter(machine=ActionProductMachine(loggers=[]), auth_coordinator=auth)
        adapter.get("/actions/ping", PingAction)
        app = adapter.build()
        app.add_middleware(GZipMiddleware, minimum_size=0)  # compress every response, however small
        client = TestClient(app)

        # First caller supports gzip -- the manifest response is compressed.
        compressed = client.get("/client-manifest.json", headers={"Accept-Encoding": "gzip"})
        assert compressed.status_code == 200
        assert compressed.headers.get("content-encoding") == "gzip"

        # Second caller does not send Accept-Encoding at all -- httpx's default
        # transport still auto-decodes a gzip body if the server claims one, so
        # request with a raw client that will not decode for us, to observe the
        # server's actual bytes and headers unfiltered.
        with TestClient(app, headers={}) as raw_client:
            plain = raw_client.get(
                "/client-manifest.json",
                headers={"Accept-Encoding": "identity"},
                extensions={},
            )
        assert plain.status_code == 200
        # A leaked header from the first, compressed response would show up here
        # even though this request never asked for (or received) compression.
        assert plain.headers.get("content-encoding") is None
        # The body must be plain, readable JSON -- not bytes gzip actually wrote,
        # and not raw JSON mislabeled as gzip (which is what the bug produced).
        assert plain.json()["version"] >= 1


class TestReservedManifestPath:
    """Registering an app action on the catalog path fails fast, not silently."""

    def test_registering_an_action_on_the_manifest_path_raises(self) -> None:
        adapter = FastApiAdapter(machine=ActionProductMachine(loggers=[]), auth_coordinator=AsyncMock())

        # Without the reserved-path guard this would silently shadow the catalog
        # (or be shadowed by it) instead of failing at registration.
        with pytest.raises(ReservedRoutePathError):
            adapter.get("/client-manifest.json", PingAction)
