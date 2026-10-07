# tests/adapters/fastapi/test_fastapi_endpoints.py
"""
FastApiAdapter endpoint generation strategies.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``FastApiAdapter`` picks one of three shapes for the generated route handler:

1. POST/PUT/PATCH with non-empty ``Params`` → JSON body.
2. GET/DELETE with non-empty ``Params`` → query/path parameters.
3. Any HTTP method with empty ``Params`` (no fields) → no request parameters.

``test_fastapi_adapter.py`` mostly exercises POST. This module targets the
remaining branches in ``adapter.py`` (query and no-param endpoints, plus
registered exception handlers).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    TestClient  ->  built FastAPI app  <-  FastApiAdapter.build()
                           |
                           v
                    AsyncMock machine.run
                           |
              +------------+-------------+
              |                          |
        success (Result)          AuthorizationError / ValidationFieldError
              |                          |
         HTTP 200                   HTTP 403 / 422 (handlers)

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``auth_coordinator`` is always provided (here: ``AsyncMock``).
- Error payloads surfaced to the client must match the strings raised inside
  ``machine.run`` for assertion stability.

"""

from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from aoa.action_machine.context.context import Context
from aoa.action_machine.exceptions import AuthorizationError, ValidationFieldError
from aoa.action_machine.resources.per_call_connection import PerCallConnection
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.fastapi.adapter import FastApiAdapter

from .support import DummyResourceManager, PingAction, SimpleAction

# ─────────────────────────────────────────────────────────────────────────────
# Helper — adapter with mocked machine.run
# ─────────────────────────────────────────────────────────────────────────────


def _make_app(
    run_side_effect=None,
    run_return=None,
):
    """
    Build a ``FastApiAdapter`` with a mocked ``ActionProductMachine``.

    Returns ``(adapter, machine)`` for extra assertions. By default
    ``machine.run`` returns ``PingAction.Result(message="pong")``.
    """
    machine = ActionProductMachine(loggers=[])

    auth = AsyncMock()
    auth.process.return_value = Context()

    if run_return is not None:
        machine.run = AsyncMock(return_value=run_return)
    elif run_side_effect is not None:
        machine.run = AsyncMock(side_effect=run_side_effect)
    else:
        machine.run = AsyncMock(return_value=PingAction.Result(message="pong"))

    adapter = FastApiAdapter(
        machine=machine,
        auth_coordinator=auth,
    )
    return adapter, machine


# ═════════════════════════════════════════════════════════════════════════════
# GET with query parameters (strategy 2)
# ═════════════════════════════════════════════════════════════════════════════


class TestGetWithQueryParams:
    """Covers query-parameter endpoints for GET/DELETE with non-empty Params."""

    def test_get_extracts_query_params(self) -> None:
        """GET reads fields from the query string and returns 200."""
        # Arrange — SimpleAction.Params has required field ``name``
        adapter, _machine = _make_app(
            run_return=SimpleAction.Result(greeting="Hello, Alice!"),
        )
        adapter.get("/simple", SimpleAction)
        app = adapter.build()
        client = TestClient(app)

        # Act
        response = client.get("/simple?name=Alice")

        # Assert
        assert response.status_code == 200
        _machine.run.assert_called_once()

    def test_delete_extracts_query_params(self) -> None:
        """DELETE uses the same query-parameter strategy."""
        # Arrange
        adapter, _machine = _make_app(
            run_return=SimpleAction.Result(greeting="Deleted"),
        )
        adapter.delete("/simple", SimpleAction)
        app = adapter.build()
        client = TestClient(app)

        # Act
        response = client.delete("/simple?name=test")

        # Assert
        assert response.status_code == 200


# ═════════════════════════════════════════════════════════════════════════════
# GET with empty Params (strategy 3)
# ═════════════════════════════════════════════════════════════════════════════


class TestGetEmptyParams:
    """Covers no-parameter endpoints when Params has no fields."""

    def test_get_no_params(self) -> None:
        """GET works without query parameters when Params is empty."""
        # Arrange — PingAction.Params has no fields
        adapter, _machine = _make_app()
        adapter.get("/ping", PingAction)
        app = adapter.build()
        client = TestClient(app)

        # Act
        response = client.get("/ping")

        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == "pong"

    def test_post_no_params(self) -> None:
        """POST accepts an empty JSON body when Params is empty."""
        # Arrange
        adapter, _machine = _make_app()
        adapter.post("/ping", PingAction)
        app = adapter.build()
        client = TestClient(app)

        # Act
        response = client.post("/ping", json={})

        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == "pong"


# ═════════════════════════════════════════════════════════════════════════════
# Per-route connections
# ═════════════════════════════════════════════════════════════════════════════


