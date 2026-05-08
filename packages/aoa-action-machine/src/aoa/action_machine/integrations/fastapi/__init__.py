# packages/aoa-action-machine/src/aoa/action_machine/integrations/fastapi/__init__.py
"""
FastAPI integration package for ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Expose the FastAPI adapter surface that converts ActionMachine actions into
HTTP endpoints with request/response validation, error mapping, and OpenAPI
documentation.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    Action registration
      adapter.post/get/put/delete/patch(...)
                │
                ▼
      FastApiRouteRecord (typed route contract)
                │
                ▼
      FastApiAdapter.build()
        ├─ generated FastAPI handlers
        ├─ protocol error mapping
        ├─ OpenAPI metadata wiring
        └─ automatic /health endpoint

═══════════════════════════════════════════════════════════════════════════════
INSTALLATION
═══════════════════════════════════════════════════════════════════════════════

    pip install aoa-run[fastapi]

═══════════════════════════════════════════════════════════════════════════════
COMPONENTS
═══════════════════════════════════════════════════════════════════════════════

- ``FastApiAdapter`` — concrete adapter exposing ``post/get/put/delete/patch``.
- ``FastApiRouteRecord`` — frozen route record with HTTP-specific metadata:
  method, path, tags, summary, description, operation_id, deprecated.

═══════════════════════════════════════════════════════════════════════════════
QUICK START
═══════════════════════════════════════════════════════════════════════════════

    from aoa.action_machine.intents.check_roles import NoAuthCoordinator
    from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
    from aoa.action_machine.integrations.fastapi import FastApiAdapter

    machine = ActionProductMachine()

    adapter = FastApiAdapter(
        machine=machine,
        auth_coordinator=NoAuthCoordinator(),
        title="Orders API",
        version="0.1.0",
    )

    # Minimal route: request_model == params_type
    adapter.post("/api/v1/orders", CreateOrderAction, tags=["orders"])

    # request_model differs -> params_mapper required
    adapter.get("/api/v1/orders", ListOrdersAction,
                request_model=ListOrdersRequest,
                params_mapper=map_list_request,
                tags=["orders"])

    # Explicit open route policy (depends on selected auth coordinator)
    adapter.get("/api/v1/ping", PingAction, tags=["system"])

    app = adapter.build()

    # Run:
    # uvicorn myapp:app --reload

═══════════════════════════════════════════════════════════════════════════════
OPENAPI GENERATION
═══════════════════════════════════════════════════════════════════════════════

OpenAPI schema is generated from metadata already declared in code:

- Field descriptions -> ``Field(description="...")`` in Params/Result.
- Constraints -> ``Field(gt=0, min_length=3, pattern=...)`` in Params.
- Examples -> ``Field(examples=[...])`` in Params/Result.
- Endpoint summary -> action ``@meta(description="...")``.
- Tags -> ``tags=[...]`` during route registration.

Swagger UI: ``http://host:port/docs``.
ReDoc: ``http://host:port/redoc``.

═══════════════════════════════════════════════════════════════════════════════
ERROR MAPPING
═══════════════════════════════════════════════════════════════════════════════

The adapter installs FastAPI exception handlers:

    AuthorizationError   -> HTTP 403 Forbidden
    ValidationFieldError -> HTTP 422 Unprocessable Entity
    Exception            -> HTTP 500 Internal Server Error

Each response uses JSON body ``{"detail": "<error message>"}``.

═══════════════════════════════════════════════════════════════════════════════
HEALTH CHECK
═══════════════════════════════════════════════════════════════════════════════

Endpoint ``GET /health`` is added automatically at ``build()``.
Returns ``{"status": "ok"}`` for liveness probes, monitoring, and load-balancer checks.
"""

try:
    import fastapi  # noqa: F401
except ImportError:
    raise ImportError(
        "To use action_machine.integrations.fastapi, install the optional dependency: "
        "pip install aoa-run[fastapi]"
    ) from None

from aoa.action_machine.integrations.fastapi.adapter import FastApiAdapter
from aoa.action_machine.integrations.fastapi.route_record import FastApiRouteRecord

__all__ = [
    "FastApiAdapter",
    "FastApiRouteRecord",
]
