# src/examples/fastapi_mcp_services/app_fastapi_service.py
"""
FastAPI Service based on ActionMachine.

Launch:
    uvicorn examples.fastapi_mcp_services.app_fastapi_service:app --reload

Documentation:
    Swagger UI: http://localhost:8000/docs
    ReDoc:      http://localhost:8000/redoc
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
            "Example HTTP service based on ActionMachine.\n\n"
            "Demonstrates automatic OpenAPI generation from Pydantic models "
            "and the `@meta` decorator. Field descriptions, constraints, examples — "
            "all taken from code without duplication."
        ),
    )
    .get("/api/v1/ping", PingAction, tags=["system"])
    .post("/api/v1/orders", CreateOrderAction, tags=["orders"])
    .get("/api/v1/orders/{order_id}", GetOrderAction, tags=["orders"])
    .build()
)
