# src/examples/fastapi_service/actions/__init__.py
"""
Действия (Actions) для примера FastAPI-сервиса.

Содержит три действия с вложенными моделями Params/Result:
- PingAction — проверка доступности сервиса (GET, без аутентификации).
- CreateOrderAction — создание заказа (POST, с валидацией полей).
- GetOrderAction — получение заказа по ID (GET, path-параметр).
"""

from .create_order import CreateOrderAction
from .get_order import GetOrderAction
from .ping import PingAction

__all__ = [
    "PingAction",
    "CreateOrderAction",
    "GetOrderAction",
]
