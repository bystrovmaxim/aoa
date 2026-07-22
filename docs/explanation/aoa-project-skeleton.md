<!-- translated-from: aoa-project-skeleton_draft.md @ 2026-07-10T14:55:05Z (filesystem mtime; draft is gitignored, no git history) · sha256:7f4ffd5415cb -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# AOA as a project skeleton

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>

---

AOA is easy to start understanding through `Action`: a single business operation with `Params`, `Result`, aspects, and `state`. That's the right entry point into the model, but an incomplete picture. Stop there, and AOA looks like a way to dress up functions. In reality, `Action` is the center of the business layer around which the skeleton of the whole project is assembled.

In a typical architecture a project often grows from external shapes: first HTTP endpoints, then services behind them, then repositories, then DTOs, then tests and observability. The business scenario ends up smeared across transport, DI, ORM, middleware, logs, and test mocks. To understand what the system actually does, you have to assemble the meaning from several layers.

AOA proposes the reverse order: design the system starting from operations.

First we answer the question: **what actions can the product perform?** Create an order, charge a payment, refund money, approve a request, send a notification, recalculate a limit. Each such action becomes an `Action`: a unit of meaning that can be called, checked, exposed, observed, tested, and shown on a graph.

The rest of the parts are built up around these operations:

- transport is plugged in through adapters;
- external dependencies are declared as ports;
- data sources hide behind `Resource`;
- domain objects are described as `Entity`;
- observability is wired in through plugins;
- tests assemble a different environment around the same operation;
- Maxitor builds a map of the system from the same declarations.

This is how AOA becomes a practical form of clean and hexagonal architecture: the outside plugs into the core but doesn't mix with it; business scenarios sit at the center; the project's boundaries become not just a folder-naming convention but executable, checkable declarations.

---

## The central axis: product operations

In AOA a project doesn't start with tables or API routes. It starts with a catalog of operations.

```text
StoreDomain
  CreateOrderAction
  CancelOrderAction
  GetOrderAction

BillingDomain
  ChargePaymentAction
  RefundPaymentAction

MessagingDomain
  SendReceiptAction
```

This isn't just a list of classes. It's an inventory of the system's capabilities. If an operation became an `Action`, it has:

- an explicit input, `Params`;
- an explicit output, `Result`;
- declared access;
- a known pipeline of steps;
- contracts for the intermediate `state`;
- lifecycle events;
- a place on the system graph.

The operation stops being a method hidden inside a service. It becomes an object of architecture.

That's exactly why `Action` is not "just another wrapper around a function." It's the point where business meaning becomes machine-readable.

More: [Action and the pipeline](../tutorials/step-01-action-and-pipeline.md).

---

## Layer 1. The service boundary

The service layer is responsible for how the outside world enters the system. HTTP, MCP, CLI, GraphQL, a queue, a cron job — these are different delivery shapes for a request. They shouldn't change the business scenario.

In AOA this boundary is held by adapters:

```text
HTTP request ── FastApiAdapter ─┐
MCP call     ── McpAdapter     ├── ActionProductMachine ── Action
CLI command  ── CLIAdapter     ┘
```

The adapter does the external work:

- accepts the request from a specific transport;
- builds the `Context`;
- validates or maps the input into the internal `Params`;
- runs the `Action` through the machine;
- returns the `Result` in the transport's shape.

Meanwhile the `Action` doesn't know where the call came from. The same `CreateOrderAction` can be an HTTP endpoint, an MCP tool for an AI agent, and a CLI command. If the transport changes, the adapter changes. The business scenario stays the same.

This is the hexagonal boundary in applied form: transport plugs in from outside but doesn't grow into the operation.

