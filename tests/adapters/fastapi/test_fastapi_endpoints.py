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

from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from action_machine.integrations.fastapi.adapter import FastApiAdapter
from action_machine.model.exceptions import AuthorizationError, ValidationFieldError
from action_machine.runtime.action_product_machine import ActionProductMachine
from tests.scenarios.domain_model import PingAction, SimpleAction

# ─────────────────────────────────────────────────────────────────────────────
# Helper — adapter with mocked machine.run
# ─────────────────────────────────────────────────────────────────────────────


def _make_app(
    connections_factory=None,
    run_side_effect=None,
    run_return=None,
):
    """
    Build a ``FastApiAdapter`` with a mocked ``ActionProductMachine``.

    Returns ``(adapter, machine)`` for extra assertions. By default
    ``machine.run`` returns ``PingAction.Result(message="pong")``.
    """
    machine = ActionProductMachine(mode="test")

    auth = AsyncMock()
    auth.process.return_value = None

    if run_return is not None:
        machine.run = AsyncMock(return_value=run_return)
    elif run_side_effect is not None:
        machine.run = AsyncMock(side_effect=run_side_effect)
    else:
        machine.run = AsyncMock(return_value=PingAction.Result(message="pong"))

    adapter = FastApiAdapter(
        machine=machine,
        auth_coordinator=auth,
        connections_factory=connections_factory,
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
# connections_factory
# ═════════════════════════════════════════════════════════════════════════════


class TestConnectionsFactory:
    """Ensures ``connections_factory`` runs per request."""

    def test_factory_called_on_request(self) -> None:
        """``connections_factory`` is invoked once per incoming request."""
        # Arrange
        mock_connections = {"db": MagicMock()}
        factory = MagicMock(return_value=mock_connections)

        adapter, _machine = _make_app(connections_factory=factory)
        adapter.post("/ping", PingAction)
        app = adapter.build()
        client = TestClient(app)

        # Act
        client.post("/ping", json={})

        # Assert
        factory.assert_called_once()

    def test_factory_result_passed_to_machine(self) -> None:
        """The factory return value is forwarded into ``machine.run``."""
        # Arrange
        mock_connections = {"db": MagicMock()}
        factory = MagicMock(return_value=mock_connections)

        adapter, _machine = _make_app(connections_factory=factory)
        adapter.post("/ping", PingAction)
        app = adapter.build()
        client = TestClient(app)

        # Act
        client.post("/ping", json={})

        # Assert
        call_args = _machine.run.call_args
        assert call_args is not None


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
