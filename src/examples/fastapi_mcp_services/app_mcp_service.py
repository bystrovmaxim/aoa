# src/examples/fastapi_mcp_services/app_mcp_service.py
"""
MCP Service based on ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Demonstrates creating an MCP server from the same Actions used in the
FastAPI service. AI agents (Claude, ChatGPT, Cursor) see each Action
as a tool with full semantics: description from @meta, parameters
from Pydantic Field(description=..., examples=...), constraints.

═══════════════════════════════════════════════════════════════════════════════
LAUNCH
═══════════════════════════════════════════════════════════════════════════════

    pip install action-machine[mcp]

    # stdio (Claude Desktop, Claude Code):
    python -m examples.fastapi_mcp_services.app_mcp_service

    # streamable-http (MCP Inspector):
    python -m examples.fastapi_mcp_services.app_mcp_service --transport streamable-http

═══════════════════════════════════════════════════════════════════════════════
CLAUDE DESKTOP
═══════════════════════════════════════════════════════════════════════════════

In the claude_desktop_config.json file:

    {
      "mcpServers": {
        "orders": {
          "command": "python",
          "args": ["-m", "examples.fastapi_mcp_services.app_mcp_service"]
        }
      }
    }

═══════════════════════════════════════════════════════════════════════════════
AUTHENTICATION
═══════════════════════════════════════════════════════════════════════════════

auth_coordinator is required for all adapters. This example uses
NoAuthCoordinator — explicit declaration of no authentication. In production
it is replaced with AuthCoordinator with real components.
"""

import sys

from action_machine.contrib.mcp import McpAdapter

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
    """Starts the MCP server. --transport selects the transport."""
    transport = "stdio"
    if "--transport" in sys.argv:
        idx = sys.argv.index("--transport")
        if idx + 1 < len(sys.argv):
            transport = sys.argv[idx + 1]
    server.run(transport=transport)  # type: ignore[arg-type]


if __name__ == "__main__":
    main()
