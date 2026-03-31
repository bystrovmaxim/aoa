# src/examples/fastapi_mcp_services/app_mcp_service.py
"""
MCP-сервис на базе ActionMachine.

Создаёт MCP-сервер из Action через McpAdapter. Те же Action, что
обслуживают HTTP-клиентов через FastAPI в app_fastapi_service.py,
здесь превращаются в MCP tools для AI-агентов.

Запуск:
    # stdio (Claude Desktop, Claude Code):
    python -m examples.fastapi_mcp_services.app_mcp_service

    # streamable-http (MCP Inspector):
    python -m examples.fastapi_mcp_services.app_mcp_service --transport streamable-http

Tools:
    system.ping     — проверка доступности
    orders.create   — создание заказа
    orders.get      — получение заказа по ID

Resources:
    system://graph  — структура системы

Claude Desktop (claude_desktop_config.json):
    {
      "mcpServers": {
        "orders": {
          "command": "python",
          "args": ["-m", "examples.fastapi_mcp_services.app_mcp_service"]
        }
      }
    }

Claude Code:
    claude mcp add orders -- python -m examples.fastapi_mcp_services.app_mcp_service
"""

import sys

from action_machine.contrib.mcp import McpAdapter

from .actions import CreateOrderAction, GetOrderAction, PingAction
from .infrastructure import machine

server = (
    McpAdapter(
        machine=machine,
        server_name="Orders MCP",
        server_version="0.1.0",
    )
    .tool("system.ping", PingAction)
    .tool("orders.create", CreateOrderAction)
    .tool("orders.get", GetOrderAction)
    .build()
)


def main() -> None:
    """
    Запускает MCP-сервер.

    По умолчанию stdio transport. Аргумент --transport выбирает транспорт:
        python -m examples.fastapi_mcp_services.app_mcp_service --transport streamable-http
    """
    transport = "stdio"

    if "--transport" in sys.argv:
        idx = sys.argv.index("--transport")
        if idx + 1 < len(sys.argv):
            transport = sys.argv[idx + 1]

    server.run(transport=transport)


if __name__ == "__main__":
    main()
