# ActionMachine — FastAPI + MCP из одной кодовой базы

Пример, демонстрирующий ключевой принцип ActionMachine: **одни и те же Action
работают через любой протокольный адаптер без изменений**.

Действия наследуют стандартный набор **Intent**-миксинов из `BaseAction` и
объявляют поведение декораторами (`@meta`, `@check_roles`, аспекты, зависимости).
Граф метаданных строится при `GateCoordinator.build()` из этих деклараций —
см. раздел «Ключевые концепции: Intent» в корневом `README.md`.

Три действия (PingAction, CreateOrderAction, GetOrderAction) определены один раз
и подключены к двум транспортам: HTTP REST API (FastAPI) и MCP tools (для AI-агентов).

> **Production:** не копируйте `NoAuthCoordinator` из примера в прод без обдумывания.
> Для защищённых API замените его на свой `AuthCoordinator` с реальной аутентификацией.
> `NoAuthCoordinator` здесь — явное «endpoint открыт», только для демонстрации.

## Установка

```bash
# Для HTTP-сервиса:
pip install action-machine[fastapi]

# Для MCP-сервера:
pip install action-machine[mcp]

# Оба сразу:
pip install action-machine[fastapi,mcp]
```

## Запуск FastAPI (HTTP)

```bash
uvicorn examples.fastapi_mcp_services.app_fastapi_service:app --reload
```

| URL | Описание |
|-----|----------|
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000/redoc | ReDoc |
| http://localhost:8000/openapi.json | OpenAPI schema |
| http://localhost:8000/health | Health check |

## Запуск MCP (AI-агенты)

```bash
# Через stdio (для Claude Desktop, Claude Code):
python -m examples.fastapi_mcp_services.app_mcp_service

# Через streamable-http (для MCP Inspector):
python -m examples.fastapi_mcp_services.app_mcp_service --transport streamable-http
```

---

## Действия (общие для обоих транспортов)

| Действие | FastAPI | MCP Tool | Описание |
|----------|---------|----------|----------|
| PingAction | `GET /api/v1/ping` | `system.ping` | Проверка доступности |
| CreateOrderAction | `POST /api/v1/orders` | `orders.create` | Создание заказа |
| GetOrderAction | `GET /api/v1/orders/{order_id}` | `orders.get` | Получение заказа |

Дополнительно FastAPI автоматически добавляет `GET /health → {"status": "ok"}`.

### Параметры CreateOrderAction

| Поле | Тип | Обязательное | Ограничения | Описание |
|------|-----|-------------|-------------|----------|
| `user_id` | str | да | min_length=1 | ID пользователя |
| `amount` | float | да | gt=0 | Сумма заказа |
| `currency` | str | нет (default: RUB) | pattern=^[A-Z]{3}$ | Код валюты ISO 4217 |

### Примеры

**Создание заказа (curl):**

```bash
curl -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user_123", "amount": 1500.0, "currency": "RUB"}'
```

**Ответ (одинаковый для HTTP и MCP):**

```json
{
  "order_id": "ORD-user_123-001",
  "status": "created",
  "total": 1500.0
}
```

**Пинг:**

```bash
curl http://localhost:8000/api/v1/ping
```

```json
{"message": "pong"}
```

---

## FastAPI: автоматическая генерация OpenAPI

OpenAPI schema генерируется из метаданных, которые уже есть в коде:

- **Описания полей** → из `Field(description="...")` в Params и Result
- **Ограничения** → из `Field(gt=0, min_length=3, pattern=...)` в Params
- **Примеры** → из `Field(examples=["..."])` в Params и Result
- **Summary эндпоинта** → из `@meta(description="...")` действия
- **Tags** → из аргумента `tags=[...]` при регистрации маршрута

Ничего не дублируется — описания пишутся один раз в Pydantic-моделях.

## FastAPI: обработка ошибок

| Исключение | HTTP-статус | Описание |
|------------|-------------|----------|
| `AuthorizationError` | 403 Forbidden | Недостаточно прав |
| `ValidationFieldError` | 422 Unprocessable Entity | Ошибка валидации поля |
| Любое другое | 500 Internal Server Error | Внутренняя ошибка |

---

## MCP: доступные Resources

| Resource | Описание |
|----------|----------|
| `system://graph` | Структура системы: узлы (actions, domains), рёбра (depends, belongs_to) |

```json
{
  "nodes": [
    {"id": "CreateOrderAction", "type": "action", "description": "Создание нового заказа", "domain": "orders"},
    {"id": "OrdersDomain", "type": "domain", "name": "orders"}
  ],
  "edges": [
    {"from": "CreateOrderAction", "to": "OrdersDomain", "type": "belongs_to"}
  ]
}
```

## MCP: обработка ошибок

| Исключение | MCP-ответ |
|------------|-----------|
| `AuthorizationError` | `PERMISSION_DENIED: ...` |
| `ValidationFieldError` | `INVALID_PARAMS: ...` |
| Любое другое | `INTERNAL_ERROR: ...` |

---

## Интеграция с Claude Desktop

В файле `claude_desktop_config.json`:

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

## Интеграция с Claude Code

```bash
claude mcp add orders -- python -m examples.fastapi_mcp_services.app_mcp_service
```

## Тестирование через MCP Inspector

```bash
# Терминал 1:
python -m examples.fastapi_mcp_services.app_mcp_service --transport streamable-http

# Терминал 2:
npx -y @modelcontextprotocol/inspector
```

Подключиться к `http://localhost:8000/mcp`, вкладка **Tools** → **List Tools**.

---

## Архитектура

```
HTTP-клиент                    AI-агент
(curl, браузер)                (Claude, ChatGPT)
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

Action — единица бизнес-логики. Адаптер — транспорт. Одно действие
обслуживает HTTP-клиентов и AI-агентов одновременно, без дублирования.

## Структура пакета

```
fastapi_mcp_services/
├── __init__.py              ← описание примера
├── infrastructure.py        ← GateCoordinator + ActionProductMachine (общие)
├── domains.py               ← бизнес-домены (OrdersDomain, SystemDomain)
├── actions/
│   ├── __init__.py
│   ├── ping.py              ← PingAction
│   ├── create_order.py      ← CreateOrderAction
│   └── get_order.py         ← GetOrderAction
├── app_fastapi_service.py   ← FastAPI-приложение (HTTP)
├── app_mcp_service.py       ← MCP-сервер (AI-агенты)
└── README.md                ← этот файл
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

Одни и те же Action. Разные адаптеры. Ноль дублирования.
