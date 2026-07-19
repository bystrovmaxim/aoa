<!-- translated-from: step-20-entity_draft.md @ 2026-07-10T14:55:05Z (filesystem mtime; draft is gitignored, no git history) · sha256:ec1cf8dcdad0 -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Step 20 — Entity: a domain object without storage

<table width="100%"><tr>
  <td align="left"><a href="step-19-resource.md">← Step 19 — Resource</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-21-relations.md">Step 21 — Relations →</a></td>
</tr></table>

- [A business object, not a table row](#a-business-object-not-a-table-row)
- [The resource hydrates, the operation reads](#the-resource-hydrates-the-operation-reads)
- [One Entity, different load levels](#one-entity-different-load-levels)
- [What an Entity is not](#what-an-entity-is-not)
- [Relations and lifecycle — later](#relations-and-lifecycle--later)
- [Consequences](#consequences)
- [Invariants](#invariants)
- [Review questions](#review-questions)

---

An `Action` makes decisions, but it works with business objects: an order, a customer, a payment. In an ordinary project such an object is whatever the database returned: an ORM row with column-named fields, or a foreign API's JSON. Let an operation work with it directly — and it starts depending on storage details: the ORM changed, rewrite the logic; moved to another database, rewrite again.

The [previous chapter](step-19-resource.md) introduced `Resource` — pure transport. This one introduces its partner: `Entity` — the declaration of a business object in the language of the domain, without ties to storage. Together they give the separation everything was started for: `Resource` answers "how to fetch", `Entity` — "what this object is", `Action` — "what to do with it".

[▶ Try in Colab](https://drive.google.com/file/d/1tfuwCaLyGPn4zbQq71KljnM4klFHcsEE/view?usp=drive_link) · [Open in project](../../examples/step_20_entity/01_entity.py)

The full picture with relations and lifecycle: [▶ Try in Colab](https://drive.google.com/file/d/10H7oiSPR7d9rtJask9ccCzqDKSa4H9wQ/view?usp=drive_link) · [Open in project](../../examples/domain_model/01_domain_model.py)

---

## A business object, not a table row

An `Entity` is declared as a class with `@entity(description=, domain=)`, a subclass of `BaseEntity`; the name must end with `Entity` (otherwise an error at class definition):

```python
@entity(description="Customer order", domain=ShopDomain)
class OrderEntity(BaseEntity):
    id: str = Field(description="Order identifier")
    total: float = Field(ge=0, description="Order total")
    currency: str = Field(default="RUB", description="Currency code")
    status: str = Field(description="Order status")
```

`OrderEntity` knows an order has an `id`, `total`, `status`. It knows nothing about the `orders` table, the `total_amount` column, or a `JOIN` — this is the language of the domain, not of storage.

## The resource hydrates, the operation reads

Turning raw storage data into an `Entity` is the [resource's](step-19-resource.md) job, and it does it with the `build` function. In the simple case the keys match the fields:

```python
order = build({"id": "ord-1", "total": 1500.0, "currency": "RUB", "status": "paid"}, OrderEntity)
```

When the storage shape is different, the resource specifies a **mapping** — and this is its only job, without a single business decision:

```python
order = build(row, OrderEntity, lambda e, r: {
    e.id:       r["order_id"],
    e.total:    r["total_amount"],
    e.currency: r["ccy"],
    e.status:   r["state"],
})
```

`e.total` is a typed field "token", `r[...]` is a storage column. The operation, meanwhile, sees an `OrderEntity` regardless of what is under the hood — PostgreSQL, ClickHouse, or a test fixture. Changed the storage — rewrote only `build` in the resource; the operation logic is untouched.

## One Entity, different load levels

Usually different queries breed different classes: `OrderListRow`, `OrderDetailRow`, `OrderWithCustomerRow`. In AOA there is one `OrderEntity` with different **load levels**. A partial load is built via `partial`:

```python
partial = OrderEntity.partial(id="ord-3", total=42.0)   # only id and total are loaded
```

The key difference from the usual "a missing field = `None`": reading a **declared but not loaded** field is not a silent `None` but a `FieldNotLoadedError`. The not-loaded state is visible at once, rather than turning into a `None` that quietly leaks into a calculation.

**Run:**

```bash
uv run python examples/step_20_entity/01_entity.py
```

**Output:**

```text
1) Full entity (direct build):
   ord-1  total=1500.0 RUB  status=paid

2) Same Entity from a differently-shaped row (mapper):
   ord-2  total=99.5 EUR  status=shipped

3) Partial load (only id, total):
   id=ord-3  total=42.0
   is_field_loaded('status') = False
   primary key = {'id': 'ord-3'}
   reading status -> FieldNotLoadedError: Field 'status' on entity 'OrderEntity' is not loaded. Loaded fields: id, total. Use a full constructor or include 'status' in partial().
```

Everything is visible: the same `OrderEntity` built directly, from a row with different column names, and partially. For the partial instance `is_field_loaded` honestly reports what is loaded, `get_primary_key()` returns `id` (the primary key by convention), and reading the unloaded `status` fails with an explicit error.

## What an Entity is not

An `Entity` is not an ORM class, nor a DTO assembled wherever. It is `frozen` and `extra="forbid"`, and it is hydrated at the boundary — by the resource via `build`/`partial`. Do not confuse it with an [entity wire projection](step-15-schema-results.md#a-partial-entity-projection) (`BaseEntity.schema(...)`): a projection is an external *slice* for an API, validated by a JSON Schema, while an `Entity` is the internal domain contract between the resource and the operation. The first goes outward, the second lives inside.

## Relations and lifecycle — later

An `Entity` describes more than fields. An order has **relations** (a customer, order lines) and a **lifecycle** — the allowed status transitions. In this chapter `status` is a plain string field; in the [next one](../index.md#v-data-model) it becomes a `Lifecycle` — a finite-state machine where a `draft → shipped` transition is directly impossible. Relations between entities are the topic of the [Relations](../index.md#v-data-model) chapter. Here the point is to grasp the `Entity` itself as a unit of the domain.

## Consequences

The `Entity` / `Resource` separation quietly switches on several important things:

- **Cheap storage change.** PostgreSQL → ClickHouse → a test fixture — only `build` in the resource changes; `Entity` and the logic are stable.
- **No DTO sprawl.** One `Entity` instead of a family of `…Row` classes; the load level is expressed by `partial`, not a new type.
- **OCEL bound to the domain.** When the business object is declared explicitly, [process-mining events](step-09-plugins.md) bind to real objects: the analyst sees "order `ord-001` moved to `paid`", not "the `charge_aspect` step ran".

## Invariants

- **Domain, not storage.** An `Entity` is declared in business terms; it knows nothing of tables and columns.
- **Name ends with `Entity`.** A `BaseEntity` subclass must be named `…Entity`.
- **The resource hydrates.** `build(data, Entity)` directly, or with a mapper `build(row, Entity, lambda e, r: {...})`; no business logic in the mapping.
- **Load levels, not classes.** One `Entity`; `partial(...)` materialises some fields.
- **Not loaded ≠ `None`.** Reading a declared, unloaded field → `FieldNotLoadedError`.
- **`Entity` ≠ a projection.** `BaseEntity.schema(...)` is an external JSON-Schema slice; `Entity` is the internal domain contract.

The full list is in [Intents and invariants](../reference/intents-and-invariants.md); the terms are in the [Glossary](../reference/glossary.md).

## Summary

An `Entity` is the declaration of a business object in the language of the domain, detached from storage: the resource hydrates it via `build` (directly or by mapping columns to fields), and the operation reads it without knowing about the database. One `Entity` replaces a family of DTOs with different load levels, and reading an unloaded field fails explicitly rather than returning `None`. This is what makes a storage change cheap and events bound to the domain.

Next — **[Relations](step-21-relations.md)**: how an `Entity` references other entities (`Association`, `Composition`, `Aggregation`) with consistency checked at startup.

---

## Review questions

1. Why is an operation working directly with an ORM row or a foreign API's JSON a problem? What does `Entity` break out of this?
2. How is an `Entity` detached from storage, and who turns storage data into an `Entity`?
3. How does `build(data, Entity)` differ from `build(row, Entity, mapper)`, and what must not be done in the mapper?
4. How does one `Entity` replace a family of DTOs? What is a load level?
5. What happens when reading a declared but not loaded field, and how is this better than a silent `None`?
6. How does an `Entity` differ from a `BaseEntity.schema(...)` projection from the result-by-schema chapter?

> **Exercise.** In [01_entity.py](../../examples/step_20_entity/01_entity.py) load an order via `OrderEntity.partial(id="ord-9")` (only `id`) and check `is_fields(["id", "total"])` — explain the result. Then write a second `build` function with a different set of columns (as if the data came from another storage) and confirm that an operation reading `OrderEntity` does not notice the difference.

---

<table width="100%"><tr>
  <td align="left"><a href="step-19-resource.md">← Step 19 — Resource</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-21-relations.md">Step 21 — Relations →</a></td>
</tr></table>
