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
                 v
   MCP tools (call -> machine.run)

═══════════════════════════════════════════════════════════════════════════════
INSTALLATION
═══════════════════════════════════════════════════════════════════════════════

    pip install aoa-run[mcp]

═══════════════════════════════════════════════════════════════════════════════
COMPONENTS
═══════════════════════════════════════════════════════════════════════════════

- ``McpAdapter``: ``BaseAdapter[McpRouteRecord]`` specialization for MCP.
  Exposes ``tool()``, ``build()``, and ``register_all()``.
- ``McpRouteRecord``: immutable route declaration for MCP tool registration.

"""

try:
    from mcp.server.fastmcp import FastMCP  # noqa: F401
except ImportError:
    raise ImportError(
        "To use action_machine.integrations.mcp, "
        "install the extra dependency: pip install aoa-run[mcp]"
    ) from None

from action_machine.integrations.mcp.adapter import McpAdapter
from action_machine.integrations.mcp.route_record import McpRouteRecord

__all__ = [
    "McpAdapter",
    "McpRouteRecord",
]
