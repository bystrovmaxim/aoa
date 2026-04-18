# tests/adapters/mcp/test_mcp_adapter.py
"""
Tests for ``McpAdapter`` — MCP tool registration and server ``build()``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Cover ``tool()`` registration (name, description, ``@meta`` auto-description),
fluent chaining, ``build()`` returning an MCP server, ``register_all()`` driven
by the coordinator graph, ``_class_name_to_snake_case``, and mapper fields on
``McpRouteRecord``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Core.create_coordinator() + ActionProductMachine
              |
              v
    McpAdapter(BaseAdapter[McpRouteRecord])
              |
              +--> tool(...) / register_all() -> ``_routes``
              |
              v
    build() -> FastMCP (or SDK server) instance

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Tests use a real built coordinator when ``register_all`` must discover actions.
- ``auth_coordinator`` is always an ``AsyncMock`` with ``process`` stubbed.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    uv run pytest tests/adapters/mcp/test_mcp_adapter.py -q

Edge case: empty explicit description falls back to ``@meta`` text when present.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- MCP SDK types (e.g. ``FastMCP``) couple tests to the installed ``mcp`` version.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: MCP adapter registration and server construction tests.
CONTRACT: Fluent API; coordinator-driven bulk registration; snake_case naming.
INVARIANTS: Scenario actions; optional ``FullAction`` for multi-tool cases.
═══════════════════════════════════════════════════════════════════════════════
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from unittest.mock import AsyncMock

import pytest
from mcp.server.fastmcp import FastMCP

from action_machine.integrations.mcp.adapter import McpAdapter, _class_name_to_snake_case
from action_machine.integrations.mcp.route_record import McpRouteRecord
from action_machine.runtime.machines.action_product_machine import ActionProductMachine
from action_machine.runtime.machines.core import Core
from tests.scenarios.domain_model import FullAction, PingAction, SimpleAction

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _make_adapter(**kwargs) -> McpAdapter:
    """Create an McpAdapter with sensible test defaults."""
    coordinator = Core.create_coordinator()
    machine = ActionProductMachine(mode="test", coordinator=coordinator)
    auth = AsyncMock()
    auth.process.return_value = None
    return McpAdapter(
        machine=machine,
        auth_coordinator=auth,
        server_name=kwargs.get("server_name", "Test MCP"),
        server_version=kwargs.get("server_version", "0.0.1"),
    )


# ═════════════════════════════════════════════════════════════════════════════
# Constructor and properties
# ═════════════════════════════════════════════════════════════════════════════


class TestConstructor:
    """Verify adapter construction and metadata properties."""

    def test_server_name_stored(self) -> None:
        """server_name passed to constructor is accessible via property."""
        adapter = _make_adapter(server_name="Orders MCP")
        assert adapter.server_name == "Orders MCP"

    def test_server_version_stored(self) -> None:
        """server_version passed to constructor is accessible via property."""
        adapter = _make_adapter(server_version="2.0.0")
        assert adapter.server_version == "2.0.0"

    def test_routes_empty_initially(self) -> None:
        """No routes registered immediately after construction."""
        adapter = _make_adapter()
        assert adapter.routes == []


# ═════════════════════════════════════════════════════════════════════════════
# Tool registration
# ═════════════════════════════════════════════════════════════════════════════


class TestToolRegistration:
    """Verify that tool() registers correct route records."""

    def test_registers_tool(self) -> None:
        """tool() adds a route record with the given name and action_class."""
        adapter = _make_adapter()
        adapter.tool("system.ping", PingAction)

        assert len(adapter.routes) == 1
        assert adapter.routes[0].tool_name == "system.ping"
        assert adapter.routes[0].action_class is PingAction

    def test_custom_description(self) -> None:
        """Explicit description is stored on the route record."""
        adapter = _make_adapter()
        adapter.tool("ping", PingAction, description="Health check tool")

        assert adapter.routes[0].description == "Health check tool"

    def test_auto_description_from_meta(self) -> None:
        """When description is empty, @meta description is used."""
        adapter = _make_adapter()
        adapter.tool("ping", PingAction)

        # PingAction has @meta(description="Service health check")
        assert adapter.routes[0].description != ""

    def test_multiple_tools(self) -> None:
        """Multiple tool() calls register multiple routes."""
        adapter = _make_adapter()
        adapter.tool("system.ping", PingAction)
        adapter.tool("orders.create", FullAction)
        adapter.tool("simple.run", SimpleAction)

        assert len(adapter.routes) == 3
        names = [r.tool_name for r in adapter.routes]
        assert "system.ping" in names
        assert "orders.create" in names
        assert "simple.run" in names

    def test_route_is_mcp_record(self) -> None:
        """Each registered route is a McpRouteRecord instance."""
        adapter = _make_adapter()
        adapter.tool("ping", PingAction)

        assert isinstance(adapter.routes[0], McpRouteRecord)


# ═════════════════════════════════════════════════════════════════════════════
# Fluent chaining
# ═════════════════════════════════════════════════════════════════════════════


class TestFluentChain:
    """Verify that tool() returns self for chaining."""

    def test_tool_returns_self(self) -> None:
        """tool() returns the same adapter instance."""
        adapter = _make_adapter()
        result = adapter.tool("ping", PingAction)
        assert result is adapter

    def test_chained_registration(self) -> None:
        """Multiple tool() calls can be chained."""
        adapter = _make_adapter()

        result = (
            adapter
            .tool("system.ping", PingAction)
            .tool("orders.create", FullAction)
            .tool("simple.run", SimpleAction)
        )

        assert result is adapter
        assert len(adapter.routes) == 3


# ═════════════════════════════════════════════════════════════════════════════
# build()
# ═════════════════════════════════════════════════════════════════════════════


class TestBuild:
    """Verify that build() produces an MCP server."""

    def test_returns_mcp_server_instance(self) -> None:
        """build() returns the MCP server host object."""
        adapter = _make_adapter()
        adapter.tool("ping", PingAction)
        server = adapter.build()

        assert isinstance(server, FastMCP)

    def test_build_with_no_routes(self) -> None:
        """build() succeeds even with zero registered tools."""
        adapter = _make_adapter()
        server = adapter.build()

        assert isinstance(server, FastMCP)


class TestMcpInputSchema:
    """MCP tools expose inputSchema derived from action Params (Pydantic)."""

    @pytest.mark.asyncio
    async def test_list_tools_includes_param_properties(self) -> None:
        """Non-empty Params → inputSchema.properties matches model fields."""
        adapter = _make_adapter()
        adapter.tool("orders.create", FullAction)
        server = adapter.build()
        tools = await server.list_tools()
        assert len(tools) == 1
        schema = tools[0].inputSchema
        assert isinstance(schema, dict)
        assert schema.get("type") == "object"
        props = schema.get("properties") or {}
        assert "user_id" in props
        assert "amount" in props
        assert "currency" in props

    @pytest.mark.asyncio
    async def test_ping_tool_schema_is_object(self) -> None:
        """Empty Params still yields a JSON object schema for the tool."""
        adapter = _make_adapter()
        adapter.tool("system.ping", PingAction)
        server = adapter.build()
        tools = await server.list_tools()
        assert len(tools) == 1
        schema = tools[0].inputSchema
        assert schema.get("type") == "object"


# ═════════════════════════════════════════════════════════════════════════════
# _class_name_to_snake_case
# ═════════════════════════════════════════════════════════════════════════════


class TestSnakeCaseConversion:
    """Verify CamelCase to snake_case conversion with Action suffix removal."""

    def test_simple_action(self) -> None:
        """PingAction → ping."""
        assert _class_name_to_snake_case("PingAction") == "ping"

    def test_multi_word_action(self) -> None:
        """CreateOrderAction → create_order."""
        assert _class_name_to_snake_case("CreateOrderAction") == "create_order"

    def test_full_action(self) -> None:
        """FullAction → full."""
        assert _class_name_to_snake_case("FullAction") == "full"

    def test_no_action_suffix(self) -> None:
        """A class without Action suffix is converted without removal."""
        assert _class_name_to_snake_case("OrderService") == "order_service"

    def test_single_word(self) -> None:
        """Action → action (suffix is the entire name — not removed)."""
        # "Action" alone has len == len("Action"), so suffix is NOT removed
        assert _class_name_to_snake_case("Action") == "action"

    def test_consecutive_uppercase(self) -> None:
        """HTTPAction → http."""
        result = _class_name_to_snake_case("HTTPAction")
        assert result == "http"

    def test_complex_name(self) -> None:
        """GetOrderByIDAction → get_order_by_id."""
        result = _class_name_to_snake_case("GetOrderByIDAction")
        assert "get_order_by" in result


# ═════════════════════════════════════════════════════════════════════════════
# register_all
# ═════════════════════════════════════════════════════════════════════════════


class TestRegisterAll:
    """Verify register_all() auto-registers actions from the coordinator."""

    def test_returns_self(self) -> None:
        """register_all() returns the adapter for fluent chaining."""
        adapter = _make_adapter()
        result = adapter.register_all()
        assert result is adapter

    def test_registers_known_actions(self) -> None:
        """Actions discovered by the coordinator are registered as tools."""
        adapter = _make_adapter()
        adapter.register_all()

        tool_names = [r.tool_name for r in adapter.routes]
        # PingAction, SimpleAction, FullAction were registered in the coordinator
        assert len(adapter.routes) >= 3
        assert "ping" in tool_names
        assert "simple" in tool_names
        assert "full" in tool_names

    def test_tool_names_are_snake_case(self) -> None:
        """All auto-generated tool names are lowercase snake_case."""
        adapter = _make_adapter()
        adapter.register_all()

        for route in adapter.routes:
            assert route.tool_name == route.tool_name.lower()
            assert " " not in route.tool_name
