<!-- translated-from: step-06-dependencies_draft.md @ 2026-06-17T17:53:37Z · sha256:10c84ce48bc1 -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Step 06 — Dependencies

<table width="100%"><tr>
  <td align="left"><a href="step-05-error-handling.md">← Step 05 — Explicit error handling</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-07-context.md">Step 07 — Context →</a></td>
</tr></table>

- [Dependencies in the header](#dependencies-in-the-header)
- [Declare and obtain](#declare-and-obtain)
- [A contract, not a container](#a-contract-not-a-container)
- [An already-open resource](#an-already-open-resource)
- [A proxy in a nested call](#a-proxy-in-a-nested-call)
- [depends or connection](#depends-or-connection)
- [Invariants](#invariants)
- [Review questions](#review-questions)

---

In ordinary code dependencies come from anywhere. Through the constructor — and the object acquires state between calls. Through method parameters — and signatures swell. Through an IoC container — and the real composition hides in YAML. Through a factory — and from the outside it is invisible what it creates. Every way pays in readability, and they all share one trouble: **a hidden dependency is a hidden cause of changing behavior**. To learn what an operation actually touches, you have to read its whole body.

AOA does it differently: an operation declares everything external **in the header**, and cannot obtain it without declaring it. There are two kinds. `@depends` — a dependency the machine creates on demand (a service, a repository, a nested operation); the aspect takes it via `await box.resolve(...)`. `@connection` — an already-open resource the operation expects to receive at launch (a connection, a pool, a client); the aspect reads it from `connections["key"]`. Both are visible to the reader, the reviewer, the test, and the system graph.

[▶ Try in Colab](https://drive.google.com/file/d/1XS2XyVnHdJJwy3YA-Pm0R4XWSZ1m8iXZ/view?usp=drive_link) · [Open in project](../../examples/step_06_dependencies/01_depends.py)

---

## Dependencies in the header

An operation's header is its contract with the environment. `@depends(PricingService)` says: "I need this service"; `@connection(LedgerResource, key="ledger")` — "I will be handed this open resource under the key `ledger`". What is not declared is not available.

```python
@meta(description="Charge for a product", domain=BillingDomain)
@check_roles(NoneRole)
@depends(PricingService)
@connection(LedgerResource, key="ledger")
class ChargeAction(BaseAction[ChargeParams, ChargeResult]):
    ...
```

## Declare and obtain

A dependency declared through `@depends` is obtained by the aspect with a call to `await box.resolve(...)`:

```python
@regular_aspect("Compute total via the pricing service")
@result_float("total", required=True, min_value=0)
async def price_aspect(self, params, state, box, connections):
    pricing = await box.resolve(PricingService)      # declared in @depends
    return {"total": pricing.price(params.sku) * params.qty}
```

`box.resolve(PricingService)` works only because `PricingService` is declared in `@depends`. Ask for something undeclared and the machine refuses: the dependency factory knows only what is written in the header. Each `resolve` builds a fresh instance (the factory does not cache); if a dependency must be single for the whole call and carry state — its place is `@connection`, not `@depends`.

> `box.resolve` is asynchronous: always `await box.resolve(...)`.

For dependencies that are **operations**, `@depends` has a `mode` parameter: `UseCase.include` (the operation must run in this session — a verifiable contract, see [Intents and invariants](../reference/intents-and-invariants.md)) or `UseCase.extend` (it may run, or it may not). For resources `mode` is not specified.

## A contract, not a container

In most frameworks DI is a container: modules, bindings, providers, configuration. AOA looks at it more simply: DI is a contract between the operation and the infrastructure. The operation says "I need this", the machine provides. No modules and no providers — only the `@depends` decorator and, optionally, a factory (`factory=`). Simple, predictable, testable: in a test the dependency is substituted without untangling a container (see [Testing](../index.md#v-testing)).

## An already-open resource

Not everything is created by a factory. A transaction, a connection pool, an HTTP client, a store — these are already-open resources that operations **receive** rather than construct. For them there is `@connection`: it declares a slot with a key, and the connections are supplied to `machine.run(...)` as a `connections` dictionary.

```python
machine.run(Context(), ChargeAction(), params, connections={"ledger": ledger})
```

The aspect reads the resource by key: `connections["ledger"]`. The machine checks the declared slots against the supplied ones **before** launching the aspects: an extra key, a missing key, or a value that is not a `BaseResource` is an error right at the entrance. This is part of the same grammar: an operation will not receive a connection it did not declare, and will not run without a declared one.

## A proxy in a nested call

Operations call one another through `await box.run(ChildAction, params)` — this is [composition](step-01-action-and-pipeline.md), not inheritance. When a parent passes its connection to a child operation, the machine **wraps it in a proxy**: the child operation can run statements but cannot control the transaction. The transaction belongs to whoever opened it; otherwise a nested call could commit or roll back data it does not own.

```python
@regular_aspect("Record to ledger and call nested action")
async def record_aspect(self, params, state, box, connections):
    ledger = connections["ledger"]
    await ledger.execute(f"charge {params.sku} = {state['total']}")   # the owner writes
    await box.run(                                                     # ledger is proxied
        AppendEntryAction,
        EntryParams(entry=f"audit:{params.sku}"),
        connections={"ledger": ledger},
    )
    return {"total": state["total"]}
```

The child `AppendEntryAction` receives not the `ledger` itself but its proxy: `execute` passes, while `commit`/`rollback` raise `TransactionProhibitedError`. Only the parent can commit the transaction — in its `summary`.

**Run:**

```bash
uv run python examples/step_06_dependencies/01_depends.py
```

**Output:**

```text
  parent: total=17980.0
  [ledger] execute: charge sku-1 = 17980.0
  [ledger] execute: audit:sku-1
      child: commit blocked (owns no transaction)
  [ledger] COMMIT (2 rows)

Result: sku=sku-1, total=17980.0
```

The whole path is visible: the parent computed the price via `box.resolve`, wrote to the `ledger`, called the child operation (which wrote through the proxy, but had its `commit` blocked), and only the owner committed the transaction. The proxy is preserved at deeper levels too — the prohibition is not lost with further nesting.

*(In the example `PricingService` and `LedgerResource` carry `@meta(description=…, domain=…)` — like any resources in the system graph; the `LedgerProxy` is marked `@exclude_graph_model` as infrastructure. More on resources is in the [Data model](../index.md#iv-data-model) part.)*

## depends or connection

The split is simple:

- **`@depends`** — the machine **creates** the dependency on demand through `box.resolve`. Suitable for services and repositories that can be assembled on the spot, and for nested operations (`box.run`).
- **`@connection`** — the operation **receives** an already-open resource under a key from `connections`. Suitable for everything that holds a live connection or transaction and must be passed, not recreated.

Both are about the boundary with the external world (which is implemented by [resources](../index.md#iv-data-model)); both are declared in the header and checked by the machine.

## Invariants

- **Only the declared.** `box.resolve(T)` works if and only if `T` is declared in `@depends`; otherwise — `ValueError`.
- **A fresh instance.** Each `resolve` builds a new object (the factory does not cache); shared state — through `@connection`.
- **Connections contract.** The declared `@connection` keys and those passed to `machine.run` are checked before the aspects launch: an extra/missing key or a non-`BaseResource` is an error at the entrance.
- **A proxy in nesting.** A connection passed to a child operation is wrapped in a proxy: `execute` is allowed, `commit`/`rollback` — `TransactionProhibitedError`. The prohibition holds at any depth.
- **Operation modes.** `@depends` on an operation requires `mode` (`include`/`extend`); on a resource — no `mode`.
- **DI is a contract, not a container.** No modules, no bindings; only the header and the factory.

The full list is in [Intents and invariants](../reference/intents-and-invariants.md); the terms are in the [Glossary](../reference/glossary.md). Why dependencies are moved into the header is in the [Philosophy](../explanation/philosophy.md).

## Summary

An operation declares everything external in the header and does not obtain it without a declaration. `@depends` + `await box.resolve` — for what the machine creates; `@connection` + `connections["key"]` — for already-open resources passed to `machine.run`. On a nested `box.run` the connection is proxied: the nested operation runs statements but does not control someone else's transaction. Dependencies stop being a hidden cause of behavior and become a visible, verifiable part of the contract.

Next — **[Context](../index.md#ii-business-logic)**: the same principle of explicitness applied to the call environment — `@context_requires` and the context slice.

---

## Review questions

1. Why is "a hidden dependency a hidden cause of changing behavior"? What does moving dependencies into the header change?
2. How does `@depends` differ from `@connection`? When do you choose which?
3. What does `box.resolve(X)` return if `X` is not declared in `@depends`? Why is this useful?
4. `box.resolve` creates a new instance on each call. Where, then, should shared state for the whole operation call be kept?
5. Why is a connection passed to a nested operation wrapped in a proxy? What exactly does it forbid and what does it allow?
6. At what moment is the correspondence between declared and supplied `@connection` keys checked?
7. How does "DI as a contract" differ from "DI as a container"? What does AOA deliberately NOT do?

> **Exercise.** Add a second dependency to `ChargeAction` through `@depends` — for example, `TaxService` (also a resource) — and use it in `price_aspect` to account for tax. Then in the nested `AppendEntryAction` try calling `rollback` instead of `commit` and confirm the proxy blocks it too. What happens if you remove `@connection(LedgerResource, key="ledger")` from the header but still pass `connections={"ledger": ...}` to `machine.run`?

---

<table width="100%"><tr>
  <td align="left"><a href="step-05-error-handling.md">← Step 05 — Explicit error handling</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-07-context.md">Step 07 — Context →</a></td>
</tr></table>
