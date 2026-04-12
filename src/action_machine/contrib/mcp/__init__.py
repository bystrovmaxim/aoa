# src/action_machine/contrib/mcp/__init__.py
"""
MCP-адаптер для ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Превращает Action в MCP tools для AI-агентов. Разработчик пишет
``adapter.tool("orders.create", CreateOrderAction)`` — адаптер генерирует
MCP tool с inputSchema из Pydantic-модели Params, description из @meta
и handler, который транслирует вызов tool в machine.run().

Агент (Claude, ChatGPT, Cursor и др.) видит каждое Action как tool
с полной семантикой: что делает (description из @meta), какие параметры
(из Field(description=..., examples=...)), какие constraints (gt, min_length,
pattern). Агент вызывает tool — адаптер десериализует input, создаёт
экземпляр Action, вызывает machine.run() и возвращает результат как
TextContent с JSON.

Дополнительно адаптер регистрирует MCP resource ``system://graph``,
через который агент может запросить структуру всей системы: узлы
(actions, domains, dependencies, resource managers), рёбра (depends,
belongs_to, connection) и описания из @meta.

═══════════════════════════════════════════════════════════════════════════════
УСТАНОВКА
═══════════════════════════════════════════════════════════════════════════════

    pip install action-machine[mcp]

═══════════════════════════════════════════════════════════════════════════════
КОМПОНЕНТЫ
═══════════════════════════════════════════════════════════════════════════════

- McpAdapter — конкретный адаптер, наследующий BaseAdapter[McpRouteRecord].
  Предоставляет протокольный method tool() для регистрации MCP tools.
  Метод build() создаёт MCP-сервер из зарегистрированных маршрутов.
  Метод register_all() автоматически регистрирует все Action из координатора.

- McpRouteRecord — frozen-датакласс маршрута с MCP-специфичными полями:
  tool_name, description.

═══════════════════════════════════════════════════════════════════════════════
БЫСТРЫЙ СТАРТ
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.core.action_product_machine import ActionProductMachine
    from action_machine.metadata.gate_coordinator import GateCoordinator
    from action_machine.contrib.mcp import McpAdapter

    coordinator = GateCoordinator()
    machine = ActionProductMachine(mode="production")

    adapter = McpAdapter(
        machine=machine,
        server_name="Orders MCP",
        server_version="0.1.0",
    )

    # Ручная регистрация:
    adapter.tool("orders.create", CreateOrderAction)
    adapter.tool("orders.get", GetOrderAction)
    adapter.tool("system.ping", PingAction)

    # Или автоматическая регистрация всех Action из координатора:
    # adapter.register_all()

    server = adapter.build()
    server.run(transport="stdio")

═══════════════════════════════════════════════════════════════════════════════
АВТОМАТИЧЕСКАЯ ГЕНЕРАЦИЯ inputSchema
═══════════════════════════════════════════════════════════════════════════════

inputSchema генерируется из Pydantic-модели Params через
model_json_schema(). Описания полей, constraints, examples —
всё берётся из Field(description=..., gt=0, min_length=3, examples=[...]).

Агент видит полностью типизированную схему входных parameters,
включая обязательные поля, значения по умолчанию и ограничения.

═══════════════════════════════════════════════════════════════════════════════
ОБРАБОТКА ОШИБОК
═══════════════════════════════════════════════════════════════════════════════

Адаптер транслирует исключения ActionMachine в MCP-ответы:

    AuthorizationError      → isError=True, текст ошибки с пометкой PERMISSION_DENIED
    ValidationFieldError    → isError=True, текст ошибки с пометкой INVALID_PARAMS
    Exception (любое)       → isError=True, текст ошибки с пометкой INTERNAL_ERROR

═══════════════════════════════════════════════════════════════════════════════
RESOURCE system://graph
═══════════════════════════════════════════════════════════════════════════════

При build() адаптер регистрирует MCP resource ``system://graph``.
Агент может запросить этот ресурс, чтобы увидеть структуру системы:

    {
      "nodes": [
        {"id": "CreateOrderAction", "type": "action", "description": "...", "domain": "orders"},
        {"id": "OrdersDomain", "type": "domain", "name": "orders"}
      ],
      "edges": [
        {"from": "CreateOrderAction", "to": "OrdersDomain", "type": "belongs_to"}
      ]
    }

═══════════════════════════════════════════════════════════════════════════════
ИНТЕГРАЦИЯ С CLAUDE DESKTOP
═══════════════════════════════════════════════════════════════════════════════

В файле claude_desktop_config.json:

    {
      "mcpServers": {
        "orders": {
          "command": "python",
          "args": ["-m", "examples.mcp_service.server"]
        }
      }
    }

После перезапуска Claude Desktop агент увидит зарегистрированные tools
и сможет вызывать их в диалоге.
"""

try:
    from mcp.server.fastmcp import FastMCP  # noqa: F401
except ImportError:
    raise ImportError(
        "Для использования action_machine.contrib.mcp "
        "установите зависимость: pip install action-machine[mcp]"
    ) from None

from .adapter import McpAdapter
from .route_record import McpRouteRecord

__all__ = [
    "McpAdapter",
    "McpRouteRecord",
]