More: [Service](../index.md#iv-service).

---

## Layer 2. Business operations

The business layer describes the system's scenarios. Its center is `Action`.

`Action` has two outer boundaries:

- `Params` — what's needed on input;
- `Result` — what the operation promises to return.

Between them sits the pipeline:

```text
Params
  ↓
regular_aspect → checked state
  ↓
regular_aspect → checked state
  ↓
summary_aspect → Result
```

Every intermediate step declares which `state` it produces. The machine checks it right after the step. If a field is missing, has the wrong type, or violates a constraint, the next step doesn't run.

This same layer holds:

- `@check_roles` — who may run the operation;
- `@depends` — which services the operation needs;
- `@connection` — which open resources are needed during the call;
- `@context_requires` — which slice of the environment it's allowed to read;
- `@compensate` — how to roll back a step's effect;
- `@on_error` — how to handle an error after rollback;
- `cache_key` / `on_cache_write` — how the operation participates in caching;
- `box.info(...)` — which business events the operation considers significant.

This matters: the business layer in AOA doesn't reduce to "methods with logic." It holds the operation's intent, its boundaries, its obligations to the next steps, its recovery after failure, and its observability.

More: [Business logic](../index.md#iii-business-logic).

---

## Layer 3. Data and the domain model

Clean architecture requires separating business decisions from storage details. AOA does this with two distinct concepts: `Resource` and `Entity`.

`Resource` is the boundary with an external source or executor. It could be PostgreSQL, MongoDB, ClickHouse, an HTTP API, a queue, file storage, an SDK client, or a test fixture. A resource knows how to talk to the outside world but doesn't decide the business scenario.

```text
Action ──depends/connection──> Resource ──> PostgreSQL / API / Queue / Fixture
```

`Entity` is a domain object. It describes the fields, relations, and lifecycle of the subject area without being tied to a specific table or ORM mapping.

This distinction is fundamental. An ORM model is often a reflection of the database schema. An `Entity` in AOA reflects the domain. The same `OrderEntity` can be assembled from PostgreSQL, MongoDB, an external API, or a test object. The business operation works with the order as a domain object, not as its storage form.

Relations (`Association`, `Aggregation`, `Composition`) and `Lifecycle` add another level: the subject area becomes not a bag of random classes but a checkable structure. An inconsistent relation or a broken state graph is caught at build time, not in production.

More: [Data model](../index.md#v-data-model).

---

## The cross-cutting layer: the machine, events, and plugins

`ActionProductMachine` is not just a helper for calling an `Action`. It's the point where the service boundary, business operation, access, cache, dependencies, sagas, error handling, and lifecycle events all meet.

The machine sees execution as a structure:

```text
global start
  before aspect
  after aspect + checked state
  before aspect
  after aspect + checked state
  rollback / on_error / finish
global finish
```

Plugins subscribe to these events. That's why OpenTelemetry, OCEL, audit, metrics, security review, or project monitoring get not random `logger.info` calls but model events: which `Action` ran, which aspect finished, which `state` was checked, where a rollback began.

Observability in AOA isn't bolted onto code after the fact. It follows from the operation already having a formal structure.

More: [Plugins](../tutorials/step-09-plugins.md), [OpenTelemetry](../extensions/opentelemetry.md), [OCEL 2.0](../extensions/ocel.md).

---

## Testing: the same scenario, a different environment

If a business operation receives everything external only through declared ports, a test doesn't need to crack open its internals.

Instead of patching/mocking internal functions, a test assembles a different environment around the same `Action`:

- a different user;
- a different `Context`;
- a different resource;
- a different response from an external service;
- a different transaction policy;
- a different rollup mode.

The operation doesn't know it's "in a test." It goes through the same machine: roles, pipeline, checkers, compensations, `@on_error`. So the test checks the scenario as a whole, not the current shape of the implementation.

More: [Testing](../index.md#vi-testing).

---

## System visibility

Once operations, roles, dependencies, resources, entities, relations, and lifecycles are declared, the system can be read not only as a file tree. It can be built as a graph.

Maxitor shows several projections of the same code:

- the operation graph;
- an ERD;
- use cases;
- lifecycle diagrams.

This isn't hand-written documentation sitting next to the project. It's a map extracted from the same declarations the machine uses. So it doesn't just explain the system to a person — it also shows exactly what became machine-readable.

More: [Maxitor](../index.md#vii-maxitor).

---

## How to design an AOA system

The practical order is this:

1. **Name the domains.** What areas of responsibility exist in the product?
2. **Name the operations.** What can the system actually do?
3. **Describe each operation's input and output.** That's `Params` and `Result`.
4. **Break the operation into steps.** Every step should have a clear meaning and a `state` contract.
5. **Declare the external.** Everything that comes from outside must be a port: `@depends`, `@connection`, `@context_requires`.
6. **Describe failures.** Where are compensations needed, where is `@on_error` needed, where is it enough to just propagate the error?
7. **Wire up transports.** HTTP, MCP, CLI, or a queue become adapters around the same `Action`s.
8. **Describe the data.** Sources through `Resource`, domain objects through `Entity`.
9. **Add observability and tests.** Plugins see the execution, TestBench assembles test environments, Maxitor shows the graph.

This way the project grows not from controllers and tables but from the product's operations. The other layers appear as boundaries built around them.

---

## Summary

AOA is not a library for dressing up functions. It's a way to build an application around business operations.

`Action` holds the scenario. Adapters expose it to the outside. `Resource` connects it to the outside world. `Entity` describes the subject area. Plugins observe the execution. TestBench checks the scenario in a different environment. Maxitor shows the system as a graph.

That's exactly why AOA is close to clean and hexagonal architecture, but doesn't leave them only as conventions. The boundaries become part of the code that runs, is checked, and is observed.

Comparison with other approaches: [AOA next to FastAPI, Django, Clean/DDD, CQRS, and Temporal](comparison.md).

---

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>
