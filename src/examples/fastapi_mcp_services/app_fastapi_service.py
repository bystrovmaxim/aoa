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
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    uvicorn examples.fastapi_mcp_services.app_fastapi_service:app --reload

    Same module starts uvicorn when run as a file::

        python …/src/examples/fastapi_mcp_services/app_fastapi_service.py
        python …/app_fastapi_service.py --host 0.0.0.0 --port 8080

    …/ ``src`` is prepended to ``sys.path`` so absolute ``examples.*`` imports resolve.

    Swagger UI: http://localhost:8000/docs
    ReDoc:      http://localhost:8000/redoc
    Health:     http://localhost:8000/health  (registered by FastApiAdapter.build)

    Edge case: wrong optional extras — import or startup may fail; install
    ``aoa-run[fastapi]``.
"""

def _ensure_examples_package_src_on_path() -> None:
    """When this file runs as ``python …/app_fastapi_service.py``, add ``src`` to ``sys.path``."""
    if __package__:
        return
    import sys
    from pathlib import Path

    src_root = Path(__file__).resolve().parent.parent.parent
    s = str(src_root)
    if s not in sys.path:
        sys.path.insert(0, s)


_ensure_examples_package_src_on_path()

from action_machine.integrations.fastapi import FastApiAdapter
from examples.fastapi_mcp_services.actions import CreateOrderAction, GetOrderAction, PingAction
from examples.fastapi_mcp_services.infrastructure import auth, machine

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


def main() -> None:
    """Run the ASGI app with uvicorn when this file is executed directly."""
    try:
        import uvicorn  # extras: ``aoa-run[fastapi]``
    except ImportError as exc:
        msg = (
            "uvicorn is required to run this example. Install with: "
            "pip install 'aoa-run[fastapi]'"
        )
        raise SystemExit(msg) from exc

    import argparse

    parser = argparse.ArgumentParser(description="Orders API example (FastAPI)")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    parser.add_argument("--port", type=int, default=8000, help="Bind port")
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
