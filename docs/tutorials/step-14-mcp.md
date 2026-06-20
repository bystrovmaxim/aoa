<!-- translated-from: step-14-mcp_draft.md @ 2026-06-17T17:53:37Z · sha256:daac6ed50ef6 -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Step 14 — MCP adapter

<table width="100%"><tr>
  <td align="left"><a href="step-13-fastapi.md">← Step 13 — FastAPI</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-15-schema-results.md">Step 15 — Result by schema →</a></td>
</tr></table>

- [A minimal server](#a-minimal-server)
- [The tool schema — from the contract](#the-tool-schema--from-the-contract)
- [Tool names and register_all](#tool-names-and-register_all)
- [What happens per call](#what-happens-per-call)
- [A response envelope instead of HTTP codes](#a-response-envelope-instead-of-http-codes)
- [Authentication](#authentication)
- [When the external schema diverges from the contract](#when-the-external-schema-diverges-from-the-contract)
- [Testing](#testing)
- [Invariants](#invariants)
- [Review questions](#review-questions)

---

In AOA an AI agent is an equal consumer of the system, on a par with a human behind HTTP. An operation already available over [HTTP](step-13-fastapi.md) becomes a tool for a language model by adding one adapter — `McpAdapter`. The logic is not duplicated or rewritten for another protocol: the same `Action` knows nothing about MCP exactly as it knows nothing about HTTP.

[MCP](https://modelcontextprotocol.io) (Model Context Protocol) is the transport by which an agent calls external tools. The adapter derives the tool schema from `Params`, the description from `@meta`, and builds a handler that delegates to the [machine](step-11-machine.md).

Install: `pip install "aoa-action-machine[mcp]"`.

[▶ Try in Colab](https://drive.google.com/file/d/1MQBDfiix8uyixiQbbDnS-g_FWz0pdp2R/view?usp=drive_link) · [Open in project](../../examples/step_14_mcp/01_tool.py)

---

## A minimal server

The adapter is assembled the same fluent way as [FastAPI](step-13-fastapi.md): `.tool(...)` per tool, `.build()` returns a ready MCP server (`FastMCP`).

```python
from aoa.action_machine.adapters.mcp import McpAdapter
from aoa.action_machine.auth import NoAuthCoordinator
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine

machine = ActionProductMachine()

server = (
    McpAdapter(machine=machine, auth_coordinator=NoAuthCoordinator(), server_name="Greetings MCP")
    .tool("greetings.greet", GreetAction)
    .tool("greetings.admin_ping", AdminPingAction)
    .build()
)
# server.run()  — serve over stdio/SSE to an MCP client
```

**Running the example** (calls the server in-process via `server.call_tool`, without an MCP client or LLM):

```bash
uv run python examples/step_14_mcp/01_tool.py
```

**Output:**

```text
Tools exposed to the agent:
  greetings.greet        inputSchema.required=['name']
  greetings.admin_ping   inputSchema.required=['name']

Calls:
  greet(name=Alice)      -> isError=False  {"ok": true, "code": "OK", "data": {"message": "Hello, Alice!"}}
  admin_ping(name=Alice) -> isError=True  {"ok": false, "code": "PERMISSION_DENIED", "message": "Access denied. Required role: 'admin', user roles: []", "details": {}}
  greet()  [no name]     -> ToolError: inputSchema rejected the call ('name' is required)
```

The main things are visible: the tool schema is derived from `Params` (`required=['name']`), a successful call returns an `ok` envelope, an operation protected by `@check_roles(AdminRole)` gives an anonymous agent a `PERMISSION_DENIED` envelope with `isError=true`, and a call without the required argument is rejected at the protocol boundary.

## The tool schema — from the contract

The tool's `inputSchema` is generated from the Pydantic `Params` model (`model_json_schema`), and the description — from [`@meta`](step-01-action-and-pipeline.md). No separate schema for the agent needs to be written: `Field(description=...)` and constraints (`gt`, `min_length`, …) land in the schema and guide the model — it "sees" what to pass and in what format. The same contract that describes the operation for a human describes it for the agent.

## Tool names and register_all

A tool name is the identifier the agent names when calling. The recommended format is `domain.action` (`orders.create`); an empty name is forbidden (`ValueError`).

When you need to expose the whole operation catalog to the agent at once, instead of listing `.tool(...)` by hand there is `.register_all()` — it registers all operations from the graph (those with at least one aspect), deriving the name from the class name in snake_case without the `Action` suffix (`CreateOrderAction → create_order`):

```python
server = McpAdapter(machine, NoAuthCoordinator()).register_all().build()
```

## What happens per call

On each tool call the handler takes the same path as an [HTTP endpoint](step-13-fastapi.md#what-the-adapter-does-per-request):

1. **Argument validation.** The MCP layer checks the call arguments against `inputSchema` — **before** the handler. A mismatch with the schema (a missing required field, a wrong type) is rejected right here as a protocol error (`ToolError`), the operation is not run.
2. **`Context`** through `auth_coordinator`.
3. **Connections** — the declared `@connection` slots are resolved.
4. **Run** — `machine.run(context, action, params, connections)` along the [pipeline](step-11-machine.md).
5. **Response** — the `Result` is serialized and wrapped in an envelope.

## A response envelope instead of HTTP codes

Here is the main difference from HTTP. MCP has no status codes; the handler **never throws an exception outward**, but always returns a call result with a JSON envelope and an `isError` flag, so that the agent can react to structure rather than parse prose:

```json
{"ok": true, "code": "OK", "data": { ... }}
```

On failure — `isError=true` and a stable code:

| `code` | When |
|--------|------|
| `OK` | success; the payload is in `data` |
| `PERMISSION_DENIED` | `AuthorizationError` (failed `@check_roles`) |
| `INVALID_PARAMS` | `ValidationFieldError` (for the tool input, the details are in `details.errors`) |
| `INTERNAL_ERROR` | any other error |

A security-important detail: on `INTERNAL_ERROR` the message is fixed — `"Unexpected failure"` — while the real exception is written to the log but **not given to the agent**. A language model must not see a traceback and internal details of a failure.

## Authentication

`auth_coordinator` is mandatory — as with [FastAPI](step-13-fastapi.md#authentication-is-mandatory), `None` fails immediately. For an open server it is declared explicitly — `NoAuthCoordinator()` (anonymous `Context`), and then only operations with [`@check_roles(GuestRole)`](step-03-authorization-and-roles.md) work; a protected operation answers the agent `PERMISSION_DENIED`, like `admin_ping` in the example.

Extracting the agent's credentials from the MCP call itself (an api-key or token from the request metadata) is on the roadmap, together with the [four ready methods](step-12-authentication.md#four-ready-methods) of authentication. The mechanism is the same: only the extractor is protocol-dependent, while `@check_roles` checks roles identically for HTTP and MCP — the agent will not get access to what it is not allowed.

## When the external schema diverges from the contract

Schema reconciliation is arranged identically to [FastAPI](step-13-fastapi.md#when-the-external-schema-diverges-from-the-contract): `request_model`/`response_model` set the external shape, while `params_mapper`/`response_mapper` translate it into the operation's `Params`/`Result` and back — at the adapter boundary, without touching the `Action` itself.

```python
.tool(
    "greetings.greet_v2",
    GreetAction,
    request_model=GreetV2Body,
    response_model=GreetV2Response,
    params_mapper=lambda body: GreetParams(name=body.to),
    response_mapper=lambda result: GreetV2Response(greeting=result.message),
)
```

The result itself can also be returned by schema — as a complex object or a partial entity projection; the [next topic](step-15-schema-results.md) is devoted to this.

## Testing

MCP tools are tested with the same `ActionProductMachine` as in production, by calling `server.call_tool(name, arguments)` in-process — without an MCP client and without an LLM (exactly how the example is built). This checks the schema, the handler, and the response envelope all at once. To control the result, you stub only `machine.run`, not the whole stack.

## Invariants

- **The same `Action`, a different transport.** The operation knows nothing of MCP; the tool is built from its contract.
- **The schema from the contract.** `inputSchema` — from `Params` (`model_json_schema`), the description — from `@meta`.
- **`auth_coordinator` is mandatory.** An open server is `NoAuthCoordinator()`; `@check_roles` works identically for HTTP and MCP.
- **Arguments validated at the boundary.** A mismatch with `inputSchema` is rejected as a `ToolError` before the operation runs.
- **An envelope instead of codes.** Each call returns a `CallToolResult` with a JSON envelope and `isError`; codes `OK` / `PERMISSION_DENIED` / `INVALID_PARAMS` / `INTERNAL_ERROR`.
- **Internal errors do not leak.** `INTERNAL_ERROR` returns a fixed message; the real exception only to the log.

The full list is in [Intents and invariants](../reference/intents-and-invariants.md); the terms are in the [Glossary](../reference/glossary.md).

## Summary

`McpAdapter` publishes an operation as a tool for an AI agent: the tool schema is derived from `Params`, the description from `@meta`, and the handler delegates to the machine. Unlike HTTP, MCP has no status codes — each call returns a JSON envelope with `isError` and a stable code, and internal errors do not leak to the agent. Authentication and schema reconciliation are arranged the same as in FastAPI; per-request extraction of the agent's credentials is on the roadmap. The same `Action` thus reaches both HTTP and MCP at once.

Next — **[Result by JSON schema](step-15-schema-results.md)**: how to return a complex object or a partial entity projection with schema validation.

---

## Review questions

1. Why can the same `Action` be released over both HTTP and MCP without changing its code?
2. Where do the tool's `inputSchema` and its description come from? What does that give the language model?
3. How does an MCP response fundamentally differ from a FastAPI response? Why does the handler not throw an exception outward?
4. Which four codes can the envelope return, and which outcome does each correspond to?
5. Why, on `INTERNAL_ERROR`, is the agent given a fixed message rather than the exception text?
6. At which stage is a call with a missing required argument rejected — before or after the operation runs?
7. What does `register_all()` do, and when is it more convenient than listing `.tool(...)` by hand?

> **Exercise.** In [01_tool.py](../../examples/step_14_mcp/01_tool.py) add a third tool via `.tool(...)` and confirm through `server.list_tools()` that its `inputSchema` is derived from `Params`. Then call the protected operation and compare the `PERMISSION_DENIED` envelope (`isError=true`) with a successful `OK` — this is the response protocol the agent relies on.

---

<table width="100%"><tr>
  <td align="left"><a href="step-13-fastapi.md">← Step 13 — FastAPI</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-15-schema-results.md">Step 15 — Result by schema →</a></td>
</tr></table>