class TestPerRouteConnections:
    """``connections`` on each route resolve into ``machine.run``."""

    def test_connections_passed_to_machine_run(self) -> None:
        res = DummyResourceManager()
        adapter, machine = _make_app()
        adapter.post("/ping", PingAction, connections={"db": res})
        app = adapter.build()
        client = TestClient(app)

        client.post("/ping", json={})

        _args, _kwargs = machine.run.call_args
        assert _args[3] == {"db": res}

    def test_per_call_connection_factory_each_request(self) -> None:
        res = DummyResourceManager()
        calls: list[int] = []

        def factory() -> DummyResourceManager:
            calls.append(1)
            return res

        adapter, machine = _make_app()
        adapter.post("/ping", PingAction, connections={"db": PerCallConnection(factory)})
        app = adapter.build()
        client = TestClient(app)

        client.post("/ping", json={})
        client.post("/ping", json={})

        assert calls == [1, 1]
        _args1, _ = machine.run.call_args_list[0]
        _args2, _ = machine.run.call_args_list[1]
        assert _args1[3]["db"] is res
        assert _args2[3]["db"] is res

    def test_two_routes_get_distinct_connections(self) -> None:
        res_a = DummyResourceManager()
        res_b = DummyResourceManager()
        adapter, machine = _make_app()
        adapter.post("/a", PingAction, connections={"svc": res_a})
        adapter.post("/b", PingAction, connections={"svc": res_b})
        app = adapter.build()
        client = TestClient(app)

        client.post("/a", json={})
        client.post("/b", json={})

        a_conn = machine.run.call_args_list[0][0][3]
        b_conn = machine.run.call_args_list[1][0][3]
        assert a_conn == {"svc": res_a}
        assert b_conn == {"svc": res_b}

    def test_no_connections_means_none(self) -> None:
        adapter, machine = _make_app()
        adapter.post("/ping", PingAction)
        app = adapter.build()
        client = TestClient(app)

        client.post("/ping", json={})

        assert machine.run.call_args[0][3] is None


# ═════════════════════════════════════════════════════════════════════════════
# Exception handlers
# ═════════════════════════════════════════════════════════════════════════════


class TestExceptionHandlers:
    """Maps ``AuthorizationError`` → 403 and ``ValidationFieldError`` → 422."""

    def test_authorization_error_returns_403(self) -> None:
        """``AuthorizationError`` from ``machine.run`` becomes HTTP 403."""
        # Arrange
        adapter, _ = _make_app(
            run_side_effect=AuthorizationError("access denied"),
        )
        adapter.post("/ping", PingAction)
        app = adapter.build()
        client = TestClient(app, raise_server_exceptions=False)

        # Act
        response = client.post("/ping", json={})

        # Assert
        assert response.status_code == 403
        assert "access denied" in response.json()["detail"]

    def test_validation_error_returns_422(self) -> None:
        """``ValidationFieldError`` from ``machine.run`` becomes HTTP 422."""
        # Arrange
        adapter, _ = _make_app(
            run_side_effect=ValidationFieldError("field is invalid", "name"),
        )
        adapter.post("/ping", PingAction)
        app = adapter.build()
        client = TestClient(app, raise_server_exceptions=False)

        # Act
        response = client.post("/ping", json={})

        # Assert
        assert response.status_code == 422
        assert response.json()["detail"] == "field is invalid"

    def test_unhandled_error_returns_500_from_catch_all_middleware(self) -> None:
        """Unhandled exceptions are converted to a generic HTTP 500 payload."""
        # Arrange
        adapter, _ = _make_app(
            run_side_effect=RuntimeError("unexpected boom"),
        )
        adapter.post("/ping", PingAction)
        app = adapter.build()
        client = TestClient(app, raise_server_exceptions=False)

        # Act
        response = client.post("/ping", json={})

        # Assert
        assert response.status_code == 500
        assert response.json() == {"detail": "Internal server error"}


# ═════════════════════════════════════════════════════════════════════════════
# Per-route auth_coordinator override
# ═════════════════════════════════════════════════════════════════════════════


class TestPerRouteAuthCoordinatorOverride:
    """A route's ``auth_coordinator=`` overrides the adapter-wide default coordinator."""

    def test_route_override_allows_when_adapter_default_denies(self) -> None:
        """Adapter default denies (``process`` -> ``None``); the overridden route's own coordinator allows."""
        # Arrange
        machine = ActionProductMachine(loggers=[])
        machine.run = AsyncMock(return_value=PingAction.Result(message="pong"))

        denying_auth = AsyncMock()
        denying_auth.process.return_value = None
        allowing_auth = AsyncMock()
        allowing_auth.process.return_value = Context()

        adapter = FastApiAdapter(machine=machine, auth_coordinator=denying_auth)
        adapter.post("/open", PingAction, auth_coordinator=allowing_auth)
        adapter.post("/protected", PingAction)
        app = adapter.build()
        client = TestClient(app, raise_server_exceptions=False)

        # Act
        open_response = client.post("/open", json={})
        protected_response = client.post("/protected", json={})

        # Assert
        assert open_response.status_code == 200
        assert protected_response.status_code == 403
        allowing_auth.process.assert_called_once()
        denying_auth.process.assert_called_once()

    def test_no_override_falls_back_to_adapter_default(self) -> None:
        """No ``auth_coordinator=`` on the route -> the adapter's default coordinator handles it."""
        # Arrange
        machine = ActionProductMachine(loggers=[])
        machine.run = AsyncMock(return_value=PingAction.Result(message="pong"))

        default_auth = AsyncMock()
        default_auth.process.return_value = Context()

        adapter = FastApiAdapter(machine=machine, auth_coordinator=default_auth)
        adapter.post("/ping", PingAction)
        app = adapter.build()
        client = TestClient(app)

        # Act
        response = client.post("/ping", json={})

        # Assert
        assert response.status_code == 200
        default_auth.process.assert_called_once()
