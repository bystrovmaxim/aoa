<!-- translated-from: index_draft.md @ 2026-06-23T04:11:09Z · sha256:f88184fa80e4 -->
<p align="center">
  <img src="assets/aoa-logo.png" alt="AOA" width="200">
</p>

# AOA Tutorial

---

AOA was conceived for one goal: that a program's intent stays visible — a year later, and through five sets of changed hands. But that goal breaks down into several big problems, and each part of the guide is best read as an answer to a specific one: how to describe an operation without drowning it in infrastructure; how to expose it outward without smearing the logic across the transport; how to describe the domain without binding to storage; how to test all of it and how to see the system as a whole. Below, each part is labeled with the exact problem it solves.

The chapters are arranged so each builds on the previous. Each comes with a folder of executable examples — not illustrations, but working code worth running and reworking. A chapter ends with a few questions that check your understanding of the model. Sections marked *(soon)* are still being written; the reference materials at the bottom are for coming back to as needed.

---

## How to read

The guide moves from a practical entry point to the complete project architecture. First — setup and a first run, then the architectural frame, then the core business logic. After that come the service layer, the data model, testing, and Maxitor as a map of the whole system.

---

## I Getting started

> **Practical entry:** installation, first run, repository structure, and minimal orientation to the project.

- **[Getting started](tutorials/step-00-get-started.md)** — installation, uv, first run, the repository map

---

## II Introduction

> **Architectural frame:** how AOA is structured, the philosophy it is based on, how it differs from other approaches, and how it affects the team.

- **[Questions AOA answers with code](explanation/questions-aoa-answers-with-code.md)** — twelve questions about the unique capabilities and short answers with a link to the proof
- **[The system from different altitudes](explanation/system-altitudes.md)** — five levels at which an AOA system reads: from the domain catalog to the body of a step
- **[AOA as a project skeleton](explanation/aoa-project-skeleton.md)** — AOA's three layers: service boundary, business operations, data and domain model; connection with clean and hexagonal architecture
- **[The philosophy of AOA](explanation/philosophy.md)** — why the architecture is built exactly this way: the principles underneath
- **[Comparison with other frameworks](explanation/comparison.md)** — AOA next to FastAPI, Django, Clean/DDD, CQRS, Temporal; when to apply it
- **Performance** *(soon)* — the orchestration layer as a conscious cost: where the overhead lives, what to measure, and when a hot path is not cast as an Action

---

## III Business logic

> **The big problem:** how to describe an operation so its intent is visible whole, while access, state, errors, rollbacks, and dependencies do not dissolve the business logic into infrastructure.

