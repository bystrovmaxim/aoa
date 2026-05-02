# tests/adapters/fastapi/test_fastapi_adapter.py
"""
Tests for ``FastApiAdapter`` — HTTP binding for ``ActionProductMachine``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Verify registration (``post``/``get``/``put``/``delete``/``patch``), fluent
return of ``self``, ``build()`` producing a ``FastAPI`` app with ``/health`` and
exception handlers, OpenAPI metadata (title/version), and ``FastApiRouteRecord``
fields (tags, summary from ``@meta``, custom descriptions).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    TestClient / direct adapter inspection
              |
              v
    FastApiAdapter(BaseAdapter[FastApiRouteRecord])
              |
              +--> register HTTP method + path + action -> ``_routes``
              |
              v
    build() -> FastAPI app (+ auto /health, error handlers)

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``auth_coordinator`` is always provided in tests (``AsyncMock``).
- Each protocol method appends a ``FastApiRouteRecord`` and returns ``self``.

"""

from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from action_machine.integrations.fastapi.adapter import FastApiAdapter
from action_machine.integrations.fastapi.route_record import FastApiRouteRecord
from action_machine.runtime.action_product_machine import ActionProductMachine
from tests.scenarios.domain_model import PingAction, SimpleAction

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _make_adapter(**kwargs) -> FastApiAdapter:
    """Create a FastApiAdapter with sensible test defaults."""
    machine = ActionProductMachine(mode="test")
    auth = AsyncMock()
    auth.process.return_value = None
    return FastApiAdapter(
        machine=machine,
        auth_coordinator=auth,
        gate_coordinator=machine.gate_coordinator,
        title=kwargs.get("title", "Test API"),
        version=kwargs.get("version", "0.0.1"),
        description=kwargs.get("description", ""),
    )


# ═════════════════════════════════════════════════════════════════════════════
# Constructor and properties
# ═════════════════════════════════════════════════════════════════════════════


class TestConstructor:
    """Verify adapter construction and metadata properties."""

    def test_title_stored(self) -> None:
        """Title passed to constructor is accessible via property."""
        adapter = _make_adapter(title="Orders API")
        assert adapter.title == "Orders API"

    def test_version_stored(self) -> None:
        """Version passed to constructor is accessible via property."""
        adapter = _make_adapter(version="2.0.0")
        assert adapter.version == "2.0.0"

    def test_description_stored(self) -> None:
        """Description passed to constructor is accessible via property."""
        adapter = _make_adapter(description="My API description")
        assert adapter.api_description == "My API description"

    def test_routes_empty_initially(self) -> None:
        """No routes registered immediately after construction."""
        adapter = _make_adapter()
        assert adapter.routes == []


# ═════════════════════════════════════════════════════════════════════════════
# Route registration
# ═════════════════════════════════════════════════════════════════════════════


