# src/action_machine/adapters/__init__.py
"""
ActionMachine adapter package exports.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Expose the shared adapter contract used to bridge external protocols to
``machine.run(context, action, params, connections)``.

The package-level docstring is an operator-facing overview: what components are
exported, how data flows through adapters, and which invariants govern
route typing and mapper usage.

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
- ``contrib.fastapi.FastApiAdapter`` registers HTTP routes (``post/get/...``),
  builds FastAPI app, and maps machine/domain errors to HTTP responses.
- ``contrib.mcp.McpAdapter`` registers MCP tools (``tool``), builds MCP server,
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

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Action params/result types come from action generic declarations.
- Mappers are required only when protocol models differ from action types.
- ``BaseRouteRecord`` remains abstract; concrete adapters provide protocol fields.
- Mapper naming follows return value semantics:
  ``params_mapper`` returns params, ``response_mapper`` returns response.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    # Happy path
    adapter = FastApiAdapter(machine=machine)
    adapter.post("/orders/create", CreateOrderAction)
    app = adapter.build()

    mcp = McpAdapter(machine=machine)
    mcp.tool("orders.create", CreateOrderAction)
    server = mcp.build()

    # Edge case: mapper required when models differ
    adapter.post("/orders", CreateOrderAction,
                 request_model=LegacyOrderRequest,
                 params_mapper=legacy_to_params)

    # Route typing is protocol-specific via BaseRouteRecord subclasses:
    # FastApiRouteRecord(method, path, tags, ...)
    # McpRouteRecord(tool_name, description, ...)

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

Protocol-specific error mapping is implemented by concrete adapters
(``contrib.fastapi``, ``contrib.mcp``). This package only exports shared base
contracts and type-extraction helpers.

Typical mapping examples (implemented in concrete adapters):
- ``AuthorizationError`` -> HTTP 403 / MCP permission-denied equivalent.
- ``ValidationFieldError`` -> HTTP 422 / MCP invalid-params equivalent.
- fallback ``Exception`` -> transport-specific internal-error response.

Type extraction and mapping limitations:
- ``extract_action_types`` relies on action generic declarations.
- If protocol request/response models differ from action params/result models,
  corresponding mappers are required to preserve deterministic conversion.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Adapters package API surface.
CONTRACT: Export protocol-agnostic adapter abstractions and action-type extraction helper.
INVARIANTS: generic action types are source of truth; mapping contracts are validated by route records.
FLOW: protocol registration -> route records -> machine.run invocation -> protocol response mapping.
FAILURES: adapter-specific failures and transport error mapping are outside this package.
EXTENSION POINTS: implement new concrete adapters on top of BaseAdapter/BaseRouteRecord.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from .base_adapter import BaseAdapter
from .base_route_record import BaseRouteRecord, extract_action_types

__all__ = [
    "BaseAdapter",
    "BaseRouteRecord",
    "extract_action_types",
]
