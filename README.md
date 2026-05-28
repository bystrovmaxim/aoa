<p align="center">
  <img src="docs/assets/aoa-logo.png" alt="AOA" width="660"><br><br>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.12%2B-blue?logo=python&logoColor=white" alt="Python 3.12+"></a>
  <a href="https://github.com/bystrovmaxim/aoa"><img src="https://img.shields.io/badge/license-MIT-green" alt="MIT"></a>
  <a href="https://github.com/bystrovmaxim/aoa/actions/workflows/ci.yml"><img src="https://github.com/bystrovmaxim/aoa/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/tests-2076-brightgreen" alt="2076 tests">
  <img src="https://img.shields.io/badge/version-1.0.0-informational" alt="1.0.0">
</p>

# AOA — Action-Oriented Architecture

**AOA** is a Python framework where every business operation becomes a **self-documenting entity**.

In real applications, business operations rarely stay pure business logic. Neighboring layers start leaking in: transport brings request shape, security brings roles, the container brings dependencies, the database brings transactions, observability brings logs and trace ids, integrations bring retries, and errors bring rollbacks.

At the same time, hidden dependencies appear: a resource is pulled from an IoC container mid-method, context from thread-local, a connection from a global singleton. What an operation actually uses is clear only after reading the whole body. Eventually you stop knowing where business meaning ends and the infrastructure that serves it begins.

AOA solves this differently: **every system operation becomes a standalone entity** — an `Action`. Open one class and see its full contract: roles, pipeline steps, compensations, error handlers, cache, dependencies, context. Nothing outside, nothing hidden. Everything in its place.

```python
@meta(description="Place order", domain=StoreDomain)
@check_roles(ManagerRole)
@cache_key(lambda p, ctx: f"order:{p.order_id}")
class CreateOrderAction(BaseAction[CreateOrderParams, CreateOrderResult]):

    @depends(InventoryResource, PaymentGatewayResource)
    @regular_aspect("Reserve items")
    @compensate("Release reservation")
    async def reserve_items(self, params, state, box, deps):
        ...

    @regular_aspect("Charge payment")
    @on_error(PaymentGatewayError, description="Gateway error")
    async def charge_payment(self, params, state, box, deps):
        ...

    @summary_aspect("Confirm order")
    async def confirm_order(self, params, state, box, deps):
        ...
```

This is not just code — it is an **executable specification**. `ActionProductMachine` reads it and drives execution: runs steps in order, rolls back compensations on failure, routes errors, applies cache, invokes plugins. Intent no longer lives in Confluence or the author’s head.

← [Full example with all features](examples/full_example.py)

---

## Quick Start

```bash
pip install aoa-action-machine
```

```python
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator
from aoa.action_machine.auth import NoAuthCoordinator

class HelloParams(BaseParams):
    name: str

class HelloResult(BaseResult):
    message: str

@meta(description="Say hello")
class HelloAction(BaseAction[HelloParams, HelloResult]):

    @summary_aspect("Return greeting")
    async def greet(self, params, state, box, deps):
        return HelloResult(message=f"Hello, {params.name}!")

machine = ActionProductMachine(graph_coordinator=create_node_graph_coordinator())
result = asyncio.run(
    machine.run(HelloAction, HelloParams(name="World"), NoAuthCoordinator().make_context())
)
print(result.message)  # Hello, World!
```

---

## Packages


| Package                                                       | Contents                                                                    |
| ------------------------------------------------------------- | --------------------------------------------------------------------------- |
| `[aoa-action-machine](packages/aoa-action-machine/README.md)` | Framework core: Actions, pipeline, saga, cache, plugins, entities, testing |
| `[aoa-maxitor](packages/aoa-maxitor/README.md)`               | Visualizer: interactive graph, ERD, use cases, lifecycle from code         |


---

## ActionProductMachine — The Centerpiece

`ActionProductMachine` is the single entry point for any `Action`. You do not call class methods directly — you pass Action, Params, and Context to the machine, and it handles the rest.

On creation, the machine scans all registered Actions, builds the dependency graph, and validates declarations. Contract errors — wrong `@on_error` order, cyclic dependencies, missing required connections — are caught before the first request, not under load.