- **[Action and the pipeline](tutorials/step-01-action-and-pipeline.md)** — Action, aspects, params, result, box, state, inheritance
- **[State: the operation's x-ray](tutorials/step-02-state-as-x-ray.md)** — state contracts, checkers, observability through OpenTelemetry
- **[Authorization and roles](tutorials/step-03-authorization-and-roles.md)** — @check_roles, role classes and inheritance; conditional authorization and GuestRole — planned
- **[Saga and compensations](tutorials/step-04-saga-and-compensations.md)** — rolling back steps on failure, distributed transactions without try/finally
- **[Explicit error handling](tutorials/step-05-error-handling.md)** — @on_error: business logic, rollback, and errors as three independent layers
- **[Dependencies](tutorials/step-06-dependencies.md)** — @depends and @connection: an explicit contract on everything external, right in the header
- **[Context and environment](tutorials/step-07-context.md)** — `@context_requires` declares a slice of the call environment; `@env` connects lazy config and feature-flag providers right on the Context class with optional TTL; no thread-locals or globals
- **[Cache](tutorials/step-08-cache.md)** — cache_key and on_cache_write: the operation is responsible for meaning, the coordinator for storage
- **[Plugins](tutorials/step-09-plugins.md)** — an observer, not a participant: OpenTelemetry and OCEL out of the box
- **[Logs as business events](tutorials/step-10-logs.md)** — box.info with channels and levels instead of logger.info in the business code

---

## IV Service

> **The big problem:** how to release the same operation into different transports (HTTP, MCP) without smearing the logic across the delivery layer.

- **[ActionProductMachine](tutorials/step-11-machine.md)** — the heart of the service layer: a single entry, access, cache, pipeline, sagas, events
- **[Authentication](tutorials/step-12-authentication.md)** — auth_coordinator builds Context from a request of any transport, before the adapter
- **[FastAPI](tutorials/step-13-fastapi.md)** — REST and OpenAPI from one Action without mixing transport into the business logic
- **[MCP](tutorials/step-14-mcp.md)** — the same Action as a tool for an AI agent without duplicating logic
- **[Result by JSON schema](tutorials/step-15-schema-results.md)** — `JsonSchemaValue` and entity projections: complex objects and partial slices with schema validation
- **[Accepting complex data from a request](tutorials/step-16-complex-input.md)** — collections, nested objects, and JSON by schema in the input `Params`
- **[Connections at the request boundary](tutorials/step-17-connections.md)** — two modes of supplying `@connection` by the adapter: a shared resource or a fresh one per request
- **[Schema converters](tutorials/step-18-converters.md)** — `params_mapper`/`response_mapper` and API versions: the external schema changes, the `Action` stays one

---

## V Data model

> **The big problem:** how to describe the domain — entities, relations, lifecycle — without binding to tables and an ORM.

- **[Resource](tutorials/step-19-resource.md)** — the boundary with the external world: PostgreSQL, APIs, queues, test fixtures; pure transport separated from logic
- **[Entity](tutorials/step-20-entity.md)** — a domain object without ties to storage: one class, any data source
- **[Relations](tutorials/step-21-relations.md)** — Association, Aggregation, Composition with consistency checked at startup
- **[Lifecycle](tutorials/step-22-lifecycle.md)** — a state graph with transition validation: an inconsistent graph does not let the system start

---

## VI Testing

> **The big problem:** how to test scenarios whole, substituting the world around an operation rather than its internals — so the tests do not break on every refactoring.

- **[TestBench: the same Action, a different reality](tutorials/step-23-testbench.md)** — run depth: the whole operation, an aspect, summary, compensator, `@on_error`
- **[Substituting the environment](tutorials/step-24-substitution.md)** — `with_mocks` for dependencies and resources, `@connection` in a test, Rollup on the production schema
- **[Context](tutorials/step-25-context.md)** — `with_user`/`with_request`/`with_runtime`: assembling `Context` for `@check_roles` and `@context_requires`

---

## VII Maxitor

> **The big problem:** how to see the whole system — operations, dependencies, entities — without a single line of manual documentation.

- **[Maxitor: a system you can see](tutorials/step-26-maxitor.md)** — graph of operations, ERD, use case, and lifecycle: four projections from one code, without manual documentation

---

## Additional materials

The materials below are not a continuation of the linear I–VII route. They are a reference, practical solutions, extensions, and research notes to return to as needed.

### How-to guides

> **The task:** make a concrete design decision or migrate existing code.

- **[Action, aspect, or resource — what to choose](how-to/choosing-action-aspect-resource.md)** — an algorithm for choosing the abstraction, with examples
- **[Migrating legacy to AOA](how-to/migrating-legacy.md)** — the strangler pattern: monster → port → adapter → aspects, step by step

### Reference materials

- **[Glossary](reference/glossary.md)** — the key AOA terms, grouped by layer
- **[Questions and answers](reference/faq.md)** — positioning, the execution model, trade-offs; for those evaluating AOA
- **[Intents and invariants](reference/intents-and-invariants.md)** — what the system requires of you and what it guarantees in return

### Ready extensions

What is already in the box. Some is available right away, some installs as a separate package.

- **[OpenTelemetry](extensions/opentelemetry.md)** — plugin: traces and the `state` x-ray out of the box; `pip install aoa-otel`
- **[OCEL 2.0](extensions/ocel.md)** — plugin: an object-centric event log for process mining; `pip install aoa-ocel`
- **[ConsoleLogger](extensions/console-logger.md)** — logger: business events to the console, color by level; out of the box
- **[FastAPI](extensions/fastapi.md)** — adapter: HTTP/REST and OpenAPI from an Action; `pip install aoa-fastapi-adapter`
- **[MCP](extensions/mcp.md)** — adapter: an operation as a tool for an AI agent; `pip install aoa-mcp-adapter`
- **[LangGraph](extensions/langgraph.md)** — adapter: AOA Actions as nodes in a LangGraph agent graph; `pip install aoa-langgraph`
- **[PostgreSQL](extensions/postgresql.md)** — resource: connections and transactions through asyncpg; `pip install "aoa-action-machine[postgres]"`

### How to write your own extension

The framework's extension points. The principle everywhere is the same: you implement an interface, and the machine embeds your implementation into the unified mechanics.

- **[Your own transport adapter](how-to/authoring-adapter.md)** — gRPC, Kafka, and other protocols over the same Actions
- **[Your own authentication coordinator](how-to/authoring-auth-coordinator.md)** — JWT, OAuth2, API key: building `Context` from a request
- **[Your own plugin](how-to/authoring-plugin.md)** — a lifecycle observer over the machine's events
- **[Your own logger](how-to/authoring-logger.md)** — delivery of `box` business events to Kafka, Slack, PagerDuty
- **[Your own cache adapter](how-to/authoring-cache-adapter.md)** — Redis and other stores behind `cache_key` / `on_cache_write`
- **[Your own resource](how-to/authoring-resource.md)** — a new data source behind the `BaseResource` interface
- **[Extending Context](how-to/authoring-context-extension.md)** — your own call-environment fields and access to them through `@context_requires`
- **[Your own intent](how-to/authoring-intent.md)** — your own rule as a graph node: decorator → node → inspector → registration

### Open research

Topics opened by viewing the system as a formal object. This is not a set of ready features but a program: questions that ordinary code cannot even pose — here they can, and some are already computable from the graph. The section will be expanded.

- **[The formal model: open questions](reference/formal-model.md)** — the system as a formal object: what becomes a correctly posed question — from load calculation to proving invariants
- **[What the system knows about itself](research/self-knowledge.md)** — self-diagnosis: gaps (no compensator, a dead role), risks (a load-bearing fragile node), and hints, computable from the graph
- **[IOP: intents, invariants, and architectural molecules](research/iop-foundations.md)** — the base IOP model in AOA: an intent as a verifiable invariant, architecture atoms, and `Action` / `Resource` molecules
- **[Intent-Oriented AI Development](research/intent-oriented-ai-development.md)** — AOA as a verifiable grammar for AI agents: a capability catalog, a correct stop instead of hallucination, and a ReAct development cycle
- **[Environment Context Port](research/environment-context-port.md)** — the environment as an explicit `Context` port: lazy providers, cache scope, `@context_requires`, TestBench substitution, and protection against a new hidden global
