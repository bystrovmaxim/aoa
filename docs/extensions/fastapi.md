<!-- translated-from: fastapi_draft.md @ 2026-07-11T15:01:29Z (filesystem mtime; draft is gitignored, no git history) · sha256:a602e2e4e2ef -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# FastAPI — HTTP/REST and OpenAPI from an operation

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>

---

`FastApiAdapter` publishes an operation as an HTTP endpoint with a ready-made OpenAPI schema — **without mixing transport into business logic**. It is an adapter: the same `Action` is exposed this way both over HTTP and (via [MCP](../tutorials/step-15-mcp.md)) to an AI agent.

This page is a short extension card; the **full guide is the chapter [Step 14 — FastAPI adapter](../tutorials/step-14-fastapi.md)**. Example: [01_service.py](../../examples/step_14_fastapi/01_service.py).

Installation: `pip install aoa-fastapi-adapter`.

---

## The essentials

```python
# Fragment: one part of an example; `machine` comes from the code around it.
from aoa.fastapi import FastApiAdapter
from aoa.action_machine.auth import NoAuthCoordinator
from aoa.action_machine.context import Context

app = (
    FastApiAdapter(machine=machine, auth_coordinator=NoAuthCoordinator(context=Context()), title="Orders API")
    .post("/orders", CreateOrderAction, tags=["orders"])
    .build()                                  # -> FastAPI; serve with uvicorn
)
```

- A fluent builder `.post/.get/.put/.delete/.patch(path, ActionClass, ...)` → `.build()` → a FastAPI app.
- **OpenAPI is derived from the code** — `Params`/`Result`, `Field(description=…)`, `@meta`; Swagger at `/docs`.
- **`auth_coordinator` is mandatory** (`None` → `TypeError`); for open access use `NoAuthCoordinator(context=Context())`. See [Authentication](../tutorials/step-13-authentication.md).
- **Per-route override.** `.post(path, Action, auth_coordinator=...)` — one route uses its own coordinator instead of the adapter's default (e.g. an open `/login` next to a strict default). Without an explicit value, the adapter's default applies.
- Machine errors → HTTP codes: `AuthorizationError` → 403, `ValidationFieldError` → 422, anything else → 500; an auto `GET /health`.
- A mismatch between the external schema and the contract — `request_model`/`response_model` + `params_mapper`/`response_mapper` (see [Schema converters](../tutorials/step-20-converters.md)); open resources per request — the `connections=` argument (see [Connections at the boundary](../tutorials/step-19-connections.md)).

In full, broken down by section and with review questions — in the chapter [Step 14 — FastAPI adapter](../tutorials/step-14-fastapi.md).

---

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>
