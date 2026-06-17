<!-- translated-from: step-24-substitution_draft.md @ 2026-06-17T17:53:37Z · sha256:ffa5773dad7a -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Step 24 — Substituting the environment

<table width="100%"><tr>
  <td align="left"><a href="step-23-testbench.md">← Step 23 — TestBench</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-25-context.md">Step 25 — Context →</a></td>
</tr></table>

- [with_mocks: substitution by class](#with_mocks-substitution-by-class)
- [Mocks reach the whole tree](#mocks-reach-the-whole-tree)
- [connections: substitution by key](#connections-substitution-by-key)
- [Double run: async and sync](#double-run-async-and-sync)
- [Rollup: a live database without persisting](#rollup-a-live-database-without-persisting)
- [Invariants](#invariants)
- [Review questions](#review-questions)

---

The [previous chapter](step-23-testbench.md) showed at what **depth** to run an operation. This one is about what to **substitute** the reality around it with. There are two mechanisms, and they differ by key:

- **`with_mocks({Class: value})`** — by **class**: substitutes what an aspect obtains through `await box.resolve(...)` — a [`@depends` dependency or resource](step-06-dependencies.md);
- **`connections={key: resource}`** — by **string key** (the run argument): supplies a `@connection` resource per call.

Plus **Rollup** — a continuation of the resource theme: a run on a live schema with rollback instead of persisting.

[▶ Try in Colab](https://drive.google.com/file/d/1YOZkXCa8BsGbzjqdUG-thKhxDRE531Tp/view?usp=drive_link) · [Open in project](../../examples/step_24_substitution/01_substitution.py)

---

## with_mocks: substitution by class

`with_mocks` substitutes what an operation **resolves**. The key is the dependency or resource class, the value is the mock:

```python
pricing = AsyncMock(spec=PricingService)
pricing.price.return_value = 100.0

r = await TestBench().with_mocks({PricingService: pricing}).run(QuoteAction(), params, rollup=False)
# -> price=100.0
```

The values adapt: a ready `Result` is wrapped in a mock with a fixed result, and a callable is wrapped in a mock with a `side_effect`. A dependency not declared in `@depends` cannot be substituted — it simply does not exist for the factory.

## Mocks reach the whole tree

An important subtlety about nested operations. When a parent calls `await box.run(ReserveStockAction, ...)`, the nested operation **runs for real** through the same machine — `with_mocks` does not substitute its result wholesale. But the mocks reach **the whole tree**: the nested operation's `@depends` dependencies are substituted too. So a nested operation is controlled by substituting **its** dependencies:

```python
gateway = AsyncMock(spec=StockGateway)
gateway.reserve.return_value = "res-001"

# CheckoutAction internally calls box.run(ReserveStockAction); that resolves StockGateway
r = await TestBench().with_mocks({StockGateway: gateway}).run(CheckoutAction(), params, rollup=False)
# reservation=res-001 — the mock reached the nested operation
```

So nested operations stay real (they are tested together with the parent), and controllability comes from substituting their dependencies.

## connections: substitution by key

A `@connection` resource is substituted not through `with_mocks` but through the `connections=` argument on `run`/`run_aspect`/`run_summary` — by the same string key declared in `@connection`:

```python
journal = JournalResource()
r = await TestBench().run(RecordAction(), RecordParams(row="row-A"), rollup=False,
                          connections={"journal": journal})
```

Here you supply either a real resource (as here — to then check its state) or a mock. The split by key is not accidental: `with_mocks` is by type (what is resolved), `connections=` is by slot name (what is passed).

## Double run: async and sync

One detail worth knowing. For reliability, `TestBench.run` runs the operation **twice** — on the asynchronous and the synchronous machine — and **compares the results**: a discrepancy by itself catches a parity bug. The practical consequence: side effects on a shared mutable resource happen **twice**. So check the **result** (it is deterministic), not the accumulated state of the resource; or give each run a fresh mock/resource. In the example `RecordAction` returns not "how much was written in total" but the fact of writing, and the journal's state is checked from the outside.

## Rollup: a live database without persisting

`rollup=True` — a mode for transactional resources: the operation performs real `INSERT`/`UPDATE`, goes along the real pipeline, but on `commit()` the resource does a **rollback** instead of persisting. The integration is checked on a live schema and real DB constraints, persisting nothing.

If a resource does **not** support rollup, the machine honestly fails on `check_rollup_support()` rather than pretending the test is safe:

```python
# A resource without rollup support:
await TestBench().run(QuoteAction(), params, rollup=True)
# -> RollupNotSupportedError: Class 'PricingService' does not support rollup.

# A resource with rollup support: commit does a rollback — nothing persisted:
journal = JournalResource(rollup=True)
await TestBench().run(RecordAction(), RecordParams(row="row-B"), rollup=True,
                      connections={"journal": journal})
# journal.persisted == []  (the write happened, but commit rolled it back)
```

This is the continuation of the resource theme from the [Resource chapter](step-19-resource.md#rollup-checking-against-production-data): rollup support is declared by the resource itself, by overriding `check_rollup_support()`.

**Run:**

```bash
uv run python examples/step_24_substitution/01_substitution.py
```

**Output:**

```text
1) mock @depends            -> price=100.0
2) nested Action, mocked dep-> reservation=res-001  (mock reached the child)
3) supply @connection       -> committed=True  (row-A persisted: True)
4) rollup, unsupported res  -> RollupNotSupportedError: Class 'PricingService' does not support rollup. Implement check_rollup_support() or use a resource manager that supports transactional rollback.
5) rollup, capable res      -> committed=True  (nothing persisted: True)
```

## Invariants

- **`with_mocks` — by class.** Substitutes what an aspect `box.resolve`s (`@depends`, resources); the undeclared cannot be substituted.
- **Mocks reach the tree.** A nested operation via `box.run` runs for real; you substitute its dependencies, not its result.
- **`connections=` — by key.** A `@connection` resource is supplied by a string key per run, not through `with_mocks`.
- **Double run.** `run` cross-checks the async and sync machine; check the result, not accumulated side effects.
- **Rollup — by resource support.** `rollup=True` rolls back the commit of a capable resource; an incapable one → `RollupNotSupportedError`.

The full list is in [Intents and invariants](../reference/intents-and-invariants.md); the terms are in the [Glossary](../reference/glossary.md).

## Summary

The reality around an operation is assembled by two keys: `with_mocks` substitutes by class what the operation resolves (dependencies and resources, reaching the whole tree of nested operations), and `connections=` supplies a `@connection` resource by a string key. Nested operations stay real meanwhile — they are controlled through their dependencies. Rollup continues the resource theme: a run on a live schema with rollback instead of persisting, and a resource incapable of it fails honestly. And `run` additionally cross-checks the async machine against the sync one, so it is worth checking the result, not the accumulated side effects.

Next — **[Context](step-25-context.md)**: how `with_user`, `with_request`, and `with_runtime` assemble `Context` for `@check_roles` and `@context_requires`.

---

## Review questions

1. How does `with_mocks` differ from `connections=` in the addressing method and in what each substitutes?
2. What happens to `box.run(NestedAction)` in a test — does it run for real or get substituted? How, then, do you control the nested operation?
3. Why can a dependency not declared in `@depends` not be substituted?
4. Why does `run` run the operation on two machines, and what practical conclusion follows from this for checks?
5. What does `rollup=True` do for a capable resource, and what for an incapable one?
6. Who declares rollup support, and by which method?

> **Exercise.** In [01_substitution.py](../../examples/step_24_substitution/01_substitution.py) replace the `StockGateway` mock with a `side_effect` that throws an exception, and trace how this shows up in the `CheckoutAction` result (the error surfaces from the nested operation). Then remove `rollup=True` from the fifth test and confirm that the journal now persists the row — this is exactly the difference between the modes.

---

<table width="100%"><tr>
  <td align="left"><a href="step-23-testbench.md">← Step 23 — TestBench</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-25-context.md">Step 25 — Context →</a></td>
</tr></table>
