# src/examples/fastapi_mcp_services/actions/__init__.py
"""
Действия (Actions) — общие для FastAPI и MCP сервисов.

Содержит три действия с вложенными моделями Params/Result:
- PingAction — проверка доступности сервиса (без параметров).
- CreateOrderAction — создание заказа (с валидацией полей и constraints).
- GetOrderAction — получение заказа по ID.

Каждое действие определяется один раз и используется двумя адаптерами:
- FastApiAdapter в app_fastapi_service.py → HTTP-эндпоинты.
- McpAdapter в app_mcp_service.py → MCP tools для AI-агентов.

Бизнес-логика, валидация, описания полей — едины для обоих транспортов.
"""

from .create_order import CreateOrderAction
from .get_order import GetOrderAction
from .ping import PingAction

__all__ = [
    "CreateOrderAction",
    "GetOrderAction",
    "PingAction",
]
