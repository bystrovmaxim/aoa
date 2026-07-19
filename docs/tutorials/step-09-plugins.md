<!-- translated-from: step-09-plugins_draft.md @ 2026-07-10T14:55:05Z (filesystem mtime; draft is gitignored, no git history) · sha256:b76d9b99884b -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Step 09 — Plugins

<table width="100%"><tr>
  <td align="left"><a href="step-08-cache.md">← Step 08 — Cache</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-10-logs.md">Step 10 — Logs as business events →</a></td>
</tr></table>

- [An observer, not a participant](#an-observer-not-a-participant)
- [Lifecycle events](#lifecycle-events)
- [Two built-in plugins](#two-built-in-plugins)
- [OCEL: an event log for process mining](#ocel-an-event-log-for-process-mining)
- [Several independent projections](#several-independent-projections)
- [A custom plugin is a separate topic](#a-custom-plugin-is-a-separate-topic)
- [Invariants](#invariants)
- [Review questions](#review-questions)

---

Observing a system splits into two tasks: seeing the **mechanics** of execution (which steps ran, how long they took, where it failed) and recording **business events** ("payment declined by the limit"). Usually both are dumped into one `logger.info()` — and then logging starts to dictate the architecture, and its failure turns the observer into a participant capable of bringing down a request.

AOA separates them. The mechanics are observed by **plugins** — that is this chapter. Business events are written by `box` — that is the [next one](../index.md#iii-business-logic). The key property of a plugin: it is an **observer, not a participant**. At every step boundary the machine emits an event, the plugin receives it — and cannot change `params`, `state`, or `result`.

[▶ Try in Colab](https://drive.google.com/file/d/1oepjkBpFi_DVU5v42WwuCHj5QaKO9ahR/view?usp=drive_link) · [Open in project](../../examples/step_09_plugins/01_ocel.py)

---

## An observer, not a participant

A plugin sees everything happening — `params`, `state`, `result`, `context`, timings — but the architecture gives it no mechanism to change any of it. From this follows safety: plugins can be added and removed without fear of breaking the logic, and a plugin's failure is isolated — it does not interrupt the operation. The business code meanwhile contains not a line of observation; observability in AOA is built into the architecture, not bolted on afterward.

## Lifecycle events

At every pipeline boundary the machine emits a **typed** event with the full surroundings (operation name, `params`, `state`, timings, nesting level). The event families cover the entire life of a call:

- the start and finish of the operation — `GlobalStartEvent` / `GlobalFinishEvent`;
- step boundaries — `Before/AfterRegularAspectEvent`, `Before/AfterSummaryAspectEvent`;
- errors and handling — `OnError*` and `UnhandledErrorEvent`;
- the saga — `SagaRollbackStartedEvent` / `SagaRollbackCompletedEvent`, `Before/AfterCompensateAspectEvent`, `CompensateFailedEvent`.

Events are classes with their own hierarchy, not strings: the subscription is typed, and each event has exactly the fields that belong to it (`GlobalStartEvent` does not carry `result`, while `GlobalFinishEvent` does). It is exactly these events we already saw in the [saga](step-04-saga-and-compensations.md) and in the [`state` x-ray](step-02-state-as-x-ray.md).

## Two built-in plugins

AOA ships two plugins out of the box, both observing the same event stream in different ways:

- **`OpenTelemetryPlugin`** — OpenTelemetry traces and logs: one trace per `machine.run()`, a span per aspect, and `state` snapshots in the `aoa.state.*` attributes. This is the **operation's x-ray**, covered in detail in the [State chapter](step-02-state-as-x-ray.md). Ships in a separate package: `pip install aoa-otel`.
- **`OcelPlugin`** — writes the course of execution in **OCEL 2.0** (Object-Centric Event Log) format for process mining. Ships in a separate package: `pip install aoa-ocel`.

They are wired the same way — as a list on the machine; the `Action` business code does not change:

```python
from aoa.ocel import OcelPlugin, OcelFrame, InMemoryOcelStoreResource, OCEL_FRAMES_KEY

machine = ActionProductMachine(plugins=[OcelPlugin(store=store, short_names=True)])
```

## OCEL: an event log for process mining

`OcelPlugin` turns operation runs into an object-centric event log. An aspect that wants to participate in process mining returns `OcelFrame` rows under the key `OCEL_FRAMES_KEY`; the plugin serializes them, and the store (`InMemoryOcelStoreResource`) writes JSON on `close()`:

```python
@regular_aspect("Validation")
@result_string("validated_id", required=True)
@result_instance(OCEL_FRAMES_KEY, list, required=False)
async def validate_aspect(self, params, state, box, connections):
    order = OrderEntity(id=params.order_id)
    return {
        "validated_id": params.order_id,
        OCEL_FRAMES_KEY: [OcelFrame(object=order, qualifier="Create order")],
    }
```

**Run:**

```bash
uv run python examples/step_09_plugins/01_ocel.py
```

**Output:**

```text
Sample 07 ocel

  Validate order: id=ord-001
  Validate order: id=ord-002
  Validate order: id=ord-003

written: ocel_log.json
events: 3
```

Three runs of `CreateOrderAction` produced three events in `ocel_log.json` — without a single line of logging code in the business logic. Such a log opens in process-mining tools (for example, OC-PM): from it you build process graphs, funnels, check conformance against models. These are metrics of the **business process**, not of the infrastructure.

## Several independent projections

A plugin can be narrowed to the needed events with the `watch_events` parameter — we saw this in the [`state` x-ray](step-02-state-as-x-ray.md), where one plugin wrote the full trace and a second only the `state` snapshots and the finish. On one machine you place several independent plugins, and each sees its own part of the stream:

```python
machine = ActionProductMachine(plugins=[plugin_traces, plugin_logs])
```

Observation is assembled from several projections, each configured separately, and not one of them interferes with execution.

## A custom plugin is a separate topic

Plugins are extensible: besides `OpenTelemetryPlugin` and `OcelPlugin` you can write your own — for metrics, role-based audit, anomaly detection, or building a semantic execution tree that is then handed to a language model. This is done by subscribing to typed events (`@on(SomeEvent)` in a `BasePlugin` subclass), but it is a **separate topic** — see the [«Custom plugin»](../index.md#how-to-write-your-own-extension) extension point. What matters here is that the built-in plugins are enough to get observability without writing anything.

## Invariants

- **Read-only.** A plugin sees `params`/`state`/`result`/`context` but cannot change them.
- **Failure isolation.** A plugin's error does not interrupt the operation (the observer does not bring down the participant).
- **Typed events.** The subscription is on event classes, not strings; each event has only its own fields.
- **The full context — to plugins.** Unlike aspects, plugins see the whole `Context` (observation, not a business decision).
- **Wired as a list.** Plugins are set on the machine (`plugins=[...]`); several projections coexist, `watch_events` narrows the stream.
- **Zero lines in the business code.** Observation is not present in the operation's code.

The full list is in [Intents and invariants](../reference/intents-and-invariants.md); the terms are in the [Glossary](../reference/glossary.md). Why observation is separated from execution is in the [Philosophy](../explanation/philosophy.md).

## Summary

Plugins are a safe observation layer: they receive typed events for the whole life of a call but change nothing, and their failure is isolated. `OpenTelemetryPlugin` (traces, logs, the `state` x-ray) is in the separate package `aoa-otel`; `OcelPlugin` (a log for process mining) is in the separate package `aoa-ocel`. Both are wired as a list without touching the business code and are narrowed via `watch_events`. A custom plugin is written by subscribing to events — but that is a separate topic; the built-in ones are enough for the system to observe itself without a single line of observation in the logic.

Next — **[Logs as business events](../index.md#iii-business-logic)**: the second half of observation — what the operation itself writes through `box`, as opposed to what plugins see.

---

## Review questions

1. Into which two tasks does observation split, and why does AOA separate them? What does each — a plugin and `box` — do?
2. What does "an observer, not a participant" mean? What does a plugin see and what can it not do?
3. Why should a plugin's failure not bring down the operation? How is this connected to plugins being freely switchable on and off?
4. How are typed events better than string names? Give examples of event families.
5. How does `OpenTelemetryPlugin` differ from `OcelPlugin` in what they provide? What do they have in common in wiring?
6. What are `watch_events` and several plugins on one machine for?
7. Does a plugin see the full `Context`, unlike an aspect? Why is that safe?

> **Exercise.** In the `01_ocel.py` example add a second built-in plugin to the machine — `OpenTelemetryPlugin` with console output (as in the [State chapter](step-02-state-as-x-ray.md)) — and confirm that both projections are gathered from one run without interfering with each other. Then narrow the OTel plugin via `watch_events` to only the `state` snapshots and compare what landed in each output.

---

<table width="100%"><tr>
  <td align="left"><a href="step-08-cache.md">← Step 08 — Cache</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-10-logs.md">Step 10 — Logs as business events →</a></td>
</tr></table>
