<!-- translated-from: faq_draft.md @ 2026-06-17T15:33:42Z · sha256:1514772f93da -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Questions and answers

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>

---

Here are collected the questions that most often arise for architects and tech leads on first contact with AOA. The answers are grouped by topic, and this is not a retelling of the chapters but an attempt to explain **why** the model is built this way. If you have not yet opened [The system from different altitudes](../explanation/system-altitudes.md) — start with it, much here will become more obvious.

---

## Positioning and boundaries

### Is this a library, a framework, or an architectural style?

AOA is an architectural style, and `aoa-action-machine` is its executable implementation in Python. You can take just the Action Machine core, you can add the FastAPI/MCP adapters, the OCEL plugin, the Maxitor visualizer. What matters is not the packaging but the principle: a business operation is described as an executable contract, not as the sum of agreements around ordinary code.

### When is AOA not needed?

If the code is local, short, and has no external contract — an ordinary function is more honest. AOA starts to pay off when an operation acquires roles, steps, dependencies, rollbacks, audit, cache, transport adapters, a domain model, scenario tests — and the need to explain its behavior to another person or agent. Below that threshold the price of explicitness does not pay back, and there is no point imposing it on yourself.

### How to adopt it in an existing project?

Do not rewrite everything. Take one operation that already hurts: many roles, side effects, rollbacks, an external API, heavy testing. Cast it as an Action, wire up one adapter or one scenario test. If the value did not show on one operation — it is early to scale; if it did show — the next one comes easier, and the decision is made on facts, not faith.

### What is the main trade-off, and won't it be slow?

AOA takes away the freedom of the implicit: you cannot quietly grab the context, silently pull in a dependency, hide a rollback in a random `except`, or keep state in an Action. In return the system becomes predictable, verifiable, and observable. The price is an orchestration layer — checks, events, plugins. For most business operations the cost of the DB, the network, and external services is an order of magnitude higher than this layer, so the price is unnoticeable. Where micro-performance matters, a hot low-level path simply is not cast as an Action: AOA is for operations, not for hot loops.

---

## Why so many declarations

### So many decorators — isn't that noise?

Noise is what does not affect behavior. AOA's decorators affect behavior: `@check_roles` checks access, `@result_*` validates `state`, `@compensate` launches a rollback, `@depends` constrains the dependency factory, `@context_requires` hands out a context slice. These are not comments about intent but intent in executable form. What usually lives in the author's head and surfaces at review here lives in the code and is checked by the machine.

### Why can't we "just agree to write tidy services"?

Agreements work while the team is small and everyone remembers the context. AOA moves the agreement into the grammar of the code. You cannot forget to declare the context and then secretly read it; you cannot get an undeclared dependency; you cannot hide a mandatory rollback in a verbal agreement. The system checks what used to rest on discipline — and discipline scales worse than any tool and is the first to fade as the team grows.

### Where is the boundary between business code and the machine?

Business code lives inside aspects: validation, calculation, a domain service call, assembling the result. The machine is responsible for the uniform mechanics around it: the order of steps, `state`, the checks, roles, dependencies, context, compensations, plugins, cache, events. The boundary is needed so the scenario does not turn into a mix of logic and infrastructure — and so the mechanics can be changed without touching the meaning, and vice versa.

---

## The execution model

### Why are a single entry point and a single result so important?

An operation can be understood if it is clear where it begins and where it ends. In AOA the launch goes through the machine, and the result is returned as a `Result` or through an explicit `@on_error`. This turns the execution graph from a web of calls and side exits into a path you can trace, test, and show on a diagram.

### Why does an Action have no state of its own, and how then does `state` differ from object fields?

An Action must not remember a past call — everything that affects execution comes from the outside: `Params`, `Context`, the pipeline `state`, connections, `@depends`, the machine's plugins. So a test does not "prepare an object" but assembles the input and the environment, and the class of floating bugs where yesterday's call affects today's disappears. `state`, unlike object fields, lives only inside one run: aspects create it, the machine checks it with checkers and passes it on, but after completion it does not become the Action's memory. Intermediate data is observable but does not leak into later calls.

### Why are dependencies and context declared in advance?

A hidden dependency is a hidden cause of changing behavior. `@depends` makes external Actions and resources part of the operation's header: the reader, reviewer, test, and graph see them, and an undeclared dependency `box.resolve(...)` simply will not yield. The same logic for the context: today an aspect reads `user_id`, tomorrow `trace_id`, the day after `request_path`, and nowhere is it visible — `@context_requires` makes the consumption explicit, and the context slice will not let you read the extra.

### Errors: can you no longer raise exceptions?

You can. But if the error is part of a business scenario, it is better to declare it through `@on_error`. Then the order of handlers, the error types, and the fallback path become a visible contract. Handlers are checked top to bottom in declaration order, so there is one rule — the specific before the general: a general `@on_error(Exception)` placed first will shadow a more specific one (the machine does not reorder). No match by type — the original error goes out unchanged.

---

## Data, testing, and audience

### Is an Entity an ORM?

No. An Entity knows nothing of tables, sessions, query builders, or a concrete DB. It is a domain model: fields, relations, partial-loading semantics, lifecycle. Where to take the data from and how to assemble the entity is decided by the resource — PostgreSQL, ClickHouse, S3, an HTTP API, a fixture. So one Action works with one model while the resource implementations change under it.

### Why partial loading instead of separate DTOs per request?

Separate DTOs diverge quickly: the order list returns one shape, the card another, the report a third. AOA lets you return one domain type with different load levels. If the code accidentally touches an unloaded field, it gets a `FieldNotLoadedError` or `RelationNotLoadedError` — not a silent `None` and not a hidden lazy query to the database.

### How to test without huge integration tests?

`TestBench` runs the same Action through the same machines but lets you assemble the needed reality: the user and request context, mocks for `@depends`, connections. You can test the whole Action, one regular aspect, the summary, or a compensator separately — the tests scale by risk. For transactional resources there is rollup: a real scenario is run against the production schema (real INSERT/UPDATE, a real pipeline), but on `commit()` a rollback is done. This is neither a mock nor a dry run but a check against the real schema without saving the changes.

### What does it give a reviewer and an AI agent?

A reviewer sees not only the Python body but the change in intent: roles, dependencies, context, the pipeline, compensators, error handlers, the cache policy. The question shifts from "does the code look fine" to "is the operation's contract declared correctly". An agent gets the system's vocabulary — the Action catalog, descriptions, Pydantic schemas, MCP tools, the dependency graph, the pipeline, and documentation from the code — and does not have to guess from random functions what can be called and with which parameters.

---

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>
