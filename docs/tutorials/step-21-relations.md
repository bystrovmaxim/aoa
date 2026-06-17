<!-- translated-from: step-21-relations_draft.md @ 2026-06-17T17:53:37Z · sha256:7b2c3bf4bfe3 -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Step 21 — Relations between entities

<table width="100%"><tr>
  <td align="left"><a href="step-20-entity.md">← Step 20 — Entity</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-22-lifecycle.md">Step 22 — Lifecycle →</a></td>
</tr></table>

- [Containers: cardinality and ownership](#containers-cardinality-and-ownership)
- [Inverse: the reverse side and the startup check](#inverse-the-reverse-side-and-the-startup-check)
- [Partial loading of relations](#partial-loading-of-relations)
- [Invariants](#invariants)
- [Review questions](#review-questions)

---

An [entity](step-20-entity.md) rarely stands alone: an order has a customer and lines, a customer has orders. In an ordinary project these are foreign keys and ORM "lazy" relations — hidden queries when you touch a field, and a silent `None` when the related data was not loaded. AOA declares relations **explicitly**: with a container that carries both the cardinality and the meaning of ownership, and is checked at startup.

[▶ Try in Colab](https://drive.google.com/file/d/1i3f6nn3qS79i2aBMB1s6Hr4uyfpByUxP/view?usp=drive_link) · [Open in project](../../examples/step_21_relations/01_relations.py)

The full domain picture: [▶ Try in Colab](https://drive.google.com/file/d/10H7oiSPR7d9rtJask9ccCzqDKSa4H9wQ/view?usp=drive_link) · [Open in project](../../examples/domain_model/01_domain_model.py)

---

## Containers: cardinality and ownership

A relation is declared with a container type. Two dimensions: **how many** (`One`/`Many`) and **whose ownership**:

| Container | Ownership | Meaning |
|-----------|-----------|---------|
| `CompositeOne` / `CompositeMany` | strong | the part does not exist without the whole (order lines) |
| `AggregateOne` / `AggregateMany` | weak | the part can live separately |
| `AssociationOne` / `AssociationMany` | none | an independent reference (order ↔ customer) |

A relation is declared in `Annotated`: the container type plus the `Inverse(...)` marker (or `NoInverse()`), with a mandatory `Rel(description=...)` as the field's value:

```python
@entity(description="Customer order", domain=ShopDomain)
class OrderEntity(BaseEntity):
    id: str = Field(description="Order id")
    total: float = Field(ge=0, description="Order total")

    customer: Annotated[
        AssociationOne[CustomerEntity],
        Inverse(CustomerEntity, "orders"),
    ] = Rel(description="Customer who placed the order")        # independent reference

    lines: Annotated[
        CompositeMany[OrderLineEntity],
        Inverse(OrderLineEntity, "order"),
    ] = Rel(description="Line items of the order")              # lines belong to the order
```

`One`/`Many` set the cardinality, `composition`/`aggregation`/`association` set the meaning of ownership. These relations land in the graph and the ERD of [Maxitor](../index.md#vi-maxitor).

## Inverse: the reverse side and the startup check

`Inverse(Target, "field")` explicitly names the **paired field** on the other side. This is needed because the heuristic "find the reverse relation by type" breaks the moment an entity has two fields of the same type — whereas a single line `Inverse(OrderEntity, "lines")` is unambiguous and survives refactoring. Every declared relation must carry `Rel(description=...)` — the model stays a specification, not just code.

When the graph is built (and it is built when the machine is created), the coordinator **checks the mirroring**: that the paired field exists, that the types and target entities match, and that the cardinality is compatible. An error in the relation model surfaces **at startup**, not half a year later in a report. In the example this is visible in the first line: the machine assembled — which means the relations were validated.

For an honestly one-way link, put `NoInverse()` (the absence of a reverse side is intentional, not forgotten); `NoGraphEdge()` removes the edge from the interchange graph while keeping the field in the node metadata.

## Partial loading of relations

The [partial-loading](step-20-entity.md#one-entity-different-load-levels) rule extends to relations too: the container **always knows the id**, but the related entity may not be loaded. Reaching through an un-hydrated container is a `RelationNotLoadedError`, not a silent `None` and not a hidden query:

```python
order = OrderEntity(
    id="ord-1", total=1500.0,
    customer=AssociationOne[CustomerEntity](id="cust-1"),          # id only
    lines=CompositeMany[OrderLineEntity](ids=("line-1", "line-2")),# ids only
)

order.customer.id      # ok — the id is always there
order.customer.name    # RelationNotLoadedError — the customer row is not loaded
len(order.lines)       # 2 — the number of ids is known
list(order.lines)      # RelationNotLoadedError — the line entities are not hydrated
```

To make a relation loaded, pass the entity itself (`One`) or the entities (`Many`) into the container; then attribute access is proxied to it:

```python
order2 = OrderEntity(
    id="ord-2", total=99.0,
    customer=AssociationOne[CustomerEntity](id="cust-1", entity=customer),  # hydrated
    lines=CompositeMany[OrderLineEntity](entities=(), entities_loaded=True),
)
order2.customer.name   # "Alice"
```

**Run:**

```bash
uv run python examples/step_21_relations/01_relations.py
```

**Output:**

```text
1) Machine built — relation model validated at startup (Inverse mirroring OK)

2) Id-only relations:
   order.customer.id  = cust-1   (is_loaded=False)
   len(order.lines)   = 2   (is_loaded=False)
   order.customer.name -> RelationNotLoadedError: Related object in AssociationOne is not loaded (id='cust-1'). Cannot access 'name' — only the identifier is present. Load the related entity through your persistence / manager layer.
   iterating order.lines -> RelationNotLoadedError (ids known, rows not loaded)

3) Hydrated relation:
   order2.customer.name = Alice   (proxied through the loaded entity)
```

Different queries return one `OrderEntity` with different relation-load depth — and the system controls accidental access to the not-loaded, instead of quietly slipping in a `None` or going to the database behind your back.

## Invariants

- **A relation is a container with ownership.** `Composite` (strong) / `Aggregate` (weak) / `Association` (none) × `One`/`Many`.
- **The reverse side is declared.** `Inverse(Target, "field")` or `NoInverse()`; every relation carries `Rel(description=...)`.
- **Mirroring is checked at startup.** The coordinator verifies the paired field, types, target, and cardinality when the graph is built; an error is at startup.
- **The container always knows the id.** Cardinality and the id are available without loading; `len(Many)` is the number of ids.
- **Not loaded ≠ `None`.** Access through an un-hydrated container → `RelationNotLoadedError`; no hidden lazy queries.

The full list is in [Intents and invariants](../reference/intents-and-invariants.md); the terms are in the [Glossary](../reference/glossary.md).

## Summary

Relations between entities are declared with containers that carry both the cardinality (`One`/`Many`) and the meaning of ownership (`Composite`/`Aggregate`/`Association`), and `Inverse(...)` names the reverse side so the coordinator can check the model's mirroring at startup. Relations load partially, like fields: the container always knows the id, but reaching an un-hydrated entity fails explicitly with `RelationNotLoadedError`. So one domain type serves queries of any depth, while an inconsistent relation model does not survive to production.

Next — **[Lifecycle](step-22-lifecycle.md)**: an entity's status not as a string without rules, but as a finite-state machine with verifiable transitions.

---

## Review questions

1. What are the three kinds of relation ownership, and how does `Composite` differ from `Association`? What does `One`/`Many` set?
2. Why is `Inverse(...)` needed if the reverse relation can be found by type? When does the heuristic break?
3. What does the coordinator check when building the graph, and at what moment does an error in the relation model surface?
4. What does a relation container always hold, and what only after loading?
5. What happens on `order.customer.name` if the customer is not hydrated, and how is this better than a silent `None` or a lazy query?
6. How do you make a relation honestly one-way, and how do you remove the edge from the graph while keeping the field?

> **Exercise.** In [01_relations.py](../../examples/step_21_relations/01_relations.py) change `Inverse(CustomerEntity, "orders")` on `OrderEntity.customer` to a non-existent field name and confirm the machine fails at creation — at startup, not on the first query. Then hydrate `lines` with two `OrderLineEntity` and check that iterating over `order.lines` now passes.

---

<table width="100%"><tr>
  <td align="left"><a href="step-20-entity.md">← Step 20 — Entity</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-22-lifecycle.md">Step 22 — Lifecycle →</a></td>
</tr></table>
