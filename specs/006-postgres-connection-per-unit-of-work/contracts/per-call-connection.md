# Contract: the per-call declaration and its lifecycle

**Feature**: `specs/006-postgres-connection-per-unit-of-work` · **Date**: 2026-10-16

The surface a reader must be able to check without reading the implementation: what a per-call
declaration is made of, what validates it, and what the boundary does with it. Module:
`packages/aoa-action-machine/src/aoa/action_machine/resources/per_call_connection.py`; the new
context manager lives beside it in `resources/connection_scope.py`.

---

## 1. The declaration

```python
@dataclass(frozen=True)
class PerCallConnection:
    factory: Callable[[], BaseResource]
    finalize: Callable[[BaseResource], Awaitable[None] | None]
```

- **PC-1.1** Two fields, in this order. `factory` stays first so keyword call sites keep working;
  `finalize` is second and mandatory (FR-014, binding decision).
- **PC-1.2** `factory` is called on every resolution and must return a `BaseResource` (FR-014;
  `resolve_connections:89-93`).
- **PC-1.3** `finalize` accepts the resource the factory returned and may be synchronous or
  asynchronous — it returns either nothing or an awaitable of nothing (FR-015).

## 2. Validation — `validate_connection_entries(connections)`

Unchanged signature; it still does not call the factory or the finalizer (`per_call_connection.py:28-58`).

| Input | Answer |
| --- | --- |
| `None` | returns, no error |
| a key that is not a non-empty `str` | `TypeError("Connection key must be a non-empty string.")` |
| a duplicate key | `ValueError("Duplicate connection key: …")` |
| an entry that is a `BaseResource` | accepted |
| a `PerCallConnection` whose `factory` is not callable | `TypeError("PerCallConnection.factory must be callable.")` |
| a `PerCallConnection` whose `finalize` is not callable | `TypeError("PerCallConnection.finalize must be callable.")` — new |
| anything else | `TypeError("Connection value must be a BaseResource or PerCallConnection, …")` |

- **PC-2.1** A missing `finalize` never reaches this function: the frozen dataclass raises
  `TypeError` for the absent required field when the declaration is constructed (FR-014).

## 3. Resolution — `resolve_connections(connections)`

- **PC-3.1** Signature and return type unchanged: `Mapping[str, ConnectionValue] | None` →
  `dict[str, BaseResource] | None`; a falsy input returns `None` (FR-022). Each `PerCallConnection`
  calls `factory()` once, on this resolution; a ready resource is passed through as itself
  (FR-014, FR-019).
- **PC-3.2** A factory that returns a non-`BaseResource` raises
  `TypeError("PerCallConnection factory for key … must return BaseResource, …")` (unchanged). The
  function is not the boundary: it does not open, close or finalize anything.

## 4. `connection_scope` — the lifecycle

In `aoa/action_machine/resources/connection_scope.py` (new module beside `per_call_connection.py`).

```python
@asynccontextmanager
async def connection_scope(
    connections: Mapping[str, ConnectionValue] | None,
) -> AsyncIterator[dict[str, BaseResource] | None]: ...
```

**Algorithm, exactly** (FR-016 to FR-021). The scope does **not** call `resolve_connections`; it walks
the declaration itself, entry by entry, because it must know — per entry — whether the framework
created the resource, and it must not lose the resources created before a later factory fails:

1. For each entry of the declaration mapping, in declaration order:
   - a ready `BaseResource` → put it into the yielded mapping untouched; it has no finalizer, and the
     scope never opens or closes it (FR-019);
   - a `PerCallConnection` → call `factory()` now, record `(key, resource, finalize)` in a created
     list, and if the resource has an `open` attribute, `await resource.open()` and mark it opened
     (FR-016, FR-018). A resource without `open` is recorded but not opened.
   A `factory()` that raises stops the walk; the entries already recorded stay on the created list and
   are finalized in step 3 (FR-021).
2. `yield` the mapping — ready resources and created resources together — to the caller's block,
   which is `machine.run(...)`. The run receives only this mapping (FR-022).
3. In a `finally`, finalize exactly once every created entry: **the opened ones first, then the ones
   whose `open` was never reached or itself failed**, each group in declaration order (FR-017,
   FR-021). Await the result when it is awaitable (FR-015). Every remaining finalizer still runs after
   one of them raises.
4. If an `open()` in step 1 raised, step 3 runs and then the original exception propagates (FR-021).

