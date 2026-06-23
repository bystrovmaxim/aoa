<!-- translated-from: fastapi_draft.md @ 2026-06-17T10:30:35Z · sha256:3acdd1dc63f6 -->
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

`FastApiAdapter` publishes an operation as an HTTP endpoint with a ready-made OpenAPI schema — **without mixing transport into business logic**. It is an adapter: the same `Action` is exposed this way both over HTTP and (via [MCP](../tutorials/step-14-mcp.md)) to an AI agent.

This page is a short extension card; the **full guide is the chapter [Step 13 — FastAPI adapter](../tutorials/step-13-fastapi.md)**. Example: [01_service.py](../../examples/step_13_fastapi/01_service.py).

Installation: `pip install "aoa-action-machine[fastapi]"`.

---

## The essentials

```python
from aoa.action_machine.adapters.fastapi import FastApiAdapter
from aoa.action_machine.auth import NoAuthCoordinator

app = (
    FastApiAdapter(machine=machine, auth_coordinator=NoAuthCoordinator(context=Context()), title="Orders API")
    .post("/orders", CreateOrderAction, tags=["orders"])
    .build()                                  # -> FastAPI; serve with uvicorn
)
```

- A fluent builder `.post/.get/.put/.delete/.patch(path, ActionClass, ...)` → `.build()` → a FastAPI app.
- **OpenAPI is derived from the code** — `Params`/`Result`, `Field(description=…)`, `@meta`; Swagger at `/docs`.
- **`auth_coordinator` is mandatory** (`None` → `TypeError`); for open access use `NoAuthCoordinator(context=Context())`. See [Authentication](../tutorials/step-12-authentication.md).
- Machine errors → HTTP codes: `AuthorizationError` → 403, `ValidationFieldError` → 422, anything else → 500; an auto `GET /health`.
- A mismatch between the external schema and the contract — `request_model`/`response_model` + `params_mapper`/`response_mapper` (see [Schema converters](../tutorials/step-18-converters.md)); open resources per request — the `connections=` argument (see [Connections at the boundary](../tutorials/step-17-connections.md)).

In full, broken down by section and with review questions — in the chapter [Step 13 — FastAPI adapter](../tutorials/step-13-fastapi.md).

---

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>
