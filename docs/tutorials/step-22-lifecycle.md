<!-- translated-from: step-22-lifecycle_draft.md @ 2026-06-17T17:53:37Z · sha256:48a68f0cf4f6 -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Step 22 — Lifecycle: status as a finite-state machine

<table width="100%"><tr>
  <td align="left"><a href="step-21-relations.md">← Step 21 — Relations</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-23-testbench.md">Step 23 — TestBench →</a></td>
</tr></table>

- [Template in the class, state in the instance](#template-in-the-class-state-in-the-instance)
- [Transitions are checked](#transitions-are-checked)
- [Validating the automaton at startup](#validating-the-automaton-at-startup)
- [Invariants](#invariants)
- [Review questions](#review-questions)

---

In the [Entity chapter](step-20-entity.md) an order's status was a plain string field `status: str`. Such a status has no rules: nothing stops writing `status = "delivered"` straight from `draft`. The allowed transitions live in the developer's head or in a comment that went stale long ago.

AOA replaces the string with a finite-state machine — a `Lifecycle`, declared in code and attached to an entity as a field. This is the final touch of the **Data model** part: after `Resource`, `Entity`, and relations — the rules by which an object changes its state.

[▶ Try in Colab](https://drive.google.com/file/d/1mm0_blcgFKwd5yMJKNBSvAqjgfWjLXF6/view?usp=drive_link) · [Open in project](../../examples/step_22_lifecycle/01_lifecycle.py)

---

## Template in the class, state in the instance

A `Lifecycle` is split in two. The **template** — the graph of states and transitions — is built once in the class body with a fluent builder. Each state gets a key and a label, lists its transitions with `.to(...)`, and ends with a classification — `.initial()`, `.intermediate()`, or `.final()` (a final state has no outgoing transitions):

```python
class OrderLifecycle(Lifecycle):
    _template = (
        Lifecycle()
        .state("draft", "Draft").to("paid", "cancelled").initial()
        .state("paid", "Paid").to("shipped", "cancelled").intermediate()
        .state("shipped", "Shipped").to("delivered").intermediate()
        .state("delivered", "Delivered").final()
        .state("cancelled", "Cancelled").final()
    )
```

The **instance** holds only the current state — a single key, validated against the template:

```python
class OrderEntity(BaseEntity):
    id: str = Field(description="Order id")
    total: float = Field(ge=0, description="Order total")
    lifecycle: OrderLifecycle = Field(description="Order lifecycle state")

order = OrderEntity(id="ord-1", total=1500.0, lifecycle=OrderLifecycle("draft"))
```

A non-existent key (`OrderLifecycle("done")`) is an `InvalidStateError` right at creation. So each row in storage carries a single key, while the rules are shared, in the template.

## Transitions are checked

You ask the instance what it can do and whether a transition is possible, and the transition itself returns a **new** `Lifecycle` (the current one is not mutated) — consistent with the immutability of `Entity`. You update the entity via `model_copy`:

```python
order.lifecycle.available_transitions      # {'paid', 'cancelled'}
order.lifecycle.can_transition("shipped")  # False — you can't go straight from draft

paid = order.lifecycle.transition("paid")            # a new object
order = order.model_copy(update={"lifecycle": paid}) # apply to the entity
```

An illegal transition is not a silent write but an `InvalidTransitionError`, and it happens here and now, not "someday in production".

**Run:**

```bash
uv run python examples/step_22_lifecycle/01_lifecycle.py
```

**Output:**

```text
1) Machine built — lifecycle automaton validated at startup

2) Current state and rules:
   current_state='draft'  is_initial=True  available=['cancelled', 'paid']
   can_transition('paid')=True  can_transition('shipped')=False

3) After transition('paid'):
   order.lifecycle.current_state='paid'  (original 'draft' instance untouched)

4) Illegal transition:
   transition('delivered') -> InvalidTransitionError: Transition 'paid' → 'delivered' is not allowed on OrderLifecycle. Allowed transitions from 'paid': cancelled, shipped.
```

The main thing is visible: from `draft` only `paid` and `cancelled` are available; an allowed transition gives a new instance, and an attempt to jump from `paid` straight to `delivered` is rejected with an explicit error.

## Validating the automaton at startup

The template is not just a set of strings: when the graph is built (that is, when the machine is created), the system **validates the automaton structure** — that the states and transitions are consistent, that the `initial`/`intermediate`/`final` classification is meaningful. An inconsistent graph does not let the system start. This is the same discipline as with [relations](step-21-relations.md): the domain model is checked at startup, not falling apart in a report half a year later.

And since the automaton is declared in code rather than in a comment or a DB migration, [Maxitor](../index.md#vii-maxitor) draws it as a separate state diagram, and [OCEL events](step-09-plugins.md) bind to meaning: "order `ord-1` moved to `paid`", not "a step ran".

## Invariants

- **Template and instance are separated.** The state graph is in the class's `_template`; the instance holds one current key.
- **State is validated at creation.** A non-existent key → `InvalidStateError`.
- **A transition does not mutate.** `transition()` returns a new `Lifecycle`; the entity is updated via `model_copy`.
- **An illegal transition is explicit.** `transition()` onto a forbidden edge → `InvalidTransitionError`; a `final` state has no outgoing transitions.
- **The automaton is validated at startup.** The structure (states, transitions, classification) is checked by the graph build; inconsistency is at startup.

The full list is in [Intents and invariants](../reference/intents-and-invariants.md); the terms are in the [Glossary](../reference/glossary.md).

## Summary

A `Lifecycle` turns a status from a string without rules into a finite-state machine: the template of states and transitions is declared in the class, the instance carries one current key, a transition returns a new value and rejects forbidden paths with an explicit error, and the automaton structure is validated at startup. Together with `Resource`, `Entity`, and relations this is the AOA data model — a domain described and verifiable in code, without ties to tables.

With this the **Data model** part is assembled: the boundary with the world (`Resource`), the domain object (`Entity`), its relations, and its lifecycle. Next — the **Testing** part, and its first tool is **[TestBench](step-23-testbench.md)**: the same `Action` through the same machine, but in a substituted reality.

---

## Review questions

1. How is a `Lifecycle` better than a `status` string field? What can you not do with an automaton-status that is easy with a string?
2. What does the template hold, and what does the instance? Why is this separation convenient for storage?
3. What does `transition()` return, and why does it not change the current object? How do you apply a transition to an entity?
4. What happens on `OrderLifecycle("done")` if there is no such state, and on a forbidden `transition(...)`?
5. What is validated in the automaton when the graph is built, and at what moment will an error in the state model surface?
6. Why is an automaton declared in code useful for Maxitor and OCEL?

> **Exercise.** In [01_lifecycle.py](../../examples/step_22_lifecycle/01_lifecycle.py) walk the order along the legal path `draft → paid → shipped → delivered`, applying each transition via `model_copy`, and at `delivered` confirm that `available_transitions` is empty (a final state). Then add a `returned` state to the template with a transition from `delivered` and watch `delivered` stop being final after the rebuild.

---

<table width="100%"><tr>
  <td align="left"><a href="step-21-relations.md">← Step 21 — Relations</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-23-testbench.md">Step 23 — TestBench →</a></td>
</tr></table>
