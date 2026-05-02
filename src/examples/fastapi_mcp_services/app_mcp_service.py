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

Running the script by path works too::

    python /path/to/aoa/src/examples/fastapi_mcp_services/app_mcp_service.py
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
"""

import sys
from pathlib import Path


def _ensure_examples_package_src_on_path() -> None:
    """When this file runs as ``python …/app_mcp_service.py``, add ``src`` to ``sys.path``."""
    if __package__:
        return

    src_root = Path(__file__).resolve().parent.parent.parent
    s = str(src_root)
    if s not in sys.path:
        sys.path.insert(0, s)


_ensure_examples_package_src_on_path()

# pylint: disable=wrong-import-position
from action_machine.integrations.mcp import McpAdapter
from examples.fastapi_mcp_services.actions import CreateOrderAction, GetOrderAction, PingAction
from examples.fastapi_mcp_services.infrastructure import auth, machine

# pylint: enable=wrong-import-position

server = (
    McpAdapter(
        machine=machine,
        auth_coordinator=auth,
        gate_coordinator=machine.gate_coordinator,
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
