# packages/aoa-mcp-adapter/src/aoa/mcp/__init__.py
"""
MCP adapter for AOA ActionMachine.

Install: pip install aoa-mcp-adapter

Usage:
    from aoa.mcp import McpAdapter, McpRouteRecord
"""

try:
    from mcp.server.fastmcp import FastMCP  # noqa: F401
except ImportError:
    raise ImportError(
        "To use aoa-mcp-adapter, install: pip install aoa-mcp-adapter"
    ) from None

from aoa.mcp.adapter import McpAdapter
from aoa.mcp.route_record import McpRouteRecord

__all__ = [
    "McpAdapter",
    "McpRouteRecord",
]
