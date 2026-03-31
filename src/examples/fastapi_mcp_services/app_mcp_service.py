# src/examples/fastapi_mcp_services/app_mcp_service.py
"""
MCP-сервис на базе ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Демонстрирует создание MCP-сервера из тех же Action, что используются
в FastAPI-сервисе. AI-агенты (Claude, ChatGPT, Cursor) видят каждое
Action как tool с полной семантикой: описание из @meta, параметры
из Pydantic Field(description=..., examples=...), constraints.

═══════════════════════════════════════════════════════════════════════════════
ЗАПУСК
═══════════════════════════════════════════════════════════════════════════════

    pip install action-machine[mcp]

    # stdio (Claude Desktop, Claude Code):
    python -m examples.fastapi_mcp_services.app_mcp_service

    # streamable-http (MCP Inspector):
    python -m examples.fastapi_mcp_services.app_mcp_service --transport streamable-http

═══════════════════════════════════════════════════════════════════════════════
CLAUDE DESKTOP
═══════════════════════════════════════════════════════════════════════════════

В файле claude_desktop_config.json:

    {
      "mcpServers": {
        "orders": {
          "command": "python",
          "args": ["-m", "examples.fastapi_mcp_services.app_mcp_service"]
        }
      }
    }

═══════════════════════════════════════════════════════════════════════════════
АУТЕНТИФИКАЦИЯ
═══════════════════════════════════════════════════════════════════════════════

auth_coordinator обязателен для всех адаптеров. В этом примере используется
NoAuthCoordinator — явная декларация отсутствия аутентификации. В production
заменяется на AuthCoordinator с реальными компонентами.
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
    """Запускает MCP-сервер. --transport выбирает транспорт."""
    transport = "stdio"
    if "--transport" in sys.argv:
        idx = sys.argv.index("--transport")
        if idx + 1 < len(sys.argv):
            transport = sys.argv[idx + 1]
    server.run(transport=transport)


if __name__ == "__main__":
    main()
