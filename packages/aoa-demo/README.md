<p align="center">
  <img src="../../docs/assets/aoa-logo.png" alt="AOA" width="660"><br><br>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.12%2B-blue?logo=python&logoColor=white" alt="Python 3.12+"></a>
  <a href="https://github.com/bystrovmaxim/aoa"><img src="https://img.shields.io/badge/license-Apache_2.0-blue" alt="Apache-2.0"></a>
  <a href="https://github.com/bystrovmaxim/aoa/actions/workflows/ci.yml"><img src="https://github.com/bystrovmaxim/aoa/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/version-1.0.0-informational" alt="1.0.0">
</p>

# aoa-demo: Reference Services for AOA

`aoa-demo` contains two runnable reference services — a FastAPI HTTP service and an MCP server — built on the same domain model: orders, products, and customers. Both services expose the same `Action` operations over different transports, demonstrating how a single piece of business logic is published via `FastApiAdapter` for REST clients and via `McpAdapter` for AI agents without duplicating any logic. The package also serves as the integration fixture used in the AOA test suite.

## The identity domain: one connection per call, with or without a database

`POST /api/v1/identity/lookup` and the MCP tool `identity.lookup` are the reference
for a database-backed resource. The action declares `IdentityStoreBase` under the
connection key `identity`; the route supplies a value per call — created for the call
and closed after it — so concurrent calls never share a connection and each
transaction belongs to one caller.

It runs in two modes, and only the supplied value differs:

| Mode | When | What the route supplies |
| --- | --- | --- |
| in memory | `AOA_DEMO_POSTGRES_DSN` is unset | `IdentityStoreStub` — the same two operations, no database, no driver |
| over a pool | the variable names a database | `IdentityStore(pool=…)` — one connection borrowed per call |

The pool is created once when the service starts and closed when it stops. An MCP
service has no request-scoped startup hook, but its server has one, so both
transports pass the same `pool_lifespan` to `build()` — no wrapper to write.

```bash
# Database-free: answers from memory; needs no PostgreSQL and no driver.
uv run uvicorn aoa.demo.fastapi_mcp_services.app_fastapi_service:app --port 8000

# Over a pool: install the extra and name the database.
uv add "aoa-demo[postgres]"
AOA_DEMO_POSTGRES_DSN=postgresql://user:pass@localhost/db \
  uv run uvicorn aoa.demo.fastapi_mcp_services.app_fastapi_service:app --port 8000
```

The pool states its size bounds (`min_size=1, max_size=10`) where it is created; the
wait for a free connection is bounded on the resource
(`IdentityStore.acquire_timeout = 30.0`), because `create_pool` has no such parameter
— a `timeout=` there would bound connecting, not waiting.

What each mode is for, and what the resource does with its connection, is in
[`src/aoa/demo/model/identity/README.md`](src/aoa/demo/model/identity/README.md).
