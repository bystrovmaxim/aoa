# ActionMachine — FastAPI + MCP from one codebase

This example illustrates a core ActionMachine principle: **the same Actions
run through any protocol adapter without modification**.

Actions inherit the standard set of **Intent** mixins from `BaseAction` and
declare behavior with decorators (`@meta`, `@check_roles`, aspects, dependencies).
The metadata graph is built when `GraphCoordinator.build()` runs from those declarations —
see the “Key concepts: Intent” section in the root `README.md`.

Three actions (PingAction, CreateOrderAction, GetOrderAction) are defined once
and wired to two transports: HTTP REST API (FastAPI) and MCP tools (for AI agents).

> **Production:** do not copy `NoAuthCoordinator` from this example into production without thought.
> For protected APIs, replace it with your own `AuthCoordinator` and real authentication.
> `NoAuthCoordinator` here is an explicit “open endpoint”, for demonstration only.

## Installation

```bash
# For the HTTP service:
pip install aoa-run[fastapi]

# For the MCP server:
pip install aoa-run[mcp]

# Both:
pip install aoa-run[fastapi,mcp]
```

## Running FastAPI (HTTP)

```bash
uvicorn examples.fastapi_mcp_services.app_fastapi_service:app --reload
```


| URL                                                                      | Description    |
| ------------------------------------------------------------------------ | -------------- |
| [http://localhost:8000/docs](http://localhost:8000/docs)                 | Swagger UI     |
| [http://localhost:8000/redoc](http://localhost:8000/redoc)               | ReDoc          |
| [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json) | OpenAPI schema |
| [http://localhost:8000/health](http://localhost:8000/health)             | Health check   |


## Running MCP (AI agents)

```bash
# Via stdio (Claude Desktop, Claude Code):
python -m examples.fastapi_mcp_services.app_mcp_service

# Via streamable-http (MCP Inspector):
python -m examples.fastapi_mcp_services.app_mcp_service --transport streamable-http
```

---

## Actions (shared by both transports)


| Action            | FastAPI                         | MCP Tool        | Description        |
| ----------------- | ------------------------------- | --------------- | ------------------ |
| PingAction        | `GET /api/v1/ping`              | `system.ping`   | Liveness check     |
| CreateOrderAction | `POST /api/v1/orders`           | `orders.create` | Create an order    |
| GetOrderAction    | `GET /api/v1/orders/{order_id}` | `orders.get`    | Fetch an order     |


FastAPI also registers `GET /health → {"status": "ok"}` automatically.

### CreateOrderAction parameters


| Field       | Type   | Required            | Constraints         | Description           |
| ----------- | ------ | ------------------- | ------------------- | --------------------- |
| `user_id`   | str    | yes                 | min_length=1        | User ID               |
| `amount`    | float  | yes                 | gt=0                | Order amount          |
| `currency`  | str    | no (default: RUB)   | pattern=^[A-Z]{3}$  | ISO 4217 currency code |


### Examples

**Create order (curl):**

```bash
curl -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user_123", "amount": 1500.0, "currency": "RUB"}'
```

**Response (same shape for HTTP and MCP):**

```json
{
  "order_id": "ORD-user_123-001",
  "status": "created",
  "total": 1500.0
}
```

**Ping:**

```bash
curl http://localhost:8000/api/v1/ping
```

```json
{"message": "pong"}
```

---

## FastAPI: automatic OpenAPI generation

The OpenAPI schema is generated from metadata already in the code:

- **Field descriptions** → from `Field(description="...")` on Params and Result
- **Constraints** → from `Field(gt=0, min_length=3, pattern=...)` on Params
- **Examples** → from `Field(examples=["..."])` on Params and Result
- **Endpoint summary** → from the action’s `@meta(description="...")`
- **Tags** → from the `tags=[...]` argument when registering the route

Nothing is duplicated — descriptions are written once in the Pydantic models.

## FastAPI: error handling


| Exception              | HTTP status               | Description              |
| ---------------------- | ------------------------- | ------------------------ |
| `AuthorizationError`   | 403 Forbidden             | Insufficient permissions |
| `ValidationFieldError` | 422 Unprocessable Entity  | Field validation error   |
| Anything else          | 500 Internal Server Error | Internal error           |


---

## MCP: available resources


| Resource         | Description                                                                 |
| ---------------- | --------------------------------------------------------------------------- |
| `system://graph` | System structure: nodes (actions, domains), edges (depends, belongs_to)    |


```json
{
  "nodes": [
    {"id": "CreateOrderAction", "type": "action", "description": "Create a new order", "domain": "orders"},
    {"id": "OrdersDomain", "type": "domain", "name": "orders"}
  ],
  "edges": [
    {"from": "CreateOrderAction", "to": "OrdersDomain", "type": "belongs_to"}
  ]
}
```

## MCP: error handling


| Exception              | MCP response             |
| ---------------------- | ------------------------ |
| `AuthorizationError`   | `PERMISSION_DENIED: ...` |
| `ValidationFieldError` | `INVALID_PARAMS: ...`    |
| Anything else          | `INTERNAL_ERROR: ...`    |


---

## Claude Desktop integration

In `claude_desktop_config.json`:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "orders": {
      "command": "python",
      "args": ["-m", "examples.fastapi_mcp_services.app_mcp_service"]
    }
  }
}
```

## Claude Code integration

```bash
claude mcp add orders -- python -m examples.fastapi_mcp_services.app_mcp_service
```

## Testing with MCP Inspector

```bash
# Terminal 1:
python -m examples.fastapi_mcp_services.app_mcp_service --transport streamable-http

# Terminal 2:
npx -y @modelcontextprotocol/inspector
```

Connect to `http://localhost:8000/mcp`, open the **Tools** tab → **List Tools**.

---

## Architecture

```
HTTP client                   AI agent
(curl, browser)               (Claude, ChatGPT)
    │                              │
    │  HTTP                        │  MCP protocol
    ▼                              ▼
FastApiAdapter               McpAdapter
(app_fastapi_service.py)     (app_mcp_service.py)
    │                              │
    └──────────┬───────────────────┘
               │
               ▼
       ActionProductMachine
       (infrastructure.py)
               │
       ┌───────┼───────┐
       │       │       │
    Ping    Create    Get
    Action  Order    Order
            Action   Action
```

An Action is a unit of business logic. An adapter is transport. One action
serves HTTP clients and AI agents at the same time, without duplication.

## Package layout

```
fastapi_mcp_services/
├── __init__.py              ← example overview
├── infrastructure.py        ← GraphCoordinator + ActionProductMachine (shared)
├── domains.py               ← business domains (OrdersDomain, SystemDomain)
├── actions/
│   ├── __init__.py
│   ├── ping.py              ← PingAction
│   ├── create_order.py      ← CreateOrderAction
│   └── get_order.py         ← GetOrderAction
├── app_fastapi_service.py   ← FastAPI app (HTTP)
├── app_mcp_service.py       ← MCP server (AI agents)
└── README.md                ← this file
```

## Fluent chain

**FastAPI:**

```python
app = (
    FastApiAdapter(machine=machine, title="Orders API", version="0.1.0")
    .get("/api/v1/ping", PingAction, tags=["system"])
    .post("/api/v1/orders", CreateOrderAction, tags=["orders"])
    .get("/api/v1/orders/{order_id}", GetOrderAction, tags=["orders"])
    .build()
)
```

**MCP:**

```python
server = (
    McpAdapter(machine=machine, server_name="Orders MCP", server_version="0.1.0")
    .tool("system.ping", PingAction)
    .tool("orders.create", CreateOrderAction)
    .tool("orders.get", GetOrderAction)
    .build()
)
```

Same Actions. Different adapters. Zero duplication.
