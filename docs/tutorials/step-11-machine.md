<!-- translated-from: step-11-machine_draft.md @ 2026-06-17T17:02:35Z · sha256:9de20cdc660a -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Step 11 — ActionProductMachine

<table width="100%"><tr>
  <td align="left"><a href="step-10-logs.md">← Step 10 — Logs as business events</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-12-authentication.md">Step 12 — Authentication →</a></td>
</tr></table>

- [A single entry point](#a-single-entry-point)
- [The lifecycle of a call](#the-lifecycle-of-a-call)
- [Six tools](#six-tools)
- [Assembling the machine](#assembling-the-machine)
- [Dynamism and extensibility](#dynamism-and-extensibility)
- [What the machine does not do](#what-the-machine-does-not-do)
- [Invariants](#invariants)
- [Review questions](#review-questions)

---

We have gone through the whole core: the operation, state, access, sagas, dependencies, context, cache, plugins, logs. All of it is declarations on an `Action`. But someone has to read those declarations and execute them literally: check access, peek into the cache, run the pipeline, unwind the saga on failure and call the handler, dispatch events to plugins, route logs. This is **`ActionProductMachine`** — the heart of the service layer.

The split is simple: **the operation describes what to do; the machine guarantees how it is executed.** The machine contains not a line of business logic — only uniform mechanics around every operation. This chapter opens the "Service" part and looks at the machine as a whole: its lifecycle and the tools with which it orchestrates an operation.

---

## A single entry point

An operation is launched in a single way:

```python
result = await machine.run(context, action, params, connections)
```

There are no other entrances. You cannot call an aspect directly, you cannot skip the role check, you cannot enter the middle of the pipeline. This is an architectural guarantee, not a convention — and it is exactly what turns the execution graph from a web of calls into one traceable path. `context` is the call environment (built by the transport, see below); `connections` are the open resources by key ([@connection](step-06-dependencies.md)).

## The lifecycle of a call

`run` leads an operation along a fixed path — strictly in this order:

1. **Access check.** [`@check_roles`](step-03-authorization-and-roles.md) is matched against `context.user.roles` — before anything else. No decorator — `MissingCheckRolesError`; the role does not fit — `AuthorizationError`. Important: access is checked **before the cache**, so a cached result will not reach someone the operation forbids.
2. **Connection validation.** The declared `@connection` keys are checked against the supplied ones.
3. **`global_start`** — [plugins](step-09-plugins.md) receive the start event.
4. **Cache.** If a [cache coordinator](step-08-cache.md) is wired: an entry is looked up by `cache_key`; a hit returns the ready result, **bypassing the pipeline**.
5. **Pipeline.** On a miss the regular [aspects](step-01-action-and-pipeline.md) run — each with `before`/`after` events and [checker](step-02-state-as-x-ray.md) validation — then the `summary`.
6. **Errors.** On an aspect failure: the [saga unwind](step-04-saga-and-compensations.md) (if there is a stack), then [`@on_error`](step-05-error-handling.md) with the original error.
7. **Cache write.** After a clean `summary` — `on_cache_write` decides whether to store.
8. **`global_finish`** — plugins receive the result and the full time.

Along the whole path [`box`](step-10-logs.md) emits business events that fan out to the loggers. Nested calls (`box.run`) take the same path with their own nesting level.

## Six tools

The machine is assembled from tools — each responsible for one cross-cutting concern, and each replaceable. Six of them are the main ones:

1. **Execution** — the `run` itself: reads the declarations and leads the operation along the pipeline.
2. **The system graph** (`graph_coordinator`) — built **at application startup**: all operations, their dependencies and calls. Here too the machine checks the grammar of intents — cycles, contracts, incomplete declarations. The **fail-fast** principle: an inconsistent graph does not let the service start.
3. **Access** (`role_checker`) — the role check on every call.
4. **Cache** (`cache_coordinator`) — an optional layer over the pipeline; off by default.
5. **Observation** (`plugins` / `plugin_coordinator`) — dispatching lifecycle events to plugins.
6. **Business events** (`log_coordinator` / loggers) — routing `box` by channels and levels.

Alongside them work the executive parts of the same path: the connection validator, the saga coordinator, and the error handler — they are built into execution and usually stay standard. But **authentication** does not belong to the machine: `Context` is built by the transport at its boundary (the adapter), and the machine receives it ready in `run(context, ...)`. About this — the next chapters of the "Service" part.

## Assembling the machine

The tools are passed at machine creation — all optional, each with a reasonable default:

```python
machine = ActionProductMachine(
    plugins=[OpenTelemetryPlugin()],                               # observation
    log_coordinator=LogCoordinator(loggers=[ConsoleLogger()]),     # business events
    cache_coordinator=CacheCoordinator(),                          # cache (otherwise none)
)
```

What you do not pass the machine supplies itself: the system graph is built by default, the role check and the connection validator are taken standard. The single notable exception is the cache: without a `cache_coordinator` there is no cache at all, and the operation's hooks stay silent. In the simplest case a bare `ActionProductMachine()` is enough — exactly how the examples from the [first chapter](step-01-action-and-pipeline.md) were launched.

## Dynamism and extensibility

The tools are wired, unwired, and replaced depending on the environment — a separate assembly for production, development, and tests, up to reconfiguration on the fly. And they are all extensible: AOA provides a base set, but for a particular project you write a [custom cache coordinator](../index.md#how-to-write-your-own-extension) (for example, Redis), a [custom logger](../index.md#how-to-write-your-own-extension) (Kafka, Slack, PagerDuty), or a [custom plugin](../index.md#how-to-write-your-own-extension). The machine is not hardwired to a single implementation — it orchestrates interfaces.

## What the machine does not do

The machine contains no business logic and does not know what a particular operation does. It does not manage transactions automatically — `commit`/`rollback` remain with the operation and its [resources](../index.md#iv-data-model). It does not change `params`, `state`, or `result` and does not influence what `summary` returns. Its single task is a uniform, deterministic, and safe execution path. Everything else is the responsibility of operations and resources.

At the same time the machine holds the **metamodel** of every operation, assembled when the graph was built: roles, dependencies, ordered steps, contracts, connections. This data cannot diverge from the code — without it the operation will not run — and on it stand the system graph, [Maxitor](../index.md#vi-maxitor), and the access matrix (see [The system from different altitudes](../explanation/system-altitudes.md)).

## Invariants

- **A single entrance.** Only `machine.run(...)`; you cannot enter the middle of the pipeline.
- **A fixed order.** Access → connections → cache → pipeline → (sagas → `@on_error`) → cache write; roles are checked before the cache.
- **The graph at startup.** An inconsistent graph (cycles, incomplete declarations) fails the launch — fail fast.
- **Cache by consent.** Without a `cache_coordinator` there is no cache; the other tools have defaults.
- **No business logic.** The machine does not change data, does not decide for `summary`, does not manage transactions.
- **The metamodel is correct by construction.** The operation's specification is assembled by the machine and cannot diverge from the code.

The full list is in [Intents and invariants](../reference/intents-and-invariants.md); the terms are in the [Glossary](../reference/glossary.md). Why execution is separated from description is in the [Philosophy](../explanation/philosophy.md).

## Summary

`ActionProductMachine` is the single executor and the heart of the service layer: one entrance, a fixed path (access, cache, pipeline, sagas, errors, events), without a single line of business logic. Its tools — the graph, roles, cache, plugins, loggers — are wired and replaced per environment, while authentication stays at the transport and arrives as a ready `Context`. The operation describes the intent; the machine executes it the same way, predictably.

Next — **[Authentication](step-12-authentication.md)**: who builds `Context` at the transport boundary, and how, before the operation begins its work.

---

## Review questions

1. What does "the operation describes, the machine guarantees" mean? Which of the things listed in the core does the machine itself do?
2. Why is there only one entrance into an operation, and what does it buy?
3. In what order do the access check and the cache go — and why exactly so?
4. Name the six tools of the machine. Which one is off by default, and what happens without it?
5. Where is `Context` built, and why is it not the machine's job?
6. When is the system graph built and what does it check? How is this connected to fail fast?
7. What does the machine deliberately NOT do? To whom does transaction control belong?

> **Exercise.** Take any core example (for instance, [`01_cache.py`](../../examples/step_08_cache/01_cache.py)) and assemble a machine with two tools at once: `cache_coordinator=CacheCoordinator()` and `plugins=[...]` (any built-in plugin from the [plugins chapter](step-09-plugins.md)). Trace from the output that on a cache hit the pipeline does not run, but the plugin still receives the `global_finish` event.

---

<table width="100%"><tr>
  <td align="left"><a href="step-10-logs.md">← Step 10 — Logs as business events</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-12-authentication.md">Step 12 — Authentication →</a></td>
</tr></table>
