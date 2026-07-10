<!-- translated-from: authoring-resource_draft.md @ 2026-06-20T20:51:23Z (filesystem mtime; draft is gitignored, no git history) · sha256:3700e5e625ef -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Your own resource

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>

- [When this is needed](#when-this-is-needed)
- [The contract: @meta + get_wrapper_class](#the-contract-meta--get_wrapper_class)
- [Step 1. The manager — pure transport](#step-1-the-manager--pure-transport)
- [Step 2. A wrapper for nested operations](#step-2-a-wrapper-for-nested-operations)
- [Step 3. Wiring to an operation](#step-3-wiring-to-an-operation)
- [Rollup: a run without writing](#rollup-a-run-without-writing)
- [What is important to know](#what-is-important-to-know)
- [Verification](#verification)

---

## When this is needed

A resource is a long-lived **transport** to the external world (a DB, a queue, an API client, a store): open, execute, return. No business rules — decisions live in the operation, the resource answers only "how to fetch". To add a new data source behind the same contract, subclass `BaseResource`. The whole concept — [Step 19 — Resource](../tutorials/step-19-resource.md); here is how to write your own.

The full example: [06_custom_resource.py](../../examples/how_to/06_custom_resource.py).

## The contract: @meta + get_wrapper_class

`BaseResource` (`from aoa.action_machine.resources.base_resource import BaseResource`) requires two things:

- **`@meta(description=, domain=)`** — mandatory (via `MetaIntent`); without it the graph build fails;
- **`get_wrapper_class() -> type[BaseResource] | None`** — the single abstract method (see [Step 2](#step-2-a-wrapper-for-nested-operations)).

Plus, optionally, `async check_rollup_support() -> bool` (raises `RollupNotSupportedError` by default; see [Rollup](#rollup-a-run-without-writing)). The transport methods themselves (`execute`, `fetch`, `send`, anything) are yours: aspects call them via `connections["key"]`.

## Step 1. The manager — pure transport

The manager owns the connection and the operations over it. Here is an in-memory "ledger" with a transaction:

```python
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.intents.meta import meta

@meta(description="In-memory ledger (transport only)", domain=LedgerDomain)
class LedgerResource(BaseResource):
    def __init__(self) -> None:
        self._entries: list[str] = []

    def get_wrapper_class(self) -> type[BaseResource] | None:
        return LedgerWrapper                 # nested operations get the blocking proxy

    async def open(self) -> None:    self._entries = []
    async def execute(self, entry: str) -> int:
        self._entries.append(entry); return len(self._entries)
    async def commit(self) -> None:  ...     # commit
    async def rollback(self) -> None: self._entries = []
```

## Step 2. A wrapper for nested operations

This is what distinguishes an AOA resource from "a class with methods". When a resource is propagated into a **nested** operation (through `box.run`), the machine substitutes it with `get_wrapper_class()(...)` — so the child code can **use** the resource but not **control** its transaction (the transaction belongs to the root operation). Three forms:

| `get_wrapper_class()` | When | Wrapper behavior |
|---|---|---|
| `None` | a simple non-transactional resource | direct pass-through (as in [Step 19](../tutorials/step-19-resource.md)) |
| a **delegating** wrapper | holds a client/handle (API, SDK) | passes the same `service` deeper, no lifecycle |
| a **blocking** wrapper | a transactional resource | delegates `execute`, but `open/begin/commit/rollback` → `TransactionProhibitedError` |

A blocking wrapper is also a `BaseResource` with `@meta`; its `get_wrapper_class()` returns itself (the guarantee holds at any depth):

```python
from aoa.action_machine.exceptions import TransactionProhibitedError

@meta(description="Ledger handle for nested actions", domain=LedgerDomain)
class LedgerWrapper(BaseResource):
    def __init__(self, inner): self._inner = inner
    def get_wrapper_class(self): return LedgerWrapper
    async def execute(self, entry): return await self._inner.execute(entry)   # executing — allowed
    async def commit(self):  raise TransactionProhibitedError("nested cannot commit")
    async def rollback(self): raise TransactionProhibitedError("nested cannot rollback")
    # open / begin — likewise
```

The canonical SQL stack (Protocol → manager → wrapper) and its delegating variant are covered in the [PostgreSQL extension](../extensions/postgresql.md).

## Step 3. Wiring to an operation

A resource is declared on an operation via [`@connection`](../tutorials/step-17-connections.md) and supplied in `connections`; the aspect reads it by key:

```python
from aoa.action_machine.intents.connection import connection

@meta(description="Post a ledger entry", domain=LedgerDomain)
@check_roles(GuestRole)
@connection(LedgerResource, key="ledger")
class PostEntryAction(BaseAction[PostParams, PostResult]):
    @summary_aspect("Post entry")
    async def post_summary(self, params, state, box, connections):
        count = await connections["ledger"].execute(params.entry)
        return PostResult(count=count)

# machine.run(ctx, PostEntryAction(), params, {"ledger": LedgerResource()})
```

An alternative — `@depends` + `await box.resolve(LedgerResource)`, when the resource is built by the dependency factory ([Step 6 — Dependencies](../tutorials/step-06-dependencies.md)).

## Rollup: a run without writing

If a resource is transactional, it can be made fit for a run against the production schema without saving: override `check_rollup_support()` → `True`, and in `commit()`, when `rollup=True`, perform a **rollback instead of writing**. Then the operation can be [tested](../tutorials/step-24-substitution.md) against the real DB constraints while saving nothing. With `rollup=True` the dependency factory itself calls `check_rollup_support()` and fails on resources without support.

## What is important to know

- **Transport, not decisions.** There must be no business `if` in a resource — only "how to fetch". The decision of what to do with the data is in the operation; that is why an operation is tested by **swapping the resource**.
- **`@meta` is mandatory**, the name is up to you (the `Resource` suffix is a convention, not a runtime requirement; unlike `Action`/`Entity`).
- **The runtime substitutes the wrapper**, not you: in `tools_box` on `box.run`, `get_wrapper_class()` is taken. You only decide what guarantee it gives (None / delegation / blocking).
- **`check_rollup_support()` raises by default** with `RollupNotSupportedError` — a deliberate fail-fast: a resource that cannot roll back must not silently "support" rollup.

## Verification

```bash
uv run python examples/how_to/06_custom_resource.py
```

```text
root: posted entry, count=1, committed=['debit 100']
nested: execute -> 2
nested: commit refused -> TransactionProhibitedError
```

The root operation executed and committed an entry; the wrapper (what a nested operation would receive) allowed `execute` but refused `commit`. The whole resource concept, with review questions — [Step 19 — Resource](../tutorials/step-19-resource.md).

---

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>
