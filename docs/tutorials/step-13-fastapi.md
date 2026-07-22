<!-- translated-from: step-13-fastapi_draft.md @ 2026-07-11T15:02:03Z (filesystem mtime; draft is gitignored, no git history) · sha256:e9c82664b0dc -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Step 13 — FastAPI adapter

<table width="100%"><tr>
  <td align="left"><a href="step-12-authentication.md">← Step 12 — Authentication</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-14-mcp.md">Step 14 — MCP →</a></td>
</tr></table>

- [A minimal service](#a-minimal-service)
- [What the adapter does per request](#what-the-adapter-does-per-request)
- [Routes and parameters](#routes-and-parameters)
- [Authentication is mandatory](#authentication-is-mandatory)
- [OpenAPI from code](#openapi-from-code)
- [When the external schema diverges from the contract](#when-the-external-schema-diverges-from-the-contract)
- [Errors](#errors)
- [Testing](#testing)
- [Invariants](#invariants)
- [Review questions](#review-questions)

---

The [machine](step-11-machine.md) gives a single entry into an operation, but on its own it lives inside the process. To make the operation available from the outside over HTTP, it must be released into a transport — and here the temptation arises to mix business logic with the web layer: parse the request body, check the token, assemble the response — all right in the handler. AOA separates this: the transport lives in an **adapter**, and the `Action` stays clean.

`FastApiAdapter` publishes an operation as an HTTP endpoint — **without changing its code**. The adapter takes on the whole transport: it validates the request, builds [`Context`](step-12-authentication.md) through the authentication coordinator, runs the operation on the [machine](step-11-machine.md), and turns the `Result` back into JSON. The same `Action` thus reaches both HTTP and (through [MCP](step-14-mcp.md)) an AI agent.

Install: `pip install aoa-fastapi-adapter`.

[▶ Try in Colab](https://drive.google.com/file/d/1b2H35JM9YfR8NxvqBEsO-SniygjlZtBH/view?usp=drive_link) · [Open in project](../../examples/step_13_fastapi/01_service.py)

---

## A minimal service

The adapter is assembled fluently: each `.post/.get/...` call is one endpoint, and `.build()` returns a ready FastAPI app.

```python
from aoa.fastapi import FastApiAdapter
from aoa.action_machine.auth import NoAuthCoordinator
from aoa.action_machine.context import Context
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine

machine = ActionProductMachine()

app = (
    FastApiAdapter(machine=machine, auth_coordinator=NoAuthCoordinator(context=Context()), title="Greetings API")
    .post("/greet", GreetAction, tags=["greetings"])
    .build()
)
# uvicorn module:app
```

`GreetAction` stays an ordinary operation — it knows nothing about HTTP. The adapter import is from `aoa.fastapi`.

## What the adapter does per request

On each request the endpoint takes the same path:

1. **Request validation.** FastAPI parses the body/query string into a Pydantic model (by default — the operation's `Params`).
2. **`Context`.** `auth_coordinator.process(request)` is called — the call context is built.
3. **Connections.** The declared `@connection` slots are resolved, if any.
4. **Run.** `machine.run(context, action, params, connections)` — the operation goes along the [pipeline](step-11-machine.md) (access, cache, aspects, sagas, errors).
5. **Response.** The `Result` is serialized into JSON.

Plus, `build()` adds a service `GET /health` → `{"status": "ok"}` and a wrapper guaranteeing HTTP 500 on any uncaught error.

## Routes and parameters

Available are `post / get / put / delete / patch` — all return `self` for chaining. How parameters are passed the adapter chooses itself:

- **POST/PUT/PATCH** with non-empty `Params` → parameters in the JSON body;
- **GET/DELETE** with non-empty `Params` → parameters from the query and the path (`/orders/{order_id}` → `order_id` from the path, the rest from the query);
- **empty `Params`** → an endpoint with no body and no query.

Each route has `tags`, `summary`, `operation_id`, `deprecated` for OpenAPI.

## Authentication is mandatory

`auth_coordinator` is a required argument: `None` fails immediately with `TypeError`, so that authentication cannot be forgotten by oversight. For an open API it is declared explicitly — `NoAuthCoordinator(context=Context())`. The coordinator builds `Context` at the transport boundary; the machine receives it ready (in detail — in the [Authentication](step-12-authentication.md) chapter).

A specific route can override this default with its own coordinator — `auth_coordinator=` in `.post/.get/.put/.delete/.patch(...)`:

```python
app = (
    FastApiAdapter(machine=machine, auth_coordinator=strict_jwt_coordinator)
    .post("/auth/login", LoginAction, auth_coordinator=NoAuthCoordinator(context=Context()))  # exception
    .post("/orders", CreateOrderAction)                                                        # inherits the default
    .build()
)
```

Without `auth_coordinator=` on the route, the adapter default applies.

[▶ Try in Colab](#02_auth_override.ipynb) · [Open in project](../../examples/step_13_fastapi/02_auth_override.py)

## OpenAPI from code

The OpenAPI schema is generated from what is already declared in the code: field descriptions from `Field(description=...)`, constraints from `Field(gt=0, min_length=3, ...)`, the summary from `@meta`, the tags from the route registration. No separate schema needs to be written — Swagger UI is available at `/docs`.

## When the external schema diverges from the contract

The external schema does not always match the operation's contract: a new API version came out, the frontend renamed a field, a partner needs a different format. There is no need to change the `Action` itself — the translation is placed at the adapter boundary:

- `request_model` — the Pydantic model of the external request; `params_mapper(body)` brings it to the operation's `Params`;
- `response_model` — the external response model; `response_mapper(result)` brings the `Result` to it.

```python
.post(
    "/greet/v2",
    GreetAction,
    request_model=GreetV2Body,                                  # external schema (field `to`)
    response_model=GreetV2Response,                             # external schema (field `greeting`)
    params_mapper=lambda body: GreetParams(name=body.to),       # request -> Params
    response_mapper=lambda result: GreetV2Response(greeting=result.message),  # Result -> response
)
```

So v1 and v2 live side by side, and `GreetAction` does not change — all the difference between versions lies at the adapter boundary, exactly where it belongs. (A mapper and its corresponding `*_model` are set as a pair: a `response_mapper` without a `response_model` will return a result that does not match the response contract.) Returning the result itself by schema is a separate topic of the [next chapters](step-15-schema-results.md).

## Errors

The adapter translates machine errors into HTTP codes:

| Exception | Code |
|-----------|------|
| `AuthorizationError` | 403 |
| `ValidationFieldError` | 422 |
| everything else (uncaught) | 500 |

## Testing

The adapter is tested with the same `ActionProductMachine` as in production, through FastAPI's `TestClient` — it works in-process, without starting a server.

**Run:**

```bash
uv run python examples/step_13_fastapi/01_service.py
```

**Output:**

```text
GET  /health     -> 200 {'status': 'ok'}
POST /greet      -> 200 {'message': 'Hello, Alice!'}
POST /admin/ping -> 403 {'detail': "Access denied. Required role: 'admin', user roles: []", 'reason': 'FORBIDDEN_ROLE', 'level': 1}
POST /greet/v2   -> 200 {'greeting': 'Hello, Bob!'}
```

Everything is visible at once: the open operation answers 200, the one protected by `@check_roles(AdminRole)` gives 403 for an anonymous call, and the `/greet/v2` route swaps the external schema without touching the operation. Controlling results in a test is convenient by stubbing only `machine.run`, not the whole stack.

## Invariants

- **Transport in the adapter, not the operation.** The `Action` knows nothing of HTTP; the adapter builds the app from `Params`/`Result` and `@meta`.
- **`auth_coordinator` is mandatory.** `None` → `TypeError`; open access is declared explicitly via `NoAuthCoordinator(context=Context())`.
- **A route can override the coordinator.** `.post(path, Action, auth_coordinator=...)` — without it, the adapter default applies (`BaseAdapter.effective_auth_coordinator`).
- **Parameters by method.** POST/PUT/PATCH → body, GET/DELETE → query and path, empty `Params` → no body.
- **OpenAPI from code.** The schema and `/docs` are derived from the contract; no separate specification is needed.
- **Schema translation at the boundary.** `request_model`/`response_model` + `params_mapper`/`response_mapper` reconcile the external shape with the contract, without touching the `Action`.
- **Errors → codes.** `AuthorizationError` → 403, `ValidationFieldError` → 422, the rest → 500; `GET /health` is added automatically.

The full list is in [Intents and invariants](../reference/intents-and-invariants.md); the terms are in the [Glossary](../reference/glossary.md). Why the transport is moved into the adapter is in the [Comparison with FastAPI](../explanation/comparison.md#fastapi).

## Summary

`FastApiAdapter` releases an operation over HTTP without mixing transport into the business logic: a fluent builder registers routes, derives OpenAPI from `Params`/`Result`/`@meta`, builds `Context` through the mandatory `auth_coordinator`, and translates machine errors into HTTP codes. When the external schema diverges from the contract, the translation is placed at the adapter boundary via `*_model` + `*_mapper`, while the `Action` itself stays unchanged. The same `Action` also reaches an AI agent — about which the next chapter.

Next — **[MCP](step-14-mcp.md)**: how to publish the same operation as a tool for a language model.

---

## Review questions

1. Why is the transport moved into the adapter rather than written in the handler next to the business logic? What, thanks to this, does the `Action` not know?
2. Which five steps does each HTTP request take from validation to response?
3. Why is `auth_coordinator` a required argument, and how do you declare an open endpoint?
4. How does the adapter decide where to take parameters from — the body, the query, or the path?
5. Where does the OpenAPI schema come from? What do you need to write additionally for it?
6. An external API renamed a request field. How do you reconcile it with the operation's contract without changing the `Action`?
7. Into which HTTP codes are `AuthorizationError` and `ValidationFieldError` translated?
8. A route needs open access, but the adapter default is strict. How do you express that without weakening the default for every other route?

> **Exercise.** In [01_service.py](../../examples/step_13_fastapi/01_service.py) add a `GET` route for an operation with non-empty `Params` and verify through `TestClient` that the parameters are read from the query. Then add a `response_model`/`response_mapper` to one of the routes and confirm that the external response schema changed, while the `Action` itself stayed the same.

---

<table width="100%"><tr>
  <td align="left"><a href="step-12-authentication.md">← Step 12 — Authentication</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-14-mcp.md">Step 14 — MCP →</a></td>
</tr></table>
