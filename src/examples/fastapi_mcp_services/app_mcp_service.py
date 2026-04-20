# src/examples/fastapi_mcp_services/app_mcp_service.py
"""
MCP server exposing the same ActionMachine actions as the FastAPI example.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Builds an MCP server via ``McpAdapter`` so AI clients (e.g. Claude, ChatGPT,
Cursor) call the same ``PingAction``, ``CreateOrderAction``, and ``GetOrderAction``
as HTTP users. Tool metadata comes from ``@meta`` and Pydantic
``Field(description=..., examples=...)`` — no duplicate tool specs.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    MCP client (stdio or streamable-http)
              |
              v
         McpAdapter
              |
              v
    machine.run(...)  <- ActionProductMachine from infrastructure
              |
              v
    PingAction | CreateOrderAction | GetOrderAction

    auth_coordinator  <- infrastructure.auth (NoAuthCoordinator in this sample)

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Install and run::

    pip install aoa-run[mcp]

    # stdio (Claude Desktop, Claude Code):
    python -m examples.fastapi_mcp_services.app_mcp_service

    # streamable-http (e.g. MCP Inspector):
    python -m examples.fastapi_mcp_services.app_mcp_service --transport streamable-http

Claude Desktop ``claude_desktop_config.json``::

    {
      "mcpServers": {
        "orders": {
          "command": "python",
          "args": ["-m", "examples.fastapi_mcp_services.app_mcp_service"]
        }
      }
    }

Edge case: invalid or missing value after ``--transport`` leaves transport as
``stdio`` (see ``main()`` parsing).

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: MCP entrypoint for dual-transport example; thin adapter over shared machine.
CONTRACT: Export built ``server``; ``main()`` runs with configurable transport.
INVARIANTS: No business logic — registration and startup only.
═══════════════════════════════════════════════════════════════════════════════
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

import sys

from action_machine.integrations.mcp import McpAdapter

from .actions import CreateOrderAction, GetOrderAction, PingAction
from .infrastructure import auth, machine

server = (
    McpAdapter(
        machine=machine,
        auth_coordinator=auth,
        server_name="Orders MCP",
        server_version="0.1.0",
    )
    .tool("system.ping", PingAction)
    .tool("orders.create", CreateOrderAction)
    .tool("orders.get", GetOrderAction)
    .build()
)


def main() -> None:
    """Run the MCP server; use ``--transport <name>`` to override default stdio."""
    transport = "stdio"
    if "--transport" in sys.argv:
        idx = sys.argv.index("--transport")
        if idx + 1 < len(sys.argv):
            transport = sys.argv[idx + 1]
    server.run(transport=transport)  # type: ignore[arg-type]


if __name__ == "__main__":
    main()
