# Contract: the SQL resource after this change

**Feature**: `specs/007-sql-contract-driver-helpers/spec.md` · **Date**: 2026-10-17

This contract fixes what the structural type, the base resource and the driver are obliged to answer once the
generic query member has left. It is normative for the implementation tasks: a member listed as a member MUST exist,
a member listed as removed MUST NOT exist anywhere on the shape, and the prose that names the members is part of the
shape (constitution, principle III).

## 1. The four shapes, before and after

| Shape | Members before | Members after |
| --- | --- | --- |
| `ProtocolSqlResource` (`protocol_sql_resource.py`) | `rollup`, `open`, `begin`, `commit`, `rollback`, `close`, `execute` | `rollup`, `open`, `begin`, `commit`, `rollback`, `close` |
| `SqlResource` (`sql_resource.py`) | `rollup`, `check_rollup_support`, `get_wrapper_class`, `open`\*, `begin`\*, `commit`, `rollback`\*, `close`, `execute`\* | the same without `execute`; `open`, `begin`, `rollback` remain abstract |
| `WrapperSqlResource` (`wrapper_sql_resource.py`) | `rollup`, `check_rollup_support`, `get_wrapper_class`, `open`†, `begin`†, `commit`†, `rollback`†, `close`†, `__aenter__`†, `__aexit__`†, `execute` | the same without `execute` |
| `PostgresResource` (`postgres_resource.py`) | `open`, `begin`, `commit`, `rollback`, `close`, `execute` | `open`, `begin`, `commit`, `rollback`, `close`, `_execute`, `_fetchrow`, `_require_connection` |

\* abstract · † refuses with `TransactionProhibitedError`

**SR-1.1** `execute` MUST NOT be a member of any of the four shapes, in any case or by any alias, and MUST NOT be
reachable on any of them through attribute access.

**SR-1.2** A SQL resource subclass MUST be instantiable while implementing `open`, `begin` and `rollback` only;
`commit` comes from the base, `close` has a harmless concrete body (from `#215`), and no fourth abstract member
exists.

**SR-1.3** The prose bound to each shape MUST name the same members the shape has: the module title and its
`PURPOSE` section, the contract line in `sql_resource.py` (`:11`), the AI-CORE `CONTRACT` key of the structural type
(`protocol_sql_resource.py:43`), the diagram in `sql_resource.py`, the diagram and one-line description in
`wrapper_sql_resource.py` (`:13`, `:38`), and the diagram in `postgres_resource.py` (`:32`).

**SR-1.4** The rollup walk-through in `sql_resource.py` (`:52-53`), which today writes statements through the
removed member, MUST be rewritten so that it does not teach a member that does not exist.

## 2. What the structural type promises

**SR-2.1** The type MUST remain `@runtime_checkable`, so that `isinstance(resource, ProtocolSqlResource)` keeps
working for the framework and for the tests.

**SR-2.2** Membership MUST be exactly the six members of the table above; a shape that supplies them (including the
proxy) satisfies the type, and one that is missing any of them does not.

**SR-2.3** `close` MUST carry a concrete harmless body on the base, so that a resource holding no connection — the
eight demo stubs, the test doubles — answers it without an edit and without a side effect (this is the `#215`
behaviour, restated because the tests assert it).

## 3. What the base resource promises

**SR-3.1** `commit` on the base MUST keep its rollup behaviour: with `rollup=True` it performs `rollback` instead of
a real commit, and it clears the transaction state through `rollback`.

**SR-3.2** `check_rollup_support()` MUST keep answering `True`, so descendants remain rollup-capable unless they
break the contract deliberately.

**SR-3.3** `get_wrapper_class()` MUST keep answering `WrapperSqlResource`, which is the safe default for a resource
that has nothing of its own to hand a nested action.

## 4. What the driver promises

**SR-4.1** The driver MUST keep the construction and lifecycle contract of `#215` unchanged: exactly one of
`connection_params` and `pool` (both or neither raises `ConnectionValidationError` in the constructor), the
connection taken in `open()` and given back in `close()`, `close()` idempotent and silent when it holds nothing, and
a transaction still open at closing ended by the resource, the connection returned, and then reported as
`TransactionLeftOpenError`.

**SR-4.2** The driver MUST answer the two protected helpers of [driver-helpers.md](./driver-helpers.md) and the one
check they share.

**SR-4.3** The driver MUST NOT publish a public query member, and MUST NOT re-export one through the `postgres`
package's `__init__` or through `sql/__init__.py` (`sql/__init__.py` exports `PoolProtocol`, `ProtocolSqlResource`,
`SqlResource`, `WrapperSqlResource` and MUST keep exactly those).

## 5. The subclasses in this repository

| Subclass | Where | What this contract means for it |
| --- | --- | --- |
| The eight demo stubs | `packages/aoa-demo/src/aoa/demo/model/{catalog,messaging,billing,store}/resources/*.py` | lose the member and the `Any` import that existed only for it; no other edit |
| `IdentityStoreStub` | `packages/aoa-demo/src/aoa/demo/model/identity/resources/identity_store_stub.py` | loses the member **and** the statement-text test its body needed; implements the domain's two primitives instead |
| `IdentityStore` (+ `IdentityStoreBase`) | `.../identity/resources/identity_store.py`, `identity_store_base.py` | implements the primitives through the protected helpers; `record_login` stops calling the removed member |
| `OcelStoreResource`, `OcelStoreWrapper` | `packages/aoa-ocel/**` | **not** a SQL resource — it implements its own protocol and keeps its own members; cited as the domain-wrapper pattern, not migrated (`FR-024`) |
| Test doubles | `packages/aoa-action-machine/tests/**` | lose the member; the incomplete-subclass case for it is deleted |

## 6. What the contract deliberately does not say

- **Nothing about how a statement is written.** The contract is a lifecycle plus rollup; a resource that wants a
  public query surface publishes its own member, with its own name and its own return type, and the framework
  neither requires nor forbids it.
- **Nothing about transactions in a helper.** `begin`/`commit`/`rollback` remain the only transaction surface, and
  a helper call outside them is the domain's own choice.
- **Nothing about the driver's types below the driver.** `asyncpg.Record` appears in the driver's protected signature
  and stops at the demo's PostgreSQL store, which converts it to a plain mapping.
- **No compatibility surface.** There is no alias, no deprecation window and no shim: a resource outside this
  repository that called the removed member breaks at the next type check, and the changelog is where it learns what
  replaced it.
