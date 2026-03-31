# src/examples/fastapi_service/app.py
"""
Точка входа FastAPI-сервиса на базе ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Создаёт FastAPI-приложение из Action через FastApiAdapter. Каждое действие
регистрируется одной строкой — адаптер генерирует async handler, подключает
валидацию Pydantic, обработку ошибок и OpenAPI-документацию автоматически.

Используется fluent chain: регистрация маршрутов и сборка приложения
выполняются в одном выражении через цепочку вызовов.

═══════════════════════════════════════════════════════════════════════════════
ЗАПУСК
═══════════════════════════════════════════════════════════════════════════════

    pip install action-machine[fastapi]
    uvicorn examples.fastapi_service.app:app --reload

═══════════════════════════════════════════════════════════════════════════════
ДОСТУПНЫЕ ЭНДПОИНТЫ
═══════════════════════════════════════════════════════════════════════════════

    GET  /health              → {"status": "ok"}           (автоматический)
    GET  /api/v1/ping         → {"message": "pong"}        (SystemDomain)
    POST /api/v1/orders       → {"order_id": ..., ...}     (OrdersDomain)
    GET  /api/v1/orders/{id}  → {"order_id": ..., ...}     (OrdersDomain)

═══════════════════════════════════════════════════════════════════════════════
ДОКУМЕНТАЦИЯ
═══════════════════════════════════════════════════════════════════════════════

    Swagger UI: http://localhost:8000/docs
    ReDoc:      http://localhost:8000/redoc
    OpenAPI:    http://localhost:8000/openapi.json

OpenAPI schema содержит описания полей из Field(description=...),
constraints (gt, min_length, pattern), examples и summary из @meta.

═══════════════════════════════════════════════════════════════════════════════
FLUENT CHAIN
═══════════════════════════════════════════════════════════════════════════════

Адаптер поддерживает цепочечные вызовы: каждый протокольный метод
(get, post, put, delete, patch) возвращает self. Метод build()
завершает цепочку и возвращает готовое FastAPI-приложение.
"""

from action_machine.contrib.fastapi import FastApiAdapter
from action_machine.core.action_product_machine import ActionProductMachine
from action_machine.core.gate_coordinator import GateCoordinator

from .actions import CreateOrderAction, GetOrderAction, PingAction

# ── Инфраструктура ActionMachine ───────────────────────────────────────────

coordinator = GateCoordinator()
machine = ActionProductMachine(mode="production", coordinator=coordinator)

# ── Создание адаптера и сборка приложения (fluent chain) ───────────────────

app = (
    FastApiAdapter(
        machine=machine,
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