- **PC-4.1** The context manager opens and closes **only what a per-call declaration created**. A
  ready resource is yielded untouched and never finalized by it (FR-019) — this is the point where a
  flattened resolve would go wrong, since `resolve_connections` deliberately merges the two kinds.
- **PC-4.2** No entry is finalized twice, on any path (FR-017, SC-008).
- **PC-4.3** Cancellation. Step 3 runs when the block was cancelled. Because a pending cancellation
  would re-raise at the first suspension, each finalize await is shielded (`asyncio.shield`) so the
  release actually completes, and the `CancelledError` is re-raised afterwards (FR-017, SC-008).


## 5. Error precedence

The rule: a closing failure never replaces the failure of the run (FR-020, SC-009).

| Run | Finalizer | What the caller sees |
| --- | --- | --- |
| raises `E` | raises `F` | `E`; `F` is recorded and does not mask it |
| raises `E` | succeeds | `E` |
| succeeds | raises `F` | `F` surfaces |
| succeeds | succeeds | the run's result |
| cancelled | anything | cancellation still propagates; the finalizer ran exactly once (FR-017) |

- **PC-5.1** "Recorded" is concrete and applies to **operational** closing failures only: such a
  failure is appended to the exception that is already propagating, with `BaseException.add_note` —
  available on this repository's Python 3.12 — so it is observable in the traceback without becoming
  the raised exception (FR-020, SC-009). Nothing is silently dropped.
- **PC-5.1a** A **contract violation** is not recorded, it is raised. A finalize that raises
  `ResourceContractViolationError` — today, `TransactionLeftOpenError` from a close that found a
  transaction open — makes that error the one the caller sees, even when the run had already failed;
  the run's error is attached as its cause (`raise violation from run_error`), so nothing is lost and
  the violation is never demoted to a note (FR-044, SC-023). The scope recognises the family rather
  than one concrete class, so a future contract violation inherits the rule.
- **PC-5.2** The precedence holds per resource and across the call: a later resource's failure does
  not hide an earlier exception either, and a failing finalizer does not stop the remaining ones.
- **PC-5.3** A `factory()` that raises produces no resource, so there is nothing to finalize for that
  entry: the exception propagates and the entries already created are still finalized (FR-021).
  "Exactly once" means once per resource that was created, not once per declaration.
- **PC-5.4** A finalizer that raises **after cleaning up** is the shape this feature creates:
  `PostgresResource.close()` rolls back a transaction it finds open, returns the connection to the
  pool, and then raises `TransactionLeftOpenError` (FR-044, contracts/sql-resource.md SR-2.5). Both
  the precedence rule and the violation rule therefore hold with the connection already back in the
  pool — neither path costs a connection.
- **PC-5.5** Cancellation is the single exception to PC-5.1a: when the task serving the call is being
  cancelled, `CancelledError` propagates and the violation is recorded beside it. Replacing a
  cancellation with another error would break `asyncio`'s own contract for the task — a timeout or a
  cancelled request must stay a cancellation (FR-044).

## 6. What a caller of `machine.run` still sees

- **PC-6.1** `machine.run` receives `dict[str, BaseResource] | None`, exactly as today (FR-022); it
  learns nothing about factories, finalizers or the context manager.
- **PC-6.2** The adapters hold the declarations and the finalizers; the machine holds neither
  (FR-017, FR-022).

## 7. Call sites that must migrate

The **five** one-argument declarations in the test suite and the **one** in the example script must
pass a finalizer (FR-041, SC-018):

| File | Line | Today | After |
| --- | --- | --- | --- |
| `packages/aoa-fastapi-adapter/tests/test_fastapi_endpoints.py` | 200 | `PerCallConnection(factory)` | `PerCallConnection(factory, finalize)` |
| `packages/aoa-action-machine/tests/action_machine/resources/test_resolve_connections.py` | 37 | `PerCallConnection(factory)` | `PerCallConnection(factory, finalize)` |
| same | 56 | `PerCallConnection(lambda: "bad")` | add a finalizer; the factory's bad return is still the point |
| same | 88 | `PerCallConnection(factory=123)` | `PerCallConnection(factory=123, finalize=…)`; the non-callable factory is still the point |
| `packages/aoa-mcp-adapter/tests/test_mcp_handler.py` | 756 | `PerCallConnection(factory=factory)` | `PerCallConnection(factory=factory, finalize=…)` |
| `examples/step_17_connections/01_connections.py` | 96 | `PerCallConnection(factory=factory)` | `PerCallConnection(factory=factory, finalize=…)` |

No test and no example may be left constructing a per-call declaration with one argument (FR-041,
SC-013, SC-018).
