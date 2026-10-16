# The identity domain

The identity domain is the demo's reference for a **database-backed resource**: one
connection per call, a transaction that belongs to one caller, and the same route
whether or not a database is running.

## What it holds

| Piece | What it is |
| --- | --- |
| `resources/identity_store_base.py` | What the domain asks of storage — `read_person`, `record_login` — in terms of the SQL contract, with no driver imported |
| `resources/identity_store.py` | The PostgreSQL store: `IdentityStoreBase` mixed with `PostgresResource`, built from a pool, one connection per call |
| `resources/identity_store_stub.py` | The same two operations in memory, so the demo runs with no database and no driver |
| `actions/identity_lookup.py` | `IdentityLookupAction` — declares `@connection(IdentityStoreBase, key="identity")` and never learns how the store was supplied |

`record_login` owns its transaction: `BEGIN`, the insert, `COMMIT` — and a
`ROLLBACK` on any failure, including cancellation. `read_person` reads through the
connection this call holds, so two concurrent lookups never meet on one session.

## The two modes

The route and the tool are the same in both. What differs is the value the boundary
is handed for the key `identity`:

| Mode | When it is chosen | What is supplied |
| --- | --- | --- |
| in memory | `AOA_DEMO_POSTGRES_DSN` is unset | `IdentityStoreStub` — no database, no driver, nothing to close |
| over a pool | the variable names a database | `PerCallConnection(factory=…IdentityStore(pool=…), finalize=…close)` |

In the pooled mode the store is created for one call, opened by the boundary before
the run and closed after it — on success, on failure and on cancellation alike. The
connection goes back to the pool; the pool itself is never closed by the resource.

## Running it

```bash
# In memory: needs neither PostgreSQL nor the postgres extra.
uv run uvicorn aoa.demo.fastapi_mcp_services.app_fastapi_service:app --port 8000
curl -X POST localhost:8000/api/v1/identity/lookup \
     -H 'content-type: application/json' \
     -d '{"person_id": "person-1", "at": "2026-10-16T12:00:00Z"}'

# Over a pool: install the extra and name the database. Without the DSN the service
# simply falls back to the in-memory store.
uv add "aoa-demo[postgres]"
AOA_DEMO_POSTGRES_DSN=postgresql://user:pass@localhost/db \
  uv run uvicorn aoa.demo.fastapi_mcp_services.app_fastapi_service:app --port 8000
```

The MCP server publishes the same action as the tool `identity.lookup`, and takes the
same connection declaration:

```bash
uv run python packages/aoa-demo/src/aoa/demo/fastapi_mcp_services/app_mcp_service.py
```

## Where the bounds are stated

- the pool's size: `min_size=1, max_size=10` where the pool is created, in
  `fastapi_mcp_services/infrastructure.py`;
- the wait for a free connection: `IdentityStore.acquire_timeout = 30.0` on the
  resource, because `create_pool` has no such parameter — a `timeout=` there would
  bound connecting, not waiting.

## Tests

`packages/aoa-demo/tests/test_identity_postgres.py` covers both modes: the holder's
named failure, the in-memory route, twenty concurrent calls, two transactions that do
not interleave, the finalizer running once per call, and the pool being created once
with its stated bounds and closed at shutdown. Nothing there needs a server; the
driver-dependent tests skip when the extra is absent.
