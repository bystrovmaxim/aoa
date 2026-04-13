# src/action_machine/integrations/mcp/__init__.py
"""
MCP integration package for ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Transforms ActionMachine actions into MCP tools consumable by AI agents.
When a developer registers ``adapter.tool("orders.create", CreateOrderAction)``,
the adapter derives an MCP input schema from ``Params`` (Pydantic),
description from action ``@meta``, and a handler that delegates to
``machine.run()``.

The package also exposes the ``system://graph`` resource, allowing agents to
inspect the action graph (nodes, edges, metadata) from the runtime coordinator.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``McpAdapter`` is the only public MCP adapter contract exported here.
- ``McpRouteRecord`` carries MCP-specific route metadata (tool name, docs).
- MCP extras are required at import time; absence fails fast with ImportError.
- Runtime behavior is delegated to ``action_machine.integrations.mcp.adapter``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Action class + @meta + Params model
                 |
                 v
         McpAdapter.tool(...)
                 |
                 v
         McpRouteRecord list
                 |
                 v
          McpAdapter.build()
                 |
      +----------+-----------+
      |                      |
      v                      v
   MCP tools           MCP resource
 (call -> machine.run)  system://graph

═══════════════════════════════════════════════════════════════════════════════
INSTALLATION
═══════════════════════════════════════════════════════════════════════════════

    pip install action-machine[mcp]

═══════════════════════════════════════════════════════════════════════════════
COMPONENTS
═══════════════════════════════════════════════════════════════════════════════

- ``McpAdapter``: ``BaseAdapter[McpRouteRecord]`` specialization for MCP.
  Exposes ``tool()``, ``build()``, and ``register_all()``.
- ``McpRouteRecord``: immutable route declaration for MCP tool registration.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.integrations.mcp import McpAdapter

    adapter = McpAdapter(
        machine=machine,
        server_name="Orders MCP",
        server_version="0.1.0",
    )

    # Happy path: manual registration.
    adapter.tool("orders.create", CreateOrderAction)
    adapter.tool("orders.get", GetOrderAction)
    server = adapter.build()
    server.run(transport="stdio")

═══════════════════════════════════════════════════════════════════════════════
    # Edge case: auto-registration from coordinator graph.
    adapter.register_all()
    server = adapter.build()

═══════════════════════════════════════════════════════════════════════════════
AUTOMATIC INPUT SCHEMA GENERATION
═══════════════════════════════════════════════════════════════════════════════

``inputSchema`` is derived from the action ``Params`` model using
``model_json_schema()``. Field docs, constraints, and examples are propagated
from Pydantic ``Field(...)`` metadata.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- ActionMachine exceptions are mapped to MCP error responses:
  - ``AuthorizationError`` -> permission-denied style MCP error.
  - ``ValidationFieldError`` -> invalid-params style MCP error.
  - Other exceptions -> internal-error style MCP error.
- JSON serialization constraints are handled by adapter-level mappers/encoders.
- Importing this package without MCP extras raises ``ImportError`` immediately.

AI-CORE-BEGIN
ROLE: Public package facade for MCP transport integration.
CONTRACT: Export stable MCP entry points and fail fast when MCP extras missing.
INVARIANTS: Exposes only McpAdapter/McpRouteRecord and preserves adapter runtime.
AI-CORE-END

"""

try:
    from mcp.server.fastmcp import FastMCP  # noqa: F401
except ImportError:
    raise ImportError(
        "To use action_machine.integrations.mcp, "
        "install the extra dependency: pip install action-machine[mcp]"
    ) from None

from action_machine.integrations.mcp.adapter import McpAdapter
from action_machine.integrations.mcp.route_record import McpRouteRecord

__all__ = [
    "McpAdapter",
    "McpRouteRecord",
]
