# src/action_machine/adapters/__init__.py
"""
ActionMachine adapters package.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Contains the adapter infrastructure — components that translate external
protocols (HTTP, MCP, gRPC, CLI) into calls to
``machine.run(context, action, params, connections)``.

An adapter is a bridge between the outside world and the ActionMachine core.
It accepts a protocol-specific request (HTTP request, MCP tool call, gRPC
message), extracts parameters, authenticates the user, invokes the action via
the machine, and returns the result in a protocol-specific format.

═══════════════════════════════════════════════════════════════════════════════
COMPONENTS
═══════════════════════════════════════════════════════════════════════════════

- BaseAdapter[R] — abstract generic adapter class. The R parameter is the type
  of a concrete RouteRecord (subclass of BaseRouteRecord). It defines the
  contract: storing routes in _routes and building a protocol application via
  build(). Concrete adapters (FastApiAdapter, McpAdapter) inherit BaseAdapter,
  implement protocol-specific registration methods (post, get, tool), and
  implement build().

- BaseRouteRecord — abstract frozen dataclass that stores the configuration of
  a single registered route. It contains fields common to all protocols and
  optional mapping fields (request_model, response_model, params_mapper,
  response_mapper). Protocol-specific fields (HTTP method, path, tags,
  tool_name) are defined in concrete subclasses (FastApiRouteRecord,
  McpRouteRecord). It cannot be instantiated directly.

- extract_action_types(action_class) — function that extracts the generic P
  and R parameters from BaseAction[P, R]. It walks __orig_bases__ in the action
  class MRO. It is called automatically when creating a RouteRecord.

═══════════════════════════════════════════════════════════════════════════════
CONCRETE ADAPTERS
═══════════════════════════════════════════════════════════════════════════════

FastApiAdapter (action_machine.contrib.fastapi):
    Converts an Action into FastAPI HTTP endpoints. Protocol methods:
    post(), get(), put(), delete(), patch(). It generates OpenAPI schema from
    Pydantic Params/Result models and the @meta decorator.

McpAdapter (action_machine.contrib.mcp):
    Converts an Action into MCP tools for AI agents. Protocol method:
    tool(). It generates inputSchema from Pydantic Params models. It registers
    the system resource graph with system://graph. It supports register_all()
    for automatic registration of all Actions from the coordinator.

═══════════════════════════════════════════════════════════════════════════════
TYPE EXTRACTION
═══════════════════════════════════════════════════════════════════════════════

params_type and result_type are ALWAYS extracted automatically from the generic
parameters BaseAction[P, R] of the action class. The developer never specifies
them manually. This is the single source of truth: the types are defined in the
action class and are not duplicated.

If protocol models (request_model, response_model) match params_type/result_type,
then they are omitted. Mappers are only needed when protocol models differ
from the action types.

═══════════════════════════════════════════════════════════════════════════════
ERROR HANDLING
═══════════════════════════════════════════════════════════════════════════════

Error handling is the responsibility of the concrete adapter. The adapter
catches ActionMachine exceptions (AuthorizationError, ValidationFieldError,
ConnectionValidationError, etc.) and maps them to protocol-specific responses:

    FastApiAdapter:
        AuthorizationError      → HTTP 403 {"detail": "..."}
        ValidationFieldError    → HTTP 422 {"detail": "..."}
        Exception               → HTTP 500 {"detail": "Internal server error"}

    McpAdapter:
        AuthorizationError      → "PERMISSION_DENIED: ..."
        ValidationFieldError    → "INVALID_PARAMS: ..."
        Exception               → "INTERNAL_ERROR: ..."

═══════════════════════════════════════════════════════════════════════════════
ROUTE TYPING
═══════════════════════════════════════════════════════════════════════════════

BaseRouteRecord is abstract and contains only common fields. Each concrete
adapter defines its own subclass with typed protocol-specific fields. IDEs
autocomplete concrete fields and mypy verifies types:

    @dataclass(frozen=True)
    class FastApiRouteRecord(BaseRouteRecord):
        method: str = "POST"
        path: str = "/"
        tags: tuple[str, ...] = ()
        summary: str = ""

    @dataclass(frozen=True)
    class McpRouteRecord(BaseRouteRecord):
        tool_name: str = ""
        description: str = ""

═══════════════════════════════════════════════════════════════════════════════
MAPPING INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

BaseRouteRecord validates invariants during creation:

1. If request_model is provided and differs from params_type, params_mapper
   is required. Without a mapper, the adapter cannot translate the protocol
   request into action params.

2. If response_model is provided and differs from result_type,
   response_mapper is required. Without a mapper, the adapter cannot translate
   the action result into a protocol response.

If request_model is omitted (None) or matches params_type, no mapper is needed
and the adapter passes the object directly.

═══════════════════════════════════════════════════════════════════════════════
MAPPER NAMING CONVENTION
═══════════════════════════════════════════════════════════════════════════════

Each mapper is named for what it RETURNS:

    params_mapper   → returns params   (transforms request → params)
    response_mapper → returns response (transforms result  → response)

═══════════════════════════════════════════════════════════════════════════════
CONCRETE ADAPTER API
═══════════════════════════════════════════════════════════════════════════════

Each concrete adapter defines its own protocol methods. One method call = one
registered route. The minimal call requires only the path/name and the action
class:

    # FastAPI:
    adapter = FastApiAdapter(machine=machine)
    adapter.post("/orders/create", CreateOrderAction)
    app = adapter.build()

    # MCP:
    adapter = McpAdapter(machine=machine)
    adapter.tool("orders.create", CreateOrderAction)
    server = adapter.build()

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE
═══════════════════════════════════════════════════════════════════════════════

    ┌──────────────────────┐
    │  External protocol   │   HTTP, MCP, gRPC, CLI
    └──────────┬───────────┘
               │
               ▼
    ┌──────────────────────┐
    │  ConcreteAdapter     │   FastApiAdapter, McpAdapter, ...
    │  extends BaseAdapter │
    │                      │
    │  post(path, action)  │──▶ creates RouteRecord, adds to _routes
    │  tool(name, action)  │──▶ creates RouteRecord, adds to _routes
    │  build()             │──▶ protocol application / server
    └──────────┬───────────┘
               │
               │  machine.run(context, action, params, connections)
               ▼
    ┌──────────────────────┐
    │  ActionProductMachine │
    └──────────────────────┘
"""

from .base_adapter import BaseAdapter
from .base_route_record import BaseRouteRecord, extract_action_types

__all__ = [
    "BaseAdapter",
    "BaseRouteRecord",
    "extract_action_types",
]
