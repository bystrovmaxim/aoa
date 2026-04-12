# src/examples/fastapi_mcp_services/__init__.py
"""
Пример сервисов на базе ActionMachine — FastAPI + MCP из одной кодовой базы.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Демонстрирует ключевой принцип ActionMachine: одни и те же Action работают
через любой протокольный адаптер без изменений.

Три действия (CreateOrderAction, GetOrderAction, PingAction) определены
один раз в пакете actions/ и подключаются к двум транспортам:

- **FastAPI** (app_fastapi_service.py) — HTTP REST API с OpenAPI-документацией.
- **MCP** (app_mcp_service.py) — MCP-сервер для AI-агентов (Claude, ChatGPT, Cursor).

Бизнес-логика, валидация, чекеры, логирование и плагины — общие.
Адаптеры — тонкий транспортный слой без бизнес-логики.

Действия опираются на **Intent**-миксины из ``BaseAction`` и декораторы
(``@meta``, ``@check_roles``, аспекты); граф метаданных собирает
``GateCoordinator.build()`` — см. корневой ``README.md`` (раздел про Intent).

═══════════════════════════════════════════════════════════════════════════════
СТРУКТУРА
═══════════════════════════════════════════════════════════════════════════════

    fastapi_mcp_services/
    ├── __init__.py              ← этот файл
    ├── infrastructure.py        ← GateCoordinator + ActionProductMachine
    ├── domains.py               ← бизнес-домены (OrdersDomain, SystemDomain)
    ├── actions/
    │   ├── __init__.py
    │   ├── ping.py              ← PingAction
    │   ├── create_order.py      ← CreateOrderAction
    │   └── get_order.py         ← GetOrderAction
    ├── app_fastapi_service.py   ← FastAPI-приложение (HTTP)
    ├── app_mcp_service.py       ← MCP-сервер (AI-агенты)
    └── README.md

═══════════════════════════════════════════════════════════════════════════════
ЗАПУСК FASTAPI
═══════════════════════════════════════════════════════════════════════════════

    pip install action-machine[fastapi]
    uvicorn examples.fastapi_mcp_services.app_fastapi_service:app --reload

    Swagger UI: http://localhost:8000/docs
    ReDoc:      http://localhost:8000/redoc
    Health:     http://localhost:8000/health

═══════════════════════════════════════════════════════════════════════════════
ЗАПУСК MCP
═══════════════════════════════════════════════════════════════════════════════

    pip install action-machine[mcp]

    # stdio (Claude Desktop, Claude Code):
    python -m examples.fastapi_mcp_services.app_mcp_service

    # streamable-http (MCP Inspector):
    python -m examples.fastapi_mcp_services.app_mcp_service --transport streamable-http

═══════════════════════════════════════════════════════════════════════════════
КЛЮЧЕВАЯ ИДЕЯ
═══════════════════════════════════════════════════════════════════════════════

Action — единица бизнес-логики. Адаптер — транспорт. Одно действие
обслуживает HTTP-клиентов и AI-агентов одновременно, без дублирования кода.
"""
