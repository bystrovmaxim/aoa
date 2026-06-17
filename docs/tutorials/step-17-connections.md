<!-- translated-from: step-17-connections_draft.md @ 2026-06-17T17:53:37Z · sha256:20f70f1418b1 -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Step 17 — Connections at the request boundary

<table width="100%"><tr>
  <td align="left"><a href="step-16-complex-input.md">← Step 16 — Complex input</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-18-converters.md">Step 18 — Schema converters →</a></td>
</tr></table>

- [Two modes](#two-modes)
- [What to choose](#what-to-choose)
- [Connections live next to the route](#connections-live-next-to-the-route)
- [The same in MCP](#the-same-in-mcp)
- [Invariants](#invariants)
- [Review questions](#review-questions)

---

In the chapter on [dependencies](step-06-dependencies.md) an operation declared an open resource with `@connection`, and an aspect read it from `connections["key"]`. There the connection was supplied by hand to `machine.run(..., connections={"ledger": ledger})`. Now the service-layer question: at the transport boundary, **who** supplies that connection, and **when**, on each incoming request?

The answer is the adapter, through the keyword-only `connections=` argument right at the registration of a route ([FastAPI](step-13-fastapi.md)) or a tool ([MCP](step-14-mcp.md)). And it can be done in **two modes**. The operation does not change: the adapter calls `resolve_connections(...)` before `machine.run`, and the aspect still simply reads `connections["ledger"]`, not knowing how the resource was supplied.

[▶ Try in Colab](https://drive.google.com/file/d/12lQFM0LMAejLSmEUKss8I6tmbpCsyUkr/view?usp=drive_link) · [Open in project](../../examples/step_17_connections/01_connections.py)

---

## Two modes

A value in the `connections` dictionary comes in exactly two kinds:

```python
# Mode 1 — a ready BaseResource: the same instance on every request
.post("/record", RecordAction, connections={"ledger": shared_ledger})

# Mode 2 — PerCallConnection: factory() runs on every request -> a fresh instance
.post("/record", RecordAction,
      connections={"ledger": PerCallConnection(factory=lambda: LedgerResource())})
```

- **A ready `BaseResource`** — you pass an already-built instance. `resolve_connections` returns it as is, so **all requests share one object** (and the state accumulated in it).
- **`PerCallConnection(factory=...)`** — you pass a factory. It is called on **every** connection resolution, that is, a **fresh** resource is born per request.

In the example `LedgerResource` remembers its instance number, and the difference is visible at once:

**Run:**

```bash
uv run python examples/step_17_connections/01_connections.py
```

**Output:**

```text
Mode 1 — ready BaseResource (shared, one instance):
  POST /record/shared  call 1 -> {'ledger_id': 1, 'entries': 1}
  POST /record/shared  call 2 -> {'ledger_id': 1, 'entries': 2}

Mode 2 — PerCallConnection (factory per request):
  POST /record/percall call 1 -> {'ledger_id': 2, 'entries': 1}
  POST /record/percall call 2 -> {'ledger_id': 3, 'entries': 1}
```

Mode 1: both requests hit the same instance `#1`, and entries accumulate in it (1 → 2). Mode 2: each request got a new instance (`#2`, then `#3`) — no state is shared.

## What to choose

- **A ready resource** — for the expensive and reusable: a connection pool, an HTTP client, an in-memory store. It is built once (usually in the app's `lifespan`) and supplied to all requests. If such a resource becomes available only after the app starts, it is kept in an external holder object and read from it inside `PerCallConnection.factory`.
- **`PerCallConnection`** — when the resource should have a **per-request lifetime**: its own connection or unit of work per call, with no shared state between requests. The factory is called synchronously on each resolution.

## Connections live next to the route

`connections=` is declared **on each route/tool**, not on the adapter as a whole. This is deliberate: an operation's dependencies are visible where it is published, and route A does not get route B's connections by mistake.

Checks are placed at two boundaries:

- **At registration.** A key is a non-empty string, no duplicates; a value is a `BaseResource` or a `PerCallConnection`, otherwise `TypeError` immediately.
- **Before the operation runs.** The machine checks the declared `@connection` keys against the supplied ones (the same check as with a manual `machine.run` from the [dependencies](step-06-dependencies.md) chapter): an extra key, a missing key, or a value that is not a `BaseResource` is an error before the first aspect. `PerCallConnection.factory` must return a `BaseResource`.

## The same in MCP

The `connections=` argument is identical on `FastApiAdapter` and on `McpAdapter.tool(...)` — both use one `resolve_connections`. So both modes work for an AI agent exactly as for HTTP: the connection is supplied on each tool call, and the operation stays transport-independent.

## Invariants

- **Two modes, and only two.** A `connections` value is a ready `BaseResource` (a shared instance) or `PerCallConnection(factory)` (fresh per request).
- **The operation does not know how it was supplied.** The adapter calls `resolve_connections` before `machine.run`; the aspect reads `connections["key"]`.
- **Per-route, not per-adapter.** Connections are declared on each route/tool; there is no adapter-global factory.
- **A double check.** The shape of the values — at registration; the correspondence with the declared `@connection` keys — before the operation runs.
- **One mechanism for FastAPI and MCP.** The same `connections=` and the same `resolve_connections`.

The full list is in [Intents and invariants](../reference/intents-and-invariants.md); the terms are in the [Glossary](../reference/glossary.md).

## Summary

At the transport boundary an operation's open resources are supplied by the adapter — through `connections=` next to the route or tool, in one of two modes: a ready `BaseResource` lives for the whole app and is shared across requests, while `PerCallConnection(factory)` gives birth to a fresh resource per request. The operation does not distinguish this: it only reads `connections["key"]`, while the machine checks the supplied against the declared `@connection` before the first aspect. So the dependency contract begun in the dependencies chapter is closed at the service layer — explicitly and verifiably.

Next — **[Schema converters](step-18-converters.md)**: how to reconcile an external request/response schema with the operation's contract when a new API version ships.

---

## Review questions

1. Which two modes does a `connections` value have, and how do they differ in the resource's lifetime?
2. Why does the operation not notice which mode the connection was supplied in? What does the adapter do for that?
3. When is a shared ready resource appropriate, and when is a `PerCallConnection`?
4. Why is `connections=` declared on the route rather than on the adapter as a whole?
5. At which two boundaries are connections checked, and what exactly is checked at each?
6. How does the behavior of `connections=` differ between FastAPI and MCP?

> **Exercise.** In [01_connections.py](../../examples/step_17_connections/01_connections.py) make `note` in `RecordParams` a required condition and call the `shared` route three times — watch `entries` grow in one instance. Then on the `percall` route replace the factory with `lambda: shared_ledger` (a ready instance inside `PerCallConnection`) and explain why the instance number stopped changing, although the mode is formally "per-call".

---

<table width="100%"><tr>
  <td align="left"><a href="step-16-complex-input.md">← Step 16 — Complex input</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-18-converters.md">Step 18 — Schema converters →</a></td>
</tr></table>
