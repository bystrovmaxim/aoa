<!-- translated-from: mcp_draft.md @ 2026-07-10T13:56:17Z (filesystem mtime; draft is gitignored, no git history) · sha256:10597f139365 -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# MCP — an operation as a tool for an AI agent

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>

- [What MCP is](#what-mcp-is)
- [Two protocols: «how to call» and «what it means»](#two-protocols-how-to-call-and-what-it-means)
- [The essentials](#the-essentials)

---

`McpAdapter` publishes the same operation as a tool for a language model — without duplicating the logic. This page is a short card; the **full guide is the chapter [Step 14 — MCP adapter](../tutorials/step-14-mcp.md)**. But MCP is a new topic, so a few words about it first.

## What MCP is

**MCP (Model Context Protocol)** is an open protocol by which AI agents (LLMs) call external tools and data: a single way to declare a tool, describe its parameters, invoke it, and get the result. Roughly speaking, MCP is to an agent what HTTP is to a browser: a common language for accessing the outside world. The specification — [modelcontextprotocol.io](https://modelcontextprotocol.io).

## Two protocols: «how to call» and «what it means»

MCP answers the question **«how to call»** a tool — the call syntax. AOA answers a different one: **«what it means»** — the operation's semantics (its contract from `Params`/`Result`/`@meta`, roles, steps). AOA does for AI the same thing MCP does for calls: it gives a **semantic vocabulary, not just syntax**.

Together they turn an agent from a blind caller into an **understanding participant**: it does not just pull a tool, it can reason — «this operation requires the admin role», «the payment step is failing right now — do not call it». That is why in AOA an AI agent is an equal consumer of the system, on a par with a human behind [HTTP](fastapi.md).

## The essentials

Installation: `pip install aoa-mcp-adapter`.

```python
from aoa.mcp import McpAdapter
from aoa.action_machine.auth import NoAuthCoordinator

server = (
    McpAdapter(machine=machine, auth_coordinator=NoAuthCoordinator(context=Context()), server_name="Orders MCP")
    .tool("orders.create", CreateOrderAction)
    .build()                                  # -> FastMCP
)
```

- A fluent builder `.tool(name, ActionClass, ...)` → `.build()` → an MCP server (`FastMCP`); `.register_all()` publishes the whole catalog of operations.
- **The tool's `inputSchema` comes from `Params`**, the description — from `@meta`: the agent receives an exact contract, no schema to write.
- **`auth_coordinator` is mandatory** (as in [FastAPI](fastapi.md)); use `NoAuthCoordinator(context=Context())` for an open server.
- **Per-tool override.** `.tool(name, Action, auth_coordinator=...)` — the same mechanism as [FastAPI](fastapi.md#the-essentials): one tool uses its own coordinator instead of the adapter's default.
- **The response is not an HTTP code but a JSON envelope** with an `isError` flag and a stable code: `OK` / `PERMISSION_DENIED` / `INVALID_PARAMS` / `INTERNAL_ERROR`; on `INTERNAL_ERROR` the traceback is written to the log but **not handed to the agent**.
- Reconciling external schemas (`request_model`/`response_model` + mappers) — [Schema converters](../tutorials/step-18-converters.md); per-call resources — the `connections=` argument.

In full, with a breakdown of the response envelope and review questions — in the chapter [Step 14 — MCP adapter](../tutorials/step-14-mcp.md). Example: [01_tool.py](../../examples/step_14_mcp/01_tool.py).

---

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>
