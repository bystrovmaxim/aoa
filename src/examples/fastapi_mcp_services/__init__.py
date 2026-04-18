# src/examples/fastapi_mcp_services/__init__.py
"""
Example services on ActionMachine — FastAPI and MCP from one codebase.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Demonstrates a core ActionMachine idea: the same Action classes run through any
protocol adapter without changing business code.

Three actions (``CreateOrderAction``, ``GetOrderAction``, ``PingAction``) are
defined once under ``actions/`` and wired to two transports:

- **FastAPI** (``app_fastapi_service.py``) — HTTP REST with OpenAPI.
- **MCP** (``app_mcp_service.py``) — MCP server for AI agents (e.g. Claude,
  ChatGPT, Cursor).

Validation, checkers, logging, and plugins stay shared; adapters stay a thin
transport layer.

Actions use **Intent** mixins on ``BaseAction`` and decorators (``@meta``,
``@check_roles``, aspects). Metadata is assembled via ``GraphCoordinator.build()``;
see the root ``README.md`` (Intent section).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

         +------------------ actions/ ------------------+
         |  PingAction, CreateOrderAction, GetOrderAction |
         +------------------------+-----------------------+
                                  |
              +-------------------+-------------------+
              |                                       |
       FastApiAdapter                         McpAdapter
    app_fastapi_service                   app_mcp_service
              |                                       |
              v                                       v
        HTTP clients                          AI / tool clients

    infrastructure.py  ->  ActionProductMachine + NoAuthCoordinator
    domains.py         ->  OrdersDomain, SystemDomain

Package layout:

    fastapi_mcp_services/
    ├── __init__.py              <- this file
    ├── infrastructure.py        <- ActionProductMachine + NoAuthCoordinator
    ├── domains.py               <- business domains (OrdersDomain, SystemDomain)
    ├── actions/
    │   ├── __init__.py
    │   ├── ping.py              <- PingAction
    │   ├── create_order.py      <- CreateOrderAction
    │   └── get_order.py         <- GetOrderAction
    ├── app_fastapi_service.py   <- FastAPI app (HTTP)
    ├── app_mcp_service.py       <- MCP server (AI agents)
    └── README.md

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Action definitions must not import or depend on FastAPI/MCP entrypoints.
- Shared ``machine`` and ``auth`` live in ``infrastructure.py``, not in adapters.
- Optional extras: ``aoa-run[fastapi]`` / ``aoa-run[mcp]`` for each transport.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

FastAPI::

    pip install aoa-run[fastapi]
    uvicorn examples.fastapi_mcp_services.app_fastapi_service:app --reload

    Swagger UI: http://localhost:8000/docs
    ReDoc:      http://localhost:8000/redoc
    Health:     http://localhost:8000/health

MCP::

    pip install aoa-run[mcp]
    python -m examples.fastapi_mcp_services.app_mcp_service
    python -m examples.fastapi_mcp_services.app_mcp_service --transport streamable-http

Edge case: run only one transport — actions in ``actions/`` stay unchanged; you
only start the app you need.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Example code is for illustration, not production hardening.
- Missing optional dependencies produce import/runtime errors when starting the
  corresponding app.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Package doc for dual-transport ActionMachine example.
CONTRACT: Single action source; adapters are transport-only.
INVARIANTS: No business logic duplication between HTTP and MCP entrypoints.
═══════════════════════════════════════════════════════════════════════════════
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""
