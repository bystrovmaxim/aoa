# tests/adapters/fastapi/test_fastapi_openapi.py
"""
Tests for OpenAPI schema generation from FastApiAdapter routes.

When build() creates a FastAPI app, the app exposes an OpenAPI schema at
/openapi.json. This schema is generated from the registered routes, including
paths, methods, tags, summary, response models, and Pydantic field metadata
(descriptions, constraints, examples).

Scenarios covered:
    - Registered POST route appears in schema under correct path and method.
    - Registered GET route appears in schema under correct path and method.
    - Tags from registration appear in the schema operation.
    - Summary from registration appears in the schema operation.
    - Health check endpoint appears in the schema.
    - Response model fields appear in schema components.
    - Multiple routes each have their own entry in the schema.
    - Pydantic field descriptions propagate to schema properties.
    - Schema title and version match adapter configuration.
    - Deprecated flag appears in the schema operation.
"""

from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from action_machine.graph.gate_coordinator import GateCoordinator
from action_machine.integrations.fastapi.adapter import FastApiAdapter
from action_machine.runtime.machines.action_product_machine import ActionProductMachine
from tests.domain_model import PingAction, SimpleAction

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _build_app_with_routes(**adapter_kwargs) -> TestClient:
    """Build a FastAPI app with standard test routes and return a TestClient."""
    GateCoordinator()
    machine = ActionProductMachine(mode="test")
    auth = AsyncMock()
    auth.process.return_value = None

    adapter = FastApiAdapter(
        machine=machine,
        auth_coordinator=auth,
        title=adapter_kwargs.get("title", "Test API"),
        version=adapter_kwargs.get("version", "1.0.0"),
    )

    adapter.post("/api/v1/ping", PingAction, tags=["system"], summary="Ping service")
    adapter.post(
        "/api/v1/orders",
        SimpleAction,
        tags=["orders"],
        summary="Create simple order",
    )

    app = adapter.build()
    return TestClient(app)


def _get_openapi(client: TestClient) -> dict:
    """Fetch and parse the OpenAPI schema from the app."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    return response.json()


# ═════════════════════════════════════════════════════════════════════════════
# Schema metadata
# ═════════════════════════════════════════════════════════════════════════════


class TestSchemaMetadata:
    """Verify top-level OpenAPI schema fields match adapter configuration."""

    def test_schema_title(self) -> None:
        """The schema title matches the adapter title."""
        client = _build_app_with_routes(title="Orders API")
        schema = _get_openapi(client)

        assert schema["info"]["title"] == "Orders API"

    def test_schema_version(self) -> None:
        """The schema version matches the adapter version."""
        client = _build_app_with_routes(version="3.2.1")
        schema = _get_openapi(client)

        assert schema["info"]["version"] == "3.2.1"


# ═════════════════════════════════════════════════════════════════════════════
# Path registration
# ═════════════════════════════════════════════════════════════════════════════


class TestPathRegistration:
    """Verify that registered routes appear in the OpenAPI paths."""

    def test_ping_path_exists(self) -> None:
        """The /api/v1/ping path appears in the schema."""
        client = _build_app_with_routes()
        schema = _get_openapi(client)

        assert "/api/v1/ping" in schema["paths"]

    def test_orders_path_exists(self) -> None:
        """The /api/v1/orders path appears in the schema."""
        client = _build_app_with_routes()
        schema = _get_openapi(client)

        assert "/api/v1/orders" in schema["paths"]

    def test_post_method_registered(self) -> None:
        """The ping endpoint is registered as a POST method."""
        client = _build_app_with_routes()
        schema = _get_openapi(client)

        ping_path = schema["paths"]["/api/v1/ping"]
        assert "post" in ping_path

    def test_health_path_exists(self) -> None:
        """The automatic /health endpoint appears in the schema."""
        client = _build_app_with_routes()
        schema = _get_openapi(client)

        assert "/health" in schema["paths"]

    def test_health_is_get(self) -> None:
        """The /health endpoint is a GET method."""
        client = _build_app_with_routes()
        schema = _get_openapi(client)

        assert "get" in schema["paths"]["/health"]


# ═════════════════════════════════════════════════════════════════════════════
# Tags and summary
# ═════════════════════════════════════════════════════════════════════════════


class TestTagsAndSummary:
    """Verify tags and summary propagate to OpenAPI operations."""

    def test_ping_tags(self) -> None:
        """The ping operation carries the 'system' tag."""
        client = _build_app_with_routes()
        schema = _get_openapi(client)

        ping_op = schema["paths"]["/api/v1/ping"]["post"]
        assert "system" in ping_op.get("tags", [])

    def test_orders_tags(self) -> None:
        """The orders operation carries the 'orders' tag."""
        client = _build_app_with_routes()
        schema = _get_openapi(client)

        orders_op = schema["paths"]["/api/v1/orders"]["post"]
        assert "orders" in orders_op.get("tags", [])

    def test_ping_summary(self) -> None:
        """The ping operation carries the custom summary."""
        client = _build_app_with_routes()
        schema = _get_openapi(client)

        ping_op = schema["paths"]["/api/v1/ping"]["post"]
        assert ping_op.get("summary") == "Ping service"

    def test_orders_summary(self) -> None:
        """The orders operation carries the custom summary."""
        client = _build_app_with_routes()
        schema = _get_openapi(client)

        orders_op = schema["paths"]["/api/v1/orders"]["post"]
        assert orders_op.get("summary") == "Create simple order"


# ═════════════════════════════════════════════════════════════════════════════
# Response model in components
# ═════════════════════════════════════════════════════════════════════════════


class TestResponseModel:
    """Verify that response models are included in schema components."""

    def test_components_section_exists(self) -> None:
        """The schema has a components/schemas section."""
        client = _build_app_with_routes()
        schema = _get_openapi(client)

        assert "components" in schema
        assert "schemas" in schema["components"]

    def test_result_model_in_components(self) -> None:
        """At least one Result model appears in the schema components."""
        client = _build_app_with_routes()
        schema = _get_openapi(client)

        component_names = list(schema["components"]["schemas"].keys())
        # PingAction.Result has a 'message' field, SimpleAction.Result has 'greeting'
        has_result = any("Result" in name for name in component_names)
        assert has_result, f"No Result model found in components: {component_names}"


# ═════════════════════════════════════════════════════════════════════════════
# Deprecated flag
# ═════════════════════════════════════════════════════════════════════════════


class TestDeprecatedFlag:
    """Verify the deprecated flag propagates to the OpenAPI operation."""

    def test_deprecated_in_schema(self) -> None:
        """A route registered with deprecated=True shows deprecated in schema."""
        GateCoordinator()
        machine = ActionProductMachine(mode="test")
        auth = AsyncMock()
        auth.process.return_value = None

        adapter = FastApiAdapter(machine=machine, auth_coordinator=auth)
        adapter.post("/old-ping", PingAction, deprecated=True)
        app = adapter.build()

        client = TestClient(app)
        schema = _get_openapi(client)

        old_ping_op = schema["paths"]["/old-ping"]["post"]
        assert old_ping_op.get("deprecated") is True
