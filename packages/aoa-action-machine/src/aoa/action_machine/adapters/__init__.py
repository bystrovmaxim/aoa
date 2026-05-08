# packages/aoa-action-machine/src/aoa/action_machine/adapters/__init__.py
"""
ActionMachine adapters package public exports.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Expose protocol-agnostic adapter contracts used to bridge transport layers
(HTTP, MCP, future integrations) to
``machine.run(context, action, params, connections)``.

This module is documentation-first and export-only: it defines no runtime
behavior by itself, but centralizes the public API for adapter foundations.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

Concrete adapters register protocol routes/tools into typed route records.
At runtime they map protocol payloads to action params, execute machine calls,
and map action results back to protocol responses.

This package exports the protocol-agnostic core:
- ``BaseAdapter`` for route registration and build lifecycle.
- ``BaseRouteRecord`` for route metadata and mapping contracts.
- ``extract_action_types`` to derive params/result types from action generics.

Concrete adapters overview:
- ``integrations.fastapi.FastApiAdapter`` registers HTTP routes (``post/get/...``),
  builds FastAPI app, and maps machine/domain errors to HTTP responses.
- ``integrations.mcp.McpAdapter`` registers MCP tools (``tool``), builds MCP server,
  and maps machine/domain errors to MCP-compatible error semantics.

Architecture sketch:

    ┌──────────────────────┐
    │  External protocol   │  HTTP / MCP / ...
    └──────────┬───────────┘
               │
               ▼
    ┌──────────────────────┐
    │  Concrete Adapter    │  FastApiAdapter / McpAdapter
    │  extends BaseAdapter │
    │  registers route/tool│
    └──────────┬───────────┘
               │ machine.run(context, action, params, connections)
               ▼
    ┌──────────────────────┐
    │ ActionProductMachine │
    └──────────────────────┘

"""

from aoa.action_machine.adapters.base_adapter import BaseAdapter
from aoa.action_machine.adapters.base_route_record import BaseRouteRecord, extract_action_types

__all__ = [
    "BaseAdapter",
    "BaseRouteRecord",
    "extract_action_types",
]
