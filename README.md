<p align="center">
  <img src="docs/assets/aoa-logo.png" alt="AOA" width="660"><br><br>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.12%2B-blue?logo=python&logoColor=white" alt="Python 3.12+"></a>
  <a href="https://github.com/bystrovmaxim/aoa"><img src="https://img.shields.io/badge/license-MIT-green" alt="MIT"></a>
  <a href="https://github.com/bystrovmaxim/aoa/actions/workflows/ci.yml"><img src="https://github.com/bystrovmaxim/aoa/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/tests-2076-brightgreen" alt="2076 tests">
  <img src="https://img.shields.io/badge/version-1.0.0-informational" alt="1.0.0">
</p>

# AOA — Action-Oriented Architecture

**AOA** is a Python architecture and runtime where business operations are not scattered across controllers, services, repositories, middleware, and background jobs. They are first-class executable objects.

In most systems, the real scenario is visible only after a forensic read: open the HTTP handler, follow the service, inspect the repository, check auth middleware, find the transaction boundary, search for cache, and hope rollback is not hidden in a broad `except`.

AOA turns that inside out. A business operation is an `Action`: typed input, ordered pipeline, explicit roles, declared dependencies, optional compensations, explicit error handlers, cache policy, plugin events, and one typed result.

Open one class and you can answer the questions that usually require a debugging session:

- Who can run this operation?
- Which steps execute, and in what order?
- Which intermediate facts does each step promise?
- Which dependencies and connections can it touch?
- What rolls back when a later step fails?
- How does it become HTTP, MCP, a graph, an audit trail, or an OCEL log?

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

This is not “documentation near the code”. It is the code path itself. `ActionProductMachine` reads the contract and drives execution: checks roles, runs steps in order, validates state, rolls back compensations, routes errors, applies cache, and emits plugin events.

← [Full example with all features](examples/full_example.py)

---

## The Invisible Thing AOA Makes Visible

The real product in AOA is not a decorator API. It is a **machine-readable business model**.

Because intent is formalized in code, the system can produce views that normally rot in separate tools:

- **Access matrix** — Actions × Roles from `@check_roles`
- **Business capability catalog** — domains and Actions from `@meta`
- **Execution graph** — pipeline steps, dependencies, compensators, error handlers
- **Transport schemas** — OpenAPI and MCP tools from `Params`, `Result`, and field metadata
- **Architecture diff** — “fraud check added before payment” instead of “47 files changed”
- **Process mining log** — OCEL events tied to domain objects
- **Interactive diagrams** — Maxitor renders full graph, ERD, use case, and lifecycle views from code

That is the disruptive part: the framework does not ask developers to keep diagrams, policies, and runtime behavior synchronized. It makes them consequences of the same executable contract.

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

`ActionProductMachine` is the single entry point for an `Action`. You do not call business methods directly. You pass Action, Params, and Context to the machine, and the machine enforces the contract.

That matters because infrastructure stops being ad hoc. The same executor powers production runs, tests, adapters, plugins, cache, logs, and process mining. There is no “real service path” and “test shortcut” drifting apart.

On startup and run, the machine can validate things humans usually discover too late: wrong `@on_error` order, missing summary aspect, undeclared connection, cyclic dependency, invalid state shape, impossible include contract.

`TestBench` uses the same machine. Adapters use the same machine. Maxitor reads the same declarations. OCEL uses the same plugin events. The machine does not change; only the surrounding environment changes.

---

## How To Read The System

### 1. Start With A Capability

An `Action` is the boundary of a business capability. It has typed `Params`, one typed `Result`, and an ordered pipeline. `regular_aspect` methods build facts in `state`; `summary_aspect` turns the final state into the result.

One Action means one public operation. Not one controller route. Not one service method. One business capability.

