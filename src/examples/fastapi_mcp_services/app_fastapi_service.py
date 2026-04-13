# src/examples/fastapi_mcp_services/app_fastapi_service.py
"""
FastAPI application wiring shared ActionMachine actions to HTTP routes.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Builds a production-style ASGI app via ``FastApiAdapter``: registers routes for
``PingAction``, ``CreateOrderAction``, and ``GetOrderAction`` using the shared
``ActionProductMachine`` and auth coordinator from ``infrastructure``.

OpenAPI is generated from Pydantic models and ``@meta`` / field metadata — no
parallel schema definitions.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    HTTP client
         |
         v
    FastAPI / Starlette
         |
         v
    FastApiAdapter (routes)
         |
         v
    machine.run(...)  <- ActionProductMachine from infrastructure
         |
         v
    PingAction | CreateOrderAction | GetOrderAction

    auth_coordinator  <- same as MCP example (infrastructure.auth)

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Routes must reference action classes from ``actions``, not duplicate handlers.
- ``app`` is the ASGI callable expected by ``uvicorn ...:app``.
- Extra dependency: ``aoa-run[fastapi]`` (see package README).

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    uvicorn examples.fastapi_mcp_services.app_fastapi_service:app --reload

    Swagger UI: http://localhost:8000/docs
    ReDoc:      http://localhost:8000/redoc
    Health:     http://localhost:8000/health  (registered by FastApiAdapter.build)

    Edge case: wrong optional extras — import or startup may fail; install
    ``aoa-run[fastapi]``.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Example-only; not a hardened production deployment template.
- Behavior depends on ``FastApiAdapter`` defaults (tags, operation IDs, health).

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: HTTP entrypoint for dual-transport example; thin adapter over shared machine.
CONTRACT: Export ``app``; register three example actions on stable URL prefixes.
INVARIANTS: No business logic in this module — only wiring.
═══════════════════════════════════════════════════════════════════════════════
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from action_machine.integrations.fastapi import FastApiAdapter

from .actions import CreateOrderAction, GetOrderAction, PingAction
from .infrastructure import auth, machine

app = (
    FastApiAdapter(
        machine=machine,
        auth_coordinator=auth,
        title="Orders API",
        version="0.1.0",
        description=(
            "Example HTTP service built on ActionMachine.\n\n"
            "OpenAPI is derived from Pydantic models and the ``@meta`` decorator. "
            "Field descriptions, constraints, and examples come from the action "
            "definitions — no duplicated schema authoring."
        ),
    )
    .get("/api/v1/ping", PingAction, tags=["system"])
    .post("/api/v1/orders", CreateOrderAction, tags=["orders"])
    .get("/api/v1/orders/{order_id}", GetOrderAction, tags=["orders"])
    .build()
)
