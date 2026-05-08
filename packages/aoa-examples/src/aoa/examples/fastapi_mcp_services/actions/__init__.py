# packages/aoa-examples/src/aoa/examples/fastapi_mcp_services/actions/__init__.py
"""
Shared actions for FastAPI and MCP services.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

This package exports canonical action classes used by both HTTP (FastAPI) and
MCP adapters in the example service. Action definitions, validation rules, and
Params/Result models are shared across transports.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

         +-------------------------------------+
         | actions package (__init__)          |
         |  - PingAction                       |
         |  - CreateOrderAction                |
         |  - GetOrderAction                   |
         +-----------------+-------------------+
                           |
               +-----------+-----------+
               |                       |
        FastApiAdapter           McpAdapter
      (HTTP endpoints)        (MCP tools for AI)
               |                       |
               +-----------+-----------+
                           |
                 shared action logic

"""

from .create_order import CreateOrderAction
from .get_order import GetOrderAction
from .ping import PingAction

__all__ = [
    "CreateOrderAction",
    "GetOrderAction",
    "PingAction",
]
