<!-- translated-from: step-19-resource_draft.md @ 2026-06-17T17:53:37Z · sha256:2aed491d0e4e -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Step 19 — Resource: pure transport

<table width="100%"><tr>
  <td align="left"><a href="step-18-converters.md">← Step 18 — Schema converters</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-20-entity.md">Step 20 — Entity →</a></td>
</tr></table>

- [Two different beings](#two-different-beings)
- [A Resource is transport only](#a-resource-is-transport-only)
- [The BaseResource contract](#the-baseresource-contract)
- [A wrapper for nested operations](#a-wrapper-for-nested-operations)
- [How an operation gets a resource](#how-an-operation-gets-a-resource)
- [Rollup: checking against production data](#rollup-checking-against-production-data)
- [Invariants](#invariants)
- [Review questions](#review-questions)

---

The **Service** part taught how to publish an operation outward. The **Data model** part answers a different question: how to describe the domain — its boundary with the external world, entities, relations, lifecycle — without tying yourself to tables and an ORM. It all starts at the boundary, and the first hero here is the `Resource`.

In an ordinary project data access lives in services and repositories. Over time business logic seeps in: first a small check, then a calculation, then a conditional rollback — and the line between "fetch data" and "make a decision" blurs. AOA breaks this cycle firmly: the system has **two different beings**, and mixing them is not allowed.

[▶ Try in Colab](https://drive.google.com/file/d/1sV6LHId4MRH7I3Pg_-XwD3nf1uD5XCmZ/view?usp=drive_link) · [Open in project](../../examples/step_19_resource/01_resource.py)

The full domain picture (entities, relations, lifecycle, and resource together): [▶ Try in Colab](https://drive.google.com/file/d/10H7oiSPR7d9rtJask9ccCzqDKSa4H9wQ/view?usp=drive_link) · [Open in project](../../examples/domain_model/01_domain_model.py)

---

## Two different beings

- **`Action`** — an operation **without memory**. Every call starts from a clean slate; everything needed arrives through [`Params`](step-01-action-and-pipeline.md), `state`, and dependencies. Nothing is kept between calls. `Action` holds the **decisions**.
- **`Resource`** — an adapter with **long-lived state**. A database connection cannot be recreated on every request; a pool of HTTP clients lives as long as the application does. This state exists between calls — so it cannot be part of an `Action`. `Resource` holds the **transport**.

**The golden rule:** state lives longer than one call — it is a `Resource`; state lives only inside a call — it is an `Action`.

## A Resource is transport only

A `Resource` contains exactly one thing: transport. Open a connection, run a query, return the result. No business rules. If an `if` based on a business condition appears inside a resource — that `if` is out of place; its place is in the operation.

In the example this is literal: `InventoryResource` can only `get_stock` and `take` — read and deduct. The **decision** "is there enough stock, reserve or refuse" is made by the operation:

```python
@summary_aspect("Reserve if enough stock")
async def reserve_summary(self, params, state, box, connections):
    inventory = connections["inventory"]            # transport
    available = await inventory.get_stock(params.sku)
    if available < params.qty:                       # the decision — in the operation
        return ReserveResult(reserved=False, remaining=available)
    await inventory.take(params.sku, params.qty)
    return ReserveResult(reserved=True, remaining=available - params.qty)
```

The resource answers the question "**how** to fetch", the operation — "**what** to do with it". This is exactly the clean port of hexagonal architecture: it knows the language of the external world but speaks to the operation in the language of the domain.

## The BaseResource contract

A resource subclasses `BaseResource` and must declare two things:

- **`@meta(description=, domain=)`** — like an operation, a description and a domain (needed by the system graph; without them the graph build fails);
- **`get_wrapper_class()`** — an abstract method: returns a wrapper class for passing into nested operations, or `None` when direct pass-through is safe.

```python
@meta(description="In-memory inventory store (transport only)", domain=WarehouseDomain)
class InventoryResource(BaseResource):
    def __init__(self, stock=None):
        self._stock = dict(stock or {})

    def get_wrapper_class(self) -> type[BaseResource] | None:
        return None          # in-memory: direct pass-through
```

## A wrapper for nested operations

Why a wrapper at all? When an operation calls a nested one through `box.run`, the resource is passed along. But the nested operation **must not** control someone else's transaction — otherwise it could commit or roll back data it does not own. We already saw this boundary in the chapters on [dependencies](step-06-dependencies.md) and [connections](step-17-connections.md); here is its source.

A transactional resource is shaped as a trio **Protocol → manager → wrapper**: the wrapper implements the same protocol, delegates `execute`, but raises `TransactionProhibitedError` on `open/begin/commit/rollback`. The root operation owns the transaction; nested ones only run statements. `get_wrapper_class()` returns this wrapper class (and the wrapper returns it again — for deeper nesting). For an in-memory or stateless resource there is no transaction, so `None` — direct pass-through. The full template is in the [«Custom resource»](../index.md#how-to-write-your-own-extension) extension point.

## How an operation gets a resource

A resource reaches an operation by two paths, both familiar from the [dependencies](step-06-dependencies.md) chapter:

- **`@connection`** — an already-open resource the operations are **handed** (a connection, pool, shared store). The aspect reads it from `connections["key"]`, and the adapter supplies it at the boundary ([in two modes](step-17-connections.md)).
- **`@depends`** — a resource the machine **creates** with a factory on demand; the aspect takes it via `await box.resolve(...)`.

In both cases the operation stays clean and **testable**: to test it, you swap the resource — give the same operation a different store. The example shows exactly this: one `ReserveStockAction`, different resources.

**Run:**

```bash
uv run python examples/step_19_resource/01_resource.py
```

**Output:**

```text
Real inventory (sku-1: 10 in stock):
  reserve 3   -> reserved=True, remaining=7
  reserve 99  -> reserved=False, remaining=7

Swapped resource (empty store, same Action):
  reserve 1   -> reserved=False, remaining=0
```

The "reserve or refuse" decision is the same — only the store behind the resource changes. Changing storage (in-memory → PostgreSQL) means rewriting only the resource; the operation logic is untouched, and `Entity` stays a stable contract between layers.

## Rollup: checking against production data

A resource can declare that it supports **rollup** — a mode where writes run in a transaction, but at the commit stage a rollback is performed instead of persisting. This lets you run a scenario against the production schema while saving nothing. By default `check_rollup_support()` raises `RollupNotSupportedError`; resources that can do it (SQL ones, for example) override the method and return `True`. In detail — in the [Testing](../index.md#v-testing) part *(soon)*.

## Invariants

- **Two beings.** A memoryless `Action` holds decisions; a `Resource` with long-lived state holds transport. State outliving the call → `Resource`.
- **Transport only.** No business rules in a resource; the decision is in the operation.
- **The contract.** `BaseResource` requires `@meta` and `get_wrapper_class()` (`None` — direct pass-through).
- **The wrapper protects the transaction.** Nested operations run statements but do not control someone else's transaction (`TransactionProhibitedError`).
- **Swap to test.** An operation gets a resource via `@connection`/`@depends` and is tested by swapping the resource, without touching the logic.

The full list is in [Intents and invariants](../reference/intents-and-invariants.md); the terms are in the [Glossary](../reference/glossary.md).

## Summary

A `Resource` is pure transport with long-lived state, strictly separated from the `Action`: the latter holds decisions, the resource holds access to the external world. It subclasses `BaseResource`, declares `@meta` and `get_wrapper_class()`, and in nested calls is wrapped so it cannot control someone else's transaction. An operation gets a resource via `@connection` or `@depends` and stays testable by swapping the resource. This separation is what makes the rest possible: storage changes without touching the logic, and `Entity` serves as the contract between layers.

Next — **[Entity](step-20-entity.md)**: a domain object independent of storage, which the resource hydrates and the operation reads.

---

## Review questions

1. State the golden rule for choosing between `Action` and `Resource`. Why can a database connection not be part of an `Action`?
2. What does a `Resource` contain, and what should not be in it? Where would a business `if` be "out of place"?
3. Which two things must a `BaseResource` subclass declare?
4. Why is a resource wrapper needed, and what does it forbid nested operations? What does `get_wrapper_class()` do?
5. By which two ways does an operation get a resource, and how do they differ?
6. How does the `Action`/`Resource` separation make an operation testable without a real database?

> **Exercise.** In [01_resource.py](../../examples/step_19_resource/01_resource.py) add a `restock(sku, qty)` method to `InventoryResource` and a `RestockAction` that calls it — confirm the resource still has no business `if`. Then move the check "you can't reserve more than the stock" inside the resource and explain why this breaks the separation and what it threatens a year from now.

---

<table width="100%"><tr>
  <td align="left"><a href="step-18-converters.md">← Step 18 — Schema converters</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-20-entity.md">Step 20 — Entity →</a></td>
</tr></table>
