<p align="center">
  <img src="docs/assets/aoa-logo.png" alt="AOA" width="660"><br><br>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.12%2B-blue?logo=python&logoColor=white" alt="Python 3.12+"></a>
  <a href="https://github.com/bystrovmaxim/aoa"><img src="https://img.shields.io/badge/license-MIT-green" alt="MIT"></a>
  <a href="https://github.com/bystrovmaxim/aoa/actions/workflows/ci.yml"><img src="https://github.com/bystrovmaxim/aoa/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/tests-2076-brightgreen" alt="2076 tests">
  <img src="https://img.shields.io/badge/version-1.0.0-informational" alt="1.0.0">
</p>

# AOA — Action-Oriented Architecture

**AOA** is a Python framework where business logic becomes an executable specification.

In real applications, business logic rarely stays clean. Adjacent layers seep in — transport dictates request shape, security enforces roles, the DI container injects dependencies, the database wraps transactions, observability adds logs and trace ids, integrations bring retries, error handling triggers rollbacks.

On top of that: hidden dependencies. A service is pulled from an IoC container via YAML config, context leaks from a thread-local, a connection comes from a global singleton. What an operation actually touches is only visible after reading the entire body — and at some point you can no longer tell where the business logic ends and the infrastructure that serves it begins.

AOA approaches this differently: **every business operation is a self-contained entity**, an `Action`. Open one class and you see roles, steps, compensations, error handlers, cache, dependencies, and context requirements. This is not documentation alongside code: `ActionProductMachine` reads this contract and executes it literally — driving the pipeline, rolling back completed steps, routing errors, wiring cache and plugins.

---

## Quick Start

```bash
pip install aoa-action-machine
```

```python
import asyncio
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

async def main():
    machine = ActionProductMachine(graph_coordinator=create_node_graph_coordinator())
    ctx = await NoAuthCoordinator().process(None)
    result = await machine.run(ctx, HelloAction(), HelloParams(name="World"))
    print(result.message)  # Hello, World!

asyncio.run(main())
```

← [Full example with all features](../../examples/full_example.py)

---

## Packages

| Package | Contents |
| ----------------------------------------------------------- | ------------------------------------------------------------------- |
| [aoa-action-machine](packages/aoa-action-machine/README.md) | Core: Actions, pipeline, sagas, cache, plugins, entities, testing |
| [aoa-maxitor](packages/aoa-maxitor/README.md) | Visualizer: interactive graph, ERD, use cases, lifecycle from code |

---

## Guide

> Code examples are in the core documentation [aoa-action-machine](packages/aoa-action-machine/README.md) and in the [examples/](../../examples/) folder. System visualization — in [aoa-maxitor](packages/aoa-maxitor/README.md).

### Action and Pipeline

**The entire business operation — in one class.** It reads top to bottom as a straight pipeline with a single entry point and a single result — no jumping between controllers, services, and helpers. Logic is split into steps, each step is a separate method with a clear contract. The contract exists both inside each step and outside the Action — so a step can be changed without fear of breaking its neighbor, and the Action itself can be embedded in another without knowing its internals.