class TestRouteRegistration:
    """Verify that protocol methods register correct route records."""

    def test_post_registers_route(self) -> None:
        """post() adds a route record with method=POST."""
        adapter = _make_adapter()
        adapter.post("/orders", PingAction)

        assert len(adapter.routes) == 1
        assert adapter.routes[0].method == "POST"
        assert adapter.routes[0].path == "/orders"
        assert adapter.routes[0].action_class is PingAction

    def test_get_registers_route(self) -> None:
        """get() adds a route record with method=GET."""
        adapter = _make_adapter()
        adapter.get("/ping", PingAction)

        assert len(adapter.routes) == 1
        assert adapter.routes[0].method == "GET"

    def test_put_registers_route(self) -> None:
        """put() adds a route record with method=PUT."""
        adapter = _make_adapter()
        adapter.put("/orders", SimpleAction)

        assert adapter.routes[0].method == "PUT"

    def test_delete_registers_route(self) -> None:
        """delete() adds a route record with method=DELETE."""
        adapter = _make_adapter()
        adapter.delete("/orders/{id}", PingAction)

        assert adapter.routes[0].method == "DELETE"

    def test_patch_registers_route(self) -> None:
        """patch() adds a route record with method=PATCH."""
        adapter = _make_adapter()
        adapter.patch("/orders/{id}", SimpleAction)

        assert adapter.routes[0].method == "PATCH"

    def test_tags_passed_to_record(self) -> None:
        """Tags are converted to a tuple and stored on the route record."""
        adapter = _make_adapter()
        adapter.post("/orders", PingAction, tags=["orders", "create"])

        assert adapter.routes[0].tags == ("orders", "create")

    def test_summary_passed_to_record(self) -> None:
        """Explicit summary is stored on the route record."""
        adapter = _make_adapter()
        adapter.post("/orders", PingAction, summary="Create order")

        assert adapter.routes[0].summary == "Create order"

    def test_auto_summary_from_meta(self) -> None:
        """When summary is empty, description from @meta is used as summary."""
        adapter = _make_adapter()
        adapter.post("/ping", PingAction)

        # PingAction has @meta(description="Service health check")
        assert adapter.routes[0].summary != ""

    def test_operation_id_passed(self) -> None:
        """Custom operation_id is stored on the route record."""
        adapter = _make_adapter()
        adapter.post("/ping", PingAction, operation_id="do_ping")

        assert adapter.routes[0].operation_id == "do_ping"

    def test_deprecated_flag_passed(self) -> None:
        """Deprecated flag is stored on the route record."""
        adapter = _make_adapter()
        adapter.post("/old", PingAction, deprecated=True)

        assert adapter.routes[0].deprecated is True


# ═════════════════════════════════════════════════════════════════════════════
# Fluent chaining
# ═════════════════════════════════════════════════════════════════════════════


class TestFluentChain:
    """Verify that protocol methods return self for chaining."""

    def test_post_returns_self(self) -> None:
        """post() returns the same adapter instance."""
        adapter = _make_adapter()
        result = adapter.post("/a", PingAction)
        assert result is adapter

    def test_chained_registration(self) -> None:
        """Multiple methods can be chained in a single expression."""
        adapter = _make_adapter()

        result = (
            adapter
            .get("/ping", PingAction, tags=["system"])
            .post("/orders", SimpleAction, tags=["orders"])
            .delete("/orders/{id}", PingAction, tags=["orders"])
        )

        assert result is adapter
        assert len(adapter.routes) == 3
        assert adapter.routes[0].method == "GET"
        assert adapter.routes[1].method == "POST"
        assert adapter.routes[2].method == "DELETE"


# ═════════════════════════════════════════════════════════════════════════════
# build() and FastAPI app
# ═════════════════════════════════════════════════════════════════════════════


class TestBuild:
    """Verify that build() produces a valid FastAPI application."""

    def test_returns_fastapi_instance(self) -> None:
        """build() returns a FastAPI object."""
        adapter = _make_adapter()
        adapter.post("/ping", PingAction)
        app = adapter.build()

        assert isinstance(app, FastAPI)

    def test_app_title(self) -> None:
        """The built app carries the title from the adapter."""
        adapter = _make_adapter(title="My API")
        app = adapter.build()

        assert app.title == "My API"

    def test_app_version(self) -> None:
        """The built app carries the version from the adapter."""
        adapter = _make_adapter(version="3.0.0")
        app = adapter.build()

        assert app.version == "3.0.0"


# ═════════════════════════════════════════════════════════════════════════════
# Health check
# ═════════════════════════════════════════════════════════════════════════════


class TestHealthCheck:
    """Verify the automatic GET /health endpoint."""

    def test_health_returns_ok(self) -> None:
        """GET /health returns 200 with {"status": "ok"}."""
        adapter = _make_adapter()
        app = adapter.build()
        client = TestClient(app)

        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


# ═════════════════════════════════════════════════════════════════════════════
# Route record type
# ═════════════════════════════════════════════════════════════════════════════


class TestRouteRecordType:
    """Verify that registered routes are FastApiRouteRecord instances."""

    def test_route_is_fastapi_record(self) -> None:
        """Each registered route is a FastApiRouteRecord."""
        adapter = _make_adapter()
        adapter.post("/ping", PingAction)

        assert isinstance(adapter.routes[0], FastApiRouteRecord)
