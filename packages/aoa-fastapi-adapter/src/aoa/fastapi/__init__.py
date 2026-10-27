# packages/aoa-fastapi-adapter/src/aoa/fastapi/__init__.py
"""
FastAPI adapter for AOA ActionMachine.

Install: pip install aoa-fastapi-adapter

Usage:
    from aoa.fastapi import FastApiAdapter, FastApiRouteRecord
    from aoa.fastapi.query_field_before import QUERY_STR_LIST_BEFORE, coerce_query_str_list
"""

try:
    import fastapi  # noqa: F401
except ImportError:
    raise ImportError(
        "To use aoa-fastapi-adapter, install: pip install aoa-fastapi-adapter"
    ) from None

from aoa.fastapi.adapter import FastApiAdapter
from aoa.fastapi.query_field_before import QUERY_STR_LIST_BEFORE, coerce_query_str_list
from aoa.fastapi.route_record import FastApiRouteRecord
from aoa.fastapi.socket_channel import SocketChannel
from aoa.fastapi.websocket_route import ConnectionRefusalError, FastApiWebSocketRoute

__all__ = [
    "QUERY_STR_LIST_BEFORE",
    "ConnectionRefusalError",
    "FastApiAdapter",
    "FastApiRouteRecord",
    "FastApiWebSocketRoute",
    "SocketChannel",
    "coerce_query_str_list",
]