→ [Action and Pipeline](packages/aoa-action-machine/README.md#5-core-actions-and-pipeline)

---

### 2. Look For Reversibility

In most systems, rollbacks hide in `finally` and `except`. Their link to a business step is unclear, and order is accidental. In AOA, compensations are declared next to the step they undo. If something fails later in the pipeline, the machine runs registered compensators in reverse order automatically.

→ [Saga and compensations](packages/aoa-action-machine/README.md#53-saga-rollback-without-hidden-magic)

---

### 3. Check The Failure Contract

When an error handler lives in a random `except Exception`, nobody validates it until an incident. AOA turns error handling into a contract: `@on_error` declares which error type is caught and what is returned. Handler order matters — the machine checks it at startup.

→ [Explicit error handling](packages/aoa-action-machine/README.md#54-explicit-errors-on_error)

---

### 4. Follow The Declared Edges

Dependencies, connections, and context reads are not supposed to appear from nowhere. AOA makes the operation’s edges visible: resources and child Actions through `@depends`, already-open handles through `@connection`, request metadata through `@context_requires`.

That is why Maxitor can draw the graph. The graph is not reverse-engineered from arbitrary Python. It is declared.

→ [Dependencies, connections, context](packages/aoa-action-machine/README.md#55-depends-all-dependencies-visible-in-the-header)

---

### 5. Add Infrastructure Without Smearing It

Infrastructure rules — cache, logs, audit, metrics — in classic services wrap business code. AOA takes another path: cache is declared as intent, logs go through channels without transport coupling, and plugins fill gaps between steps without touching business code.

→ [Cache, logs, plugins](packages/aoa-action-machine/README.md#58-logs-that-do-not-clutter-business-code)

---

### 6. Observe The Business, Not Just The Server

A plain log says “this function ran”. OCEL says how business objects moved through events over time. With `aoa-action-machine[ocel]`, Action execution can become object-centric process data for tools such as pm4py, ProM, and OC-PM.

→ [OCEL](packages/aoa-action-machine/README.md#511-ocel-process-mining-out-of-the-box)

---

### 7. Model The Domain When It Matters

Behind Actions sits a data model independent of a specific database. `BaseEntity` describes domain object structure: fields, relations, lifecycle. A resource decides where data comes from and how to build the entity — PostgreSQL, ClickHouse, HTTP API, fixture. Hexagonal style: consumers do not depend on the database; the database does not know consumers.

→ [Domain modeling](packages/aoa-action-machine/README.md#6-extended-domain-modeling)

---

### 8. Test The Same Path

Classic mocked tests drift from reality: a mocked interface changes, or the mock returns what a real resource never would. `TestBench` uses a full `ActionProductMachine` — not a stub. Code and machine stay the same — only the environment changes.

→ [Testing](packages/aoa-action-machine/README.md#512-testing-the-same-machine-a-different-reality)

---

### 9. Publish The Same Operation Everywhere

A business operation should not know where the call came from. `FastApiAdapter` and `McpAdapter` take an Action with Pydantic Params/Result and expose HTTP endpoints or MCP tools — no duplicated logic, no extra DTOs.

→ [Adapters](packages/aoa-action-machine/README.md#513-adapters-http-and-mcp-from-one-source)

---

### 10. See The System

Architecture diagrams go stale. Maxitor fixes that radically: it generates interactive diagrams from code in the browser. Everything declared via intents lands in the graph — no Miro, no Confluence, no manual updates.

→ [aoa-maxitor: full documentation](packages/aoa-maxitor/README.md)

---

## Intent-Oriented Programming

In short, AOA is a practical take on Intent-Oriented Programming.

**Intent is code.** Intent does not describe implementation from the side. It participates in execution: roles are checked, the pipeline runs, checkers validate `state`, compensators are invoked.

**Intent is observable.** Once intents are explicit, the system can be observed automatically: OpenAPI, MCP schema, graph, ERD, use case, OCEL, structured logs.

**Intent is constrained.** An Action is not infinite room for implicit rules. If a role, step result, error handler, compensation, or cache is not declared, the machine will not pretend it exists.

The developer thinks not “how to write code” but “what is the operation’s intent”. Infrastructure follows intent, not the other way around.
