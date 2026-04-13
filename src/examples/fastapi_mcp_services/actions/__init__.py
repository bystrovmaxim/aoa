# src/examples/fastapi_mcp_services/actions/__init__.py
"""
Shared actions for FastAPI and MCP services.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

This package exports canonical action classes used by both HTTP (FastAPI) and
MCP adapters in the example service. Action definitions, validation rules, and
Params/Result models are shared across transports.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Action business semantics are transport-agnostic.
- FastAPI and MCP adapters must reference the same action classes.
- Exported action set remains explicit through ``__all__``.

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

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from examples.fastapi_mcp_services.actions import CreateOrderAction

    action = CreateOrderAction()

    # Edge case: any transport mismatch should be solved in adapters,
    # not by forking action classes.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- This package exports actions only; it does not configure adapters or routing.
- Runtime behavior depends on external adapter wiring and service bootstrapping.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Shared action export boundary for dual-transport example.
CONTRACT: Keep action definitions single-source for FastAPI and MCP adapters.
INVARIANTS: No transport-specific logic should leak into action declarations.
═══════════════════════════════════════════════════════════════════════════════
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from .create_order import CreateOrderAction
from .get_order import GetOrderAction
from .ping import PingAction

__all__ = [
    "CreateOrderAction",
    "GetOrderAction",
    "PingAction",
]
