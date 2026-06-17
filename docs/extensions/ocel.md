<!-- translated-from: ocel_draft.md @ 2026-06-17T17:02:35Z · sha256:7bed1f8741cd -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# OCEL 2.0 — an object-centric event log for process mining

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>

- [Why OCEL: what ordinary process mining cannot do](#why-ocel-what-ordinary-process-mining-cannot-do)
- [Key concepts of OCEL 2.0](#key-concepts-of-ocel-20)
- [What it enables: analysis tools](#what-it-enables-analysis-tools)
- [Canonical sources](#canonical-sources)
- [Why AOA gives OCEL almost for free](#why-aoa-gives-ocel-almost-for-free)
- [Installation](#installation)
- [How an operation emits an event](#how-an-operation-emits-an-event)
- [Export policy in v1](#export-policy-in-v1)
- [Parameters](#parameters)
- [What's inside the example](#whats-inside-the-example)

---

OCEL is a relatively new topic, still little known in engineering circles, so let us start with it rather than with the plugin. `OcelPlugin` is merely an exporter; the value lies in **what kind of analysis** this format opens up.

## Why OCEL: what ordinary process mining cannot do

Process mining reconstructs the real process from an **event log**. A classic log is "flat": every event has a single **case id** (the identifier of a process instance), an activity, and a time. The whole analysis is built around this single case id: "one order — one case".

The problem is that a real business event almost always touches **several objects of different types at once**: an order, its line items, a customer, a payment, a delivery, an invoice. To fit this into a single case id, the log has to be **"flattened"** — pick one "point of view" (case notion) and bind everything to it. Flattening gives rise to two classic pathologies (that is exactly what the OCPM literature calls them):

- **Convergence:** an event linked to several objects (for example, "assemble the order" with ten line items) is **duplicated** across cases — counters and metrics get inflated.
- **Divergence:** events of different objects within one case cannot be told apart — order and dependencies are **distorted** (the sub-flows of line items collapse).

And, most importantly: each new question ("how do the line items behave?", "what about the payments?") requires a **new export** with a different case notion, while the relationships between objects are **lost irreversibly** during flattening.

**Object-centric process mining (OCPM)** removes flattening itself: an event stays linked to **many objects of many types**, with no single point of view chosen. **OCEL 2.0** is the standardized log format for such analysis.

## Key concepts of OCEL 2.0

- **Events** — events with a type (event type), a time, and attributes.
- **Objects** — objects with a type (object type) and attributes, where the attributes may **change over time** (the object lifecycle).
- **E2O (event-to-object)** — an "event → object" link with a **qualifier** (the object's role in the event): which objects took part in the event and how.
- **O2O (object-to-object)** — links between objects (order → line item, order → customer).

The log is not an "event × attributes" table but a **graph of events and objects**. OCEL 2.0 serializes to JSON / XML / SQLite.

## What it enables: analysis tools

On an object-centric log a whole class of analysis works that is inaccessible to a "flat" log:

- **Object-centric discovery** — process discovery across several object types at once (object-centric Petri nets / a directly-follows graph per type) without gluing them into one case.
- **Analysis of object-type interaction** — how orders, line items, and payments affect one another along the process.
- **Performance and bottlenecks by object type** — where exactly "delivery" stalls, not "the order in general".
- **Conformance checking** — the divergence of the observed process from a reference model, per object.

What this solves: reliable analysis of multi-object processes (order-to-cash, manufacturing, healthcare), one log for many questions instead of re-exporting under each case notion, preserved links between objects, and no convergence/divergence distortions.

## Canonical sources

- **The OCEL 2.0 standard** — the specification, schemas, and sample logs: [ocel-standard.org](https://www.ocel-standard.org/).
- **PM4Py** — an open process-mining library with object-centric support (`read_ocel2_json`, OC-discovery): [pm4py.fit.fraunhofer.de](https://pm4py.fit.fraunhofer.de/).
- The concept of **object-centric process mining** and the OCEL format go back to the work of W. van der Aalst and colleagues; the "OCEL 2.0 Specification" is the canonical description of the format.

## Why AOA gives OCEL almost for free

An object-centric log requires declared **objects**, their **types**, and their **relationships**. In AOA these already exist: [`Entity`](../tutorials/step-20-entity.md) is an object and its type, [relations](../tutorials/step-21-relations.md) are O2O/E2O, an [`Action`](../tutorials/step-01-action-and-pipeline.md) is an event. So the "choice of case notion" problem simply never arises here: objects are first-class, and the log comes out as a **by-product** of the pipeline rather than a separate export. `OcelPlugin` is an observer (a [plugin](../tutorials/step-09-plugins.md)): it does not touch the business code.

Example for this article: [01_ocel.py](../../examples/step_09_plugins/01_ocel.py).

## Installation

```bash
pip install "aoa-action-machine[ocel]"
```

## How an operation emits an event

The data flow: an aspect returns `list[OcelFrame]` → on `GlobalFinishEvent` `OcelPlugin` assembles an `OcelEvent` (with E2O links and object attributes) → writes it to the store. The aspect puts "frames" into `state` under the key `OCEL_FRAMES_KEY`; each `OcelFrame(object=entity, qualifier="...")` links the operation-event to a domain object:

```python
from aoa.action_machine.plugin.ocel import OCEL_FRAMES_KEY, OcelFrame, OcelPlugin, InMemoryOcelStoreResource

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

The store is attached as a resource with an `open()`/`close()` lifecycle; `InMemoryOcelStoreResource` accumulates events in memory and writes OCEL-2.0 JSON on `close()`:

```python
store = InMemoryOcelStoreResource(output_file="ocel_log.json")
machine = ActionProductMachine(plugins=[OcelPlugin(store=store, short_names=True)])
await store.open()
# ... machine.run(...) — each run appends an event ...
await store.close()   # write the file
```

## Export policy in v1

- **E2O only** (event-to-object) over the entity's **loaded** relations (one hop along the foreign keys). **O2O is not exported in v1.**
- The export prefers **reachability over a minimal graph**: an object lands in the event if the aspect loaded it. Filters in PM tools will narrow the view later; a **lost E2O cannot be restored** without a re-export.
- Zero frames → the event is not added; an attribute-name conflict → `OcelContractError`; the store must be opened in the owning operation.

## Parameters

`OcelPlugin(store, *, short_names=False)`:

- `store` — an `OcelStoreProtocol` implementation (for example, `InMemoryOcelStoreResource`).
- `short_names` — strips the `Action`/`Entity`/`Lifecycle` suffixes from event and object types (`CreateOrderAction` → `CreateOrder`).

## What's inside the example

```text
written: ocel_log.json
events: 3 | objects: 3

sample event:
{"id": "...", "type": "CreateOrder", "time": "...", "attributes": [],
 "relationships": [{"objectId": "orde_632_ord-001", "qualifier": "Create order"}]}
```

Three runs of `CreateOrderAction` produced three OCEL events, each with an E2O link to its own order object via `qualifier`. This is a ready input for PM4Py — assembled from the same pipeline, with no separate analytical subsystem.

The plugin concept is in the chapter [Plugins](../tutorials/step-09-plugins.md); domain objects are in the chapter [Entity](../tutorials/step-20-entity.md); your own observer is [«Your own plugin»](../index.md#how-to-write-your-own-extension).

---

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>