→ [Action and Pipeline](packages/aoa-action-machine/README.md#5-core-actions-and-pipeline)

---

### Sagas and Compensations

**Rollback you cannot forget.** Next to every step that changes the outside world, you declare how to undo it. A failure occurs — the machine rolls back the completed steps in reverse order automatically. No more manual `try/finally` blocks where you track what already ran.

→ [Sagas and Compensations](packages/aoa-action-machine/README.md#53-saga-rollback-without-hidden-magic)

---

### Explicit Error Handling

**Errors are part of the contract, not a surprise in production.** Right inside the operation you can see which error is caught and what happens next: a fallback result, a business response, or re-raise. The machine validates handler order at startup — a broad `except` physically cannot swallow what a narrower one should have caught.

→ [Explicit Error Handling](packages/aoa-action-machine/README.md#54-explicit-errors-on_error)

---

### Dependencies, Connections, Context

**What an operation touches is visible in the first lines.** Resources, child actions, database connections, required context fields — all declared in the class header. No singletons from nowhere, no thread-locals buried in a method body. And since dependencies are declared, the machine builds a graph from them — and checks for cycles before the first request.

→ [Dependencies, connections, context](packages/aoa-action-machine/README.md#55-depends-all-dependencies-visible-in-the-header)

---

### Cache, Logs, Plugins

**Infrastructure lives outside the business logic, not inside it.** Cache is declared as a policy, logs go through named channels, plugins observe steps without participating in execution — a plugin error does not bring down the request. The same event stream can be assembled into a full execution tree with `state` at every step and handed to an LLM to explain exactly what happened in a specific call.

→ [Cache, logs, plugins](packages/aoa-action-machine/README.md#58-logs-that-do-not-clutter-business-code)

---

### OCEL: Process Mining Out of the Box

**See how orders actually flow through the system — without separate instrumentation.** The same event stream that provides observability is exported to OCEL — the open process mining standard. Open it in pm4py or ProM and build a map of the real process: where it stalls, where it deviates from the intended flow. The data is already there — no manual collection needed.

→ [OCEL](packages/aoa-action-machine/README.md#511-ocel-process-mining-out-of-the-box)

---

### Domain Modeling

**The domain model is not tied to the database.** Order, user, payment — described as business objects with fields, relations, and lifecycle. Where the data comes from is decided by the resource: PostgreSQL, ClickHouse, HTTP API, or a fixture in a test. Change the storage — the model doesn't move, and consumers never know what's underneath.

→ [Domain Modeling](packages/aoa-action-machine/README.md#6-extended-domain-modeling)

---

### Testing: Same Machine, Different Reality

**In tests, code is not mocked — only data is.** The test runs the same Action that goes to production: real roles, checkers, step order, plugins. What changes is not the logic but the reality around it — resources and external systems return test data. So the test validates exactly the code that will run in production.

→ [Testing](packages/aoa-action-machine/README.md#512-testing-the-same-machine-a-different-reality)

---

### Adapters: One Action, Many Transports

**Write the operation once — expose it over HTTP, MCP, and CLI.** No logic duplication, no DTO layers. `FastApiAdapter` turns an Action into a REST endpoint with a ready-made OpenAPI spec, `McpAdapter` turns it into an AI-agent tool with a strict schema. The same operation is also callable directly from code. One contract — as many entry points as needed.

→ [Adapters](packages/aoa-action-machine/README.md#513-adapters-http-and-mcp-from-one-source)

---

### Maxitor: The System Visible in a Browser

**Architecture that never goes stale, because it is drawn from code.** The full system graph, entity ERD, use cases by role, lifecycle state machines — Maxitor assembles them from the same declarations the machine executes. No Miro and Confluence drifting from reality the day after you draw them.

→ [aoa-maxitor: full documentation](packages/aoa-maxitor/README.md)

---

## Philosophy

### A Grammar That Enforces

Predictable code is not a matter of team discipline. Agreements hold at the start but erode over time — under deadline pressure, during team changes, in the rush of the moment. What you need is a structure that physically prevents business operations from being written differently every time.

AOA is a grammar. The framework does not recommend — it enforces a single set of rules for every operation. No `@check_roles` — the code will not start. No summary aspect — the machine refuses at startup. A dependency cycle, a broken `@on_error` handler order, a mismatched checker contract — these are all initialization errors, not surprises on review or in production.

All operations share the same shape: one `Params` input, one `Result`, aspects top to bottom. When you open someone else's `Action` — or your own six months later — you do not reconstruct intent from five files. You just read top to bottom.

Complex processes are composed from simple ones: through `deps.run_action()` one `Action` calls another. No base classes, no method overrides. Each operation is small, self-contained, and testable in isolation.

One more rule that annoys at first: class names must end with suffixes — `CreateOrderAction`, `InventoryResource`, `OrderEntity`, `PaymentGatewayPlugin`. It feels like bureaucracy at first. Then the suffixes become visual anchors: `...Resource` means an external system adapter; `...Action` means a business operation. Context is read before the file is even opened.

→ [All intents and invariants](docs/intents-and-invariants.md)

---

### Observability That Stays Out of the Logic

Logs, metrics, tracing, audit, process mining — every project solves this from scratch. And almost always the same way: observability grows into the business code. Methods accumulate `logger.info` calls, timing measurements, metric pushes, audit writes. Eventually you can no longer see where the operation ends and the wrapper around it begins.

AOA starts from the premise that **the observer must not be a participant**. Business logic does not know it is being observed. Plugins attach from the outside and receive events at every step — before and after each aspect, on error, on compensation — with a snapshot of `state` at each point. Full execution context, zero influence on execution: a plugin cannot change the result, and its own error does not bring down the request.

From this separation grows almost everything in the guide: structured logs, OCEL, execution trees for LLMs. One event stream — many ways to look at the system, and none of them mixed into its logic.

---

### AI-First: Readable by Humans and Language Models Alike

AOA does not "add AI features" — it turns out to be convenient for models for the same reason it is convenient for humans: intent is declared explicitly and is machine-readable.

Three things follow from this. Every `Action` is already described by a strict schema — `Params`, `Result`, roles, metadata — so `McpAdapter` delivers it to an AI agent as a tool with a clear contract, not a random function. Any call unfolds into an execution tree with `state` at each step — pass it to a model and it can explain exactly what happened. And when an agent writes code, the grammar holds it to the same rules as a human: no roles — it won't start; broken contract — error at startup, not a silent bug in production.

The stricter the structure, the less room for hallucinations — and the more reliably both humans and models work alongside it.

---

### Intent-Oriented Programming

Why does code written a year ago turn into something nobody dares touch? Not because it was written poorly or the team was weak. Because **intent was lost**. A year later nobody remembers the details. Two years later nobody dares change it, because it is unclear what will break in the neighboring layer. Knowledge lives in comments, Jira, Confluence, in the head of the author who has since left — but the code itself does not hold it.

AOA's answer is simple: **intent must live in the code**. When you write an Action, you declare the contract first: `@check_roles`, `@depends`, `@compensate`, `@on_error`, the order of aspects. That is the design of the operation. The implementation fills the form rather than inventing it on the fly.

At first this breaks a habit: the urge is to write code immediately. But this is exactly where the shift to **intent-first** happens: first you articulate what should happen, who has the right, which steps are mandatory, and what to do on failure. Then you write the step bodies.

The result is **Intent-Oriented Programming**: code does not hide intent inside a mechanism — it starts with intent. Three properties follow:

- **Intent is executed.** Declare a role — it will be checked. Declare a compensation — it will be called. Declare a step contract — the machine validates it after every execution.
- **Intent documents itself.** The system describes itself automatically: OpenAPI, MCP schema, graph, ERD, use cases, OCEL — all from the same declarations, without manual upkeep.
- **Intent is protected by fail-fast.** Wrong role — rejected at call time. No summary aspect — rejected at startup. Dependency cycle — rejected at startup. A contract violation never passes silently — it surfaces immediately, rather than becoming a quiet bug in production.

---

## License

[MIT](LICENSE)
