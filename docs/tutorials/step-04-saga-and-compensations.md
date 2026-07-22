<!-- translated-from: step-04-saga-and-compensations_draft.md @ 2026-07-10T14:55:05Z (filesystem mtime; draft is gitignored, no git history) · sha256:a9f83533782f -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Step 04 — Saga and compensations

<table width="100%"><tr>
  <td align="left"><a href="step-03-authorization-and-roles.md">← Step 03 — Authorization and roles</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-05-error-handling.md">Step 05 — Explicit error handling →</a></td>
</tr></table>

- [The problem: no shared transaction](#the-problem-no-shared-transaction)
- [A compensator next to its step](#a-compensator-next-to-its-step)
- [Rollback runs in reverse order](#rollback-runs-in-reverse-order)
- [Signature: what, and what it was](#signature-what-and-what-it-was)
- [When a compensator will not be called](#when-a-compensator-will-not-be-called)
- [Compensator errors are silent](#compensator-errors-are-silent)
- [Compensations, then @on_error](#compensations-then-on_error)
- [Invariants](#invariants)
- [Review questions](#review-questions)

---

In a distributed system there is no shared transaction. An order reserved goods in the warehouse, charged money through the payment gateway, called an external service — and failed on the fourth step. `ROLLBACK` does not exist here: the reservation and the charge already happened in foreign systems, and undoing them is only possible through a counter-operation — release the reservation, refund the money. This rollback logic is usually smeared across the main code with flags and `try/finally`, and the line between business logic and rollback is erased: you cannot tell where the operation does its job and where it cleans up the aftermath.

The **Saga** pattern answers this thus: every step has a **compensating** operation that undoes its effect, and on failure the already-executed steps are rolled back in reverse order. AOA builds the saga into the model itself. A compensator is declared with the `@compensate` decorator next to its step — as a visible part of the contract, not an admixture in the code. The machine itself assembles the stack of executed steps and unwinds it on error; the developer is left to describe how to roll back a single step. `@compensate` is as fundamental as `@regular_aspect`.

[▶ Try in Colab](https://drive.google.com/file/d/1PUZXdfSVjvkkjzaeoQ5sclUstJmguzbw/view?usp=drive_link) · [Open in project](../../examples/step_04_saga_and_compensations/01_saga_compensate.py)

---

## The problem: no shared transaction

Take an order fulfillment of three steps: reserve the item, charge the payment, confirm the order. The first two steps change the external world (warehouse, payment gateway). If confirmation fails, the reservation and the charge remain — they must be undone with counter-actions. Without a saga that undoing would land in `try/finally`, intermixed with business logic; with a saga — next to each step, as a separate declaration.

## A compensator next to its step

`@compensate(target_aspect, description)` binds a compensator method to a regular aspect **by direct callable reference**. The target aspect must be defined before the compensator in the class body — the reference is captured at class definition time. A compensator method's name ends with `_compensate`.

```python
@regular_aspect("Reserve inventory")
@result_string("reservation_id", required=True)
async def reserve_aspect(self, params, state, box, connections):
    await box.info(Channel.business, "regular: reserve order={%var.order_id}", order_id=params.order_id)
    return {"reservation_id": f"res-{params.order_id}"}

@compensate(reserve_aspect, "Release reservation")
async def reserve_compensate(self, params, state_before, state_after, box, connections, error):
    rid = state_after["reservation_id"] if state_after else "?"
    await box.info(Channel.business, "compensate: release reservation {%var.rid}", rid=rid)
```

So the step and its rollback stand as a pair. `charge_aspect` has its own `charge_compensate` ("refund the money"). And `confirm_summary` in the example fails on purpose:

```python
@summary_aspect("Confirm order")
async def confirm_summary(self, params, state, box, connections):
    raise ValueError("order service unavailable")
```

## Rollback runs in reverse order

When a step fails, the machine unwinds the stack of already-executed steps **in reverse order** — like a stack: the last executed is rolled back first. This is correct because later steps may have relied on earlier ones; undoing must start from the end.

**Run:**

```bash
uv run python examples/step_04_saga_and_compensations/01_saga_compensate.py
```

**Output:**

```text
  regular: reserve order=ord-001
  regular: charge order=ord-001
  compensate: refund txn-ord-001
  compensate: release reservation res-ord-001

order service unavailable
```

Reserve and charge went through; confirmation failed. The unwind started from the end: first `charge_compensate` (refund the money), then `reserve_compensate` (release the reservation). And only after the rollback did the original error come out. The order "refund → release" is the reverse of the execution order "reserve → charge".

## Signature: what, and what it was

A compensator receives **two** state snapshots — therein lies the subtlety:

```python
async def reserve_compensate(self, params, state_before, state_after, box, connections, error):
    ...
```

- `state_before` — the state **before** the step: what the world was like, if it needs restoring.
- `state_after` — the state **after** the step: this is where the data for the rollback lives — the payment `txn_id`, the id of the created record. Without it the compensator would not know *what exactly* to roll back.
- `error` — the exception that triggered the unwind: you can adapt the rollback strategy to the error type.

A compensator's return value is **ignored** — it performs a side effect (refund the money, delete the record), not an update of `state`. If the compensator needs context fields, it declares them via `@context_requires`, and then a seventh parameter `ctx` arrives (as with ordinary aspects).

A separate case is `state_after is None`. It means: "the aspect returned a dictionary, but the checker rejected it — the side effect may have occurred (the request to the gateway already went out), yet there is no valid `state`". A signal to the compensator: roll back on the fact of a possible effect, without relying on data.

## When a compensator will not be called

The stack is built predictably, and it is important to know its boundaries:

- **The step threw an exception before returning a dictionary** — the frame is not added to the stack: the side effect is not guaranteed (the exception could have happened before the call to the external system), there is nothing to roll back.
- **Compensators are only for regular aspects.** A `@summary_aspect` has no compensator — it assembles the `Result`, not performs rollbackable effects.
- **Compensators are not inherited.** They are assembled from the class itself, not from ancestors: under inheritance aspects are overridden, and an inherited compensator might reference a changed step. Need a rollback in the subclass — declare the compensator anew (the same logic as with [aspects](step-01-action-and-pipeline.md)).
- **A separate stack per nesting level.** If an aspect called a nested operation through `box.run` and wrapped the call in `try/except`, the child operation unwinds *its own* stack and re-raises the error; for the parent, such an aspect completed successfully and lands in *its* stack.
- **`rollup=True` disables compensation.** In "run-with-rollback" mode (see [Testing](../index.md#vi-testing)) the rollback is done transactionally at the connection level, not by compensators; the stack is not created.

## Compensator errors are silent

A compensator works in an emergency situation — external services may be unavailable. Therefore **a compensator's error is suppressed**: the unwind continues, the remaining compensators do not lose their chance, and what comes out is the **original** error of the step, not the rollback error. Otherwise the failure of one compensator would break the unwind (some effects would remain un-rolled-back) and would replace the business error in `@on_error` with a rollback error.

The machine guarantees that the unwind will not break; the success of the rollback itself is the developer's responsibility. Hence the practice: wrap the compensator body in `try/except`, make it idempotent, and log it. For observation the failure is not lost — the machine emits a `CompensateFailedEvent`, to which a monitoring [plugin](../index.md#iii-business-logic) subscribes (the whole unwind is framed by a pair of `SagaRollbackStartedEvent`/`SagaRollbackCompletedEvent` with totals: how many rolled back, how many failed, how many skipped).

## Compensations, then @on_error

The order of failure handling is strict: **first the saga unwind, then `@on_error`.** Compensators return the system to a consistent state; the error handler already works with rolled-back data and decides what to return outward. And it receives the **original** error of the step — the unwind is transparent to it. These are two independent layers: rollback (`@compensate`) and handling (`@on_error`), which is covered in the [next chapter](../index.md#iii-business-logic). In the example there is no `@on_error`, so after the rollback the error simply came out — and the launching code caught it.

## Invariants

- **Pairing.** `@compensate(target)` must reference an existing regular aspect of the same class; otherwise — an error at initialization (a compensator without a step is "dead rollback"). At most one compensator per aspect.
- **Regular only.** A compensator cannot be hung on a `@summary_aspect`.
- **Reverse order.** The unwind goes strictly from the last executed step to the first.
- **Silence.** A compensator's error neither interrupts the unwind nor is propagated — only a `CompensateFailedEvent`.
- **No inheritance.** Compensators are taken from the class itself, not from ancestors.
- **Layer order.** First compensations, then `@on_error` with the original error.
- **All checks at graph build** (fail-fast), not at runtime.

The full list is in [Intents and invariants](../reference/intents-and-invariants.md); the terms are in the [Glossary](../reference/glossary.md). Why rollback is made a separate declaration rather than a branch in the code is in the [Philosophy](../explanation/philosophy.md).

## Summary

A saga in AOA is not scattered `try/finally` but a declaration: a step has a compensator declared next to it. The machine assembles the stack of executed steps and, on failure, unwinds it in reverse order; the compensator receives `state_before`/`state_after` and the error itself, its failures are silent and best-effort, and after the rollback control passes to `@on_error`. The rollbackability of a distributed operation becomes a visible part of its contract.

Next — **[Explicit error handling](../index.md#iii-business-logic)**: what `@on_error` does after the unwind and how errors become a third independent layer.

---

## Review questions

1. Why can't a distributed operation get by with `ROLLBACK`, and what does the Saga pattern propose instead?
2. Why are compensators unwound in reverse order and not forward?
3. Why does a compensator need two states — `state_before` and `state_after`? What does `state_after is None` mean?
4. Why are compensator errors suppressed? What would happen if they were propagated?
5. In what order do the saga unwind and `@on_error` go, and why exactly so? Which error does `@on_error` receive?
6. When does a step's frame NOT land in the compensation stack? Why does a `@summary_aspect` have no compensator?
7. Which invariant prevents declaring a compensator for a non-existent step, and at what moment is it checked?

> **Exercise.** Add a third regular step `notify_aspect` with a compensator to the example and move the failure from the summary into that step (raise an exception in `notify_aspect`). Predict which compensators will run and in what order, then check against the output. What changes if you remove `@result_string` and make the step fail by the checker rather than return a dictionary?

---

<table width="100%"><tr>
  <td align="left"><a href="step-03-authorization-and-roles.md">← Step 03 — Authorization and roles</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-05-error-handling.md">Step 05 — Explicit error handling →</a></td>
</tr></table>
