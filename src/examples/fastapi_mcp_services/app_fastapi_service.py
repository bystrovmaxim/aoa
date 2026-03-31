# src/examples/fastapi_mcp_services/app_fastapi_service.py
"""
FastAPI-сервис на базе ActionMachine.

Запуск:
    uvicorn examples.fastapi_mcp_services.app_fastapi_service:app --reload

Документация:
    Swagger UI: http://localhost:8000/docs
    ReDoc:      http://localhost:8000/redoc
"""

from action_machine.contrib.fastapi import FastApiAdapter

from .actions import CreateOrderAction, GetOrderAction, PingAction
from .infrastructure import auth, machine

app = (
    FastApiAdapter(
        machine=machine,
        auth_coordinator=auth,
        title="Orders API",
        version="0.1.0",
        description=(
            "Пример HTTP-сервиса на базе ActionMachine.\n\n"
            "Демонстрирует автоматическую генерацию OpenAPI из Pydantic-моделей "
            "и декоратора `@meta`. Описания полей, constraints, examples — "
            "всё берётся из кода без дублирования."
        ),
    )
    .get("/api/v1/ping", PingAction, tags=["system"])
    .post("/api/v1/orders", CreateOrderAction, tags=["orders"])
    .get("/api/v1/orders/{order_id}", GetOrderAction, tags=["orders"])
    .build()
)