At runtime the machine sequentially: checks roles, wires dependencies via `Dependency`, runs the pipeline step by step, intercepts events for plugins, applies cache, and runs compensations on failure.

`TestBench` uses the same machine — not a simplified stub, not a mocked pipeline. Tests run a full `ActionProductMachine`: synchronous for simple tests or async for scenarios with `await`. The machine does not change — only the environment around it.

---

## What’s Inside: A Guide

### Action and Pipeline

`Action` is the boundary of a business capability with an explicit contract. `regular_aspect` methods build data in `state`; `summary_aspect` assembles the final result. Decorators on the class and methods are not comments — they are instructions to the machine. Change a decorator — change behavior.

- Pipeline steps (`@regular_aspect`, `@summary_aspect`) are executed by the machine in strict order
- Intermediate data accumulates in typed `state`, validated by checkers between steps
- `@meta`, `@check_roles`, `@result_string` declare Action invariants: domain, roles, expected step output
- One Action — one entry point, one result, no side paths

→ [Action and Pipeline](packages/aoa-action-machine/README.md#5-core-actions-and-pipeline)

---

### Saga and Compensations

In most systems, rollbacks hide in `finally` and `except`. Their link to a business step is unclear, and order is accidental. In AOA, compensations are declared next to the step they undo. If something fails later in the pipeline, the machine runs registered compensators in reverse order automatically.

- `@compensate` declares a rollback method on the regular aspect — the link is visible without reading the body
- On failure in any step, the machine walks completed steps in reverse and invokes compensators
- No `try/finally` manually tracking what ran and what did not
- A compensator is a full method with access to `state`: it knows what to persist or restore

→ [Saga and compensations](packages/aoa-action-machine/README.md#53-saga-rollback-without-hidden-magic)

---

### Explicit Error Handling

When an error handler lives in a random `except Exception`, nobody validates it until an incident. AOA turns error handling into a contract: `@on_error` declares which error type is caught and what is returned. Handler order matters — the machine checks it at startup.

- `@on_error(SomeError)` declares a handler as part of the Action contract, not a stray `except`
- Multiple handlers go from specific to general: the machine rejects a declaration if a broader handler is listed before a narrower one
- A handler receives `error` and `state` — it can return a fallback result or re-raise
- Errors not covered by handlers propagate upward — no silently swallowed exceptions

→ [Explicit error handling](packages/aoa-action-machine/README.md#54-explicit-errors-on_error)

---

### Dependencies, Connections, Context

In ordinary code, dependencies appear from nowhere: IoC in the method body, `request.user` via thread-local, a connection via a global singleton. In AOA everything is declared in the header. Read the first lines of the class — you know everything the operation uses.

- `@depends(ResourceA, ChildAction)` — the only way to get a resource or child action; without it `box.resolve()` fails; the system checks acyclic dependencies at startup
- `@connection(DBResource, key="db")` — for resources already opened outside: transactions, pools, app-level singletons; passed via adapter or caller
- `@context_requires("user_id", "trace_id")` — the aspect declares what it reads from context; `ContextView` blocks undeclared fields
- Together these three mechanisms make the dependency graph readable without analyzing method bodies

→ [Dependencies, connections, context](packages/aoa-action-machine/README.md#55-depends-all-dependencies-visible-in-the-header)

---

### Cache, Logs, Plugins

Infrastructure rules — cache, logs, audit, metrics — in classic services wrap business code. AOA takes another path: cache is declared as intent, logs go through channels without transport coupling, and plugins fill gaps between steps without touching business code.

- `cache_key` + `on_cache_write` — declarative cache policy; `on_cache_write` decides whether to cache from data or runtime; the full Action result is cached automatically
- `box.info(channel, message)` — structured logging via named channels; routing by level and channel — no `logging.getLogger` in business code
- Plugins (`@on(event)`) intercept events between pipeline steps (before/after aspect, on_error, on_compensate) and see a `state` snapshot — unique for logging intermediate states
- A custom `CacheCoordinator` controls TTL, size, and storage (local / Redis / any backend)

→ [Cache, logs, plugins](packages/aoa-action-machine/README.md#58-logs-that-do-not-clutter-business-code)

---

### OCEL: Process Mining Out of the Box

A plain log says what happened. OCEL says how business objects moved through events over time. Different levels of analysis. AOA can export process data as OCEL and analyze it in pm4py, ProM, or any Process Mining tool.

- `aoa-action-machine[ocel]` — optional extra, does not burden the base install
- `OcelPlugin` records Action execution events tied to domain objects
- Exported OCEL logs open in pm4py for process maps, deviation analysis, conformance checking
- The same event stream used for observability becomes input for process analytics

→ [OCEL](packages/aoa-action-machine/README.md#511-ocel-process-mining-out-of-the-box)

---

### Domain Modeling

Behind Actions sits a data model independent of a specific database. `BaseEntity` describes domain object structure: fields, relations, lifecycle. A resource decides where data comes from and how to build the entity — PostgreSQL, ClickHouse, HTTP API, fixture. Hexagonal style: consumers do not depend on the database; the database does not know consumers.

- Relations (`AssociationOne/Many`, `AggregateOne/Many`, `CompositeOne/Many`) are declared in the model; the system checks mirrored cardinality
- Partial read: if a field was not loaded — `FieldNotLoadedError` or `RelationNotLoadedError` instead of silent `None`; different DB queries return the same model with different load depth
- `Lifecycle` — a state machine in the model; Maxitor renders it as a graph
- `BaseEntity.schema()` — explicit projection of entity into `BaseResult` for APIs; change projection, not the model

→ [Domain modeling](packages/aoa-action-machine/README.md#6-extended-domain-modeling)

---

### Testing: Same Machine, Different Reality

Classic mocked tests drift from reality: a mocked interface changes, or the mock returns what a real resource never would. `TestBench` uses a full `ActionProductMachine` — not a stub. Code and machine stay the same — only the environment changes.

- `TestBench` supports sync and async runs; roles, checkers, plugins, step order — all real
- Dependencies and connections are replaced with test implementations — not `patch()`, but honest objects with the right behavior
- `rollup=True` runs against a real database but rolls back the transaction — no INSERTs remain
- Actions are stateless: each test gets a clean environment; no bugs leaking from the previous call

→ [Testing](packages/aoa-action-machine/README.md#512-testing-the-same-machine-a-different-reality)

---

### Adapters: One Action — Many Transports

A business operation should not know where the call came from. `FastApiAdapter` and `McpAdapter` take an Action with Pydantic Params/Result and expose HTTP endpoints or MCP tools — no duplicated logic, no extra DTOs.

- `FastApiAdapter` generates OpenAPI routes from `Params`/`Result`/`@meta`; change a field description — Swagger updates
- `McpAdapter` turns Actions into MCP tools for AI agents; agents get strict schemas and descriptions, not random functions
- One Action is callable via HTTP, MCP, CLI, or direct code — same contract
- Connections are passed through the adapter at configuration time, not baked into business code

→ [Adapters](packages/aoa-action-machine/README.md#513-adapters-http-and-mcp-from-one-source)

---

### Maxitor: A System You Can See

Architecture diagrams go stale. Maxitor fixes that radically: it generates interactive diagrams from code in the browser. Everything declared via intents lands in the graph — no Miro, no Confluence, no manual updates.

- Full graph: domains, Actions, pipeline steps, resources, dependencies, roles — the whole system as one interactive map
- Entity ERD by domain with fields, types, and relations — from `BaseEntity` code without hand-written schemas
- Use case diagrams: roles and Actions they can call, from `@check_roles`
- JSON API: diagram data as endpoints — embed in your portal or CI

→ [aoa-maxitor: full documentation](packages/aoa-maxitor/README.md)

---

## Intent-Oriented Programming

In short, AOA is a practical take on Intent-Oriented Programming.

**Intent is code.** Intent does not describe implementation from the side. It participates in execution: roles are checked, the pipeline runs, checkers validate `state`, compensators are invoked.

**Intent is observable.** Once intents are explicit, the system can be observed automatically: OpenAPI, MCP schema, graph, ERD, use case, OCEL, structured logs.

**Intent is constrained.** An Action is not infinite room for implicit rules. If a role, step result, error handler, compensation, or cache is not declared, the machine will not pretend it exists.

The developer thinks not “how to write code” but “what is the operation’s intent”. Infrastructure follows intent, not the other way around.
