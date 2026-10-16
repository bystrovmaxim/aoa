# Phase 1 — Quickstart: One connection per unit of work, and one pool for the process

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Branch**: `feature/issue-215-postgres-connection-per-unit-of-work` · **Date**: 2026-10-16

How to convince yourself, in this order, that `PostgresResource` now holds one connection for the
length of one unit of work, that the process keeps one pool for its whole life, and that a resource
created per call cannot be declared without saying how it is closed. Every command runs from the
repository root. **No database is required and no check in this feature needs one**: tests reach a
fake pool and a fake connection through the `pool=` keyword (`packages/aoa-action-machine/tests/support/fake_pool.py`), and the same
harness stands in for the driver everywhere else; nothing below needs network access.

Acceptance is measured against the existing suite, so run the baseline first.

## 0. Prerequisites

Python 3.12, `uv`, and the repository's own workspace environment — the same one
`scripts/run_checks_with_log.sh` uses. The per-package suites set `testpaths = ["tests"]`,
`asyncio_mode = "auto"` and `pythonpath = ["src"]`, so they run from the root by path.

```bash
uv sync
uv run pytest packages/aoa-action-machine/tests packages/aoa-fastapi-adapter/tests packages/aoa-mcp-adapter/tests -q
```

**Expected before the change**: green. Record the passed count; the change may add cases and migrate
four declarations, not break an existing one (SC-013).

## 1. First, prove the defect is caught

The old resource opened one connection for the process and kept it in `self._conn`, so a second
concurrent operation raised the driver's `InterfaceError: another operation is in progress`. **The
harness must reproduce the driver's one-operation-at-a-time rule, or the concurrency test is green in
both states and proves nothing** (FR-042, SC-019).

```bash
uv run pytest packages/aoa-action-machine/tests/action_machine/resources/test_resource_unit_of_work.py -q -k "concurrent"
```

**Expected GREEN on the new code**: 30 concurrent calls under one declaration all succeed, and 0
failures carry `another operation is in progress` (SC-001); the same with a pool-backed resource is
green too, so correctness does not depend on the pool, and two concurrent transactions run their own
`BEGIN` … `COMMIT` with 0 interleaved statements and 0 rows committed by the wrong owner (FR-002,
FR-003, SC-002, SC-003). A run that raises and a run that is cancelled both release their connection
(FR-017, SC-004).

For the RED there is no historical checkout to run: the old resource had no `pool=` parameter, so a
pool-injected test cannot execute against it at all. The red is produced the way the constitution
describes verification — the **adversarial break** (FR-043): with the new test in place, break the
implementation the way the test must catch. The sharpest break is to make every resource share one
connection — a module-level connection handed out by `open()`, or a fake pool whose `acquire` always
returns the same connection — then run the command above. **Expected RED**: exactly the concurrency
case fails with the one-operation-at-a-time error and no other check newly fails; remove the break
and re-run green. Record both directions (SC-019).

## 2. The pool: ceiling, timeout, borrow and return

```bash
uv run pytest packages/aoa-action-machine/tests/action_machine/resources/test_pool_bounds.py -q -k "pool or exhaust"
```

**Expected**: with a stated `max_size=2` and 3 concurrent calls, at most 2 connections are held at
once and the third completes after the others release theirs (FR-011, SC-006). With a wait timeout
and a connection that never frees, the wait ends in a **named failure** rather than hanging (FR-009,
FR-010, SC-006). Closing a pool-backed resource returns the connection and leaves the pool open; a
resource that owns its connection closes it; one built without a pool never reaches one; 0
connections are left unreturned across successful, raising and cancelled runs (FR-006, FR-007,
SC-004, SC-005).

## 3. The pool is created once and closed once

```bash
uv run pytest packages/aoa-action-machine/tests/action_machine/resources/test_connection_scope.py -q -k "scope"
uv run pytest packages/aoa-fastapi-adapter/tests/test_adapter_lifespan.py -q
uv run pytest packages/aoa-mcp-adapter/tests/test_adapter_lifespan.py -q
uv run pytest packages/aoa-demo/tests/test_identity_postgres.py -q -k "holder or pool"
grep -rn "asyncpg\|create_pool\|Postgres\|dsn" packages/aoa-fastapi-adapter/src packages/aoa-mcp-adapter/src --include=*.py
```

**Expected**: exactly one pool is created at startup and closed exactly once at shutdown; reading the
holder before it is filled raises a named failure, not an attribute error (FR-008, FR-012, FR-013,
SC-005). Both adapters gain the same one general lifecycle option — one asynchronous context
manager, run at startup and closed at shutdown — and their sources name no database and no driver:
the `grep` finds 0 occurrences and exits 1 with no output (SC-021). It deliberately does **not**
search for the word `connection`: the adapters resolve connections and legitimately import
`ConnectionValue`, so that search would always match (the spec's SC-021 states why the check is
written against driver names). The holder itself lives in the demo, not in the machine.

## 4. The per-call pair: once, never masking, and rejected without it

```bash
uv run pytest packages/aoa-action-machine/tests/action_machine/resources/test_connection_scope.py packages/aoa-action-machine/tests/action_machine/resources/test_resolve_connections.py -q -k "finaliz or mask or precedence or reject or construct or callable"
```

**Expected**: the finalizer runs exactly once on success, on exception and on cancellation
(SC-008); a lifecycle-free resource declared per call still gets its finalizer once, opened by
nobody (FR-018); when opening a later resource fails, the already-opened ones are still finalized
(FR-021). On a failed run the run's own error reaches the caller; on an otherwise successful run the
closing failure surfaces — both 100 % (FR-020, SC-009). A declaration with no finalizer raises
`TypeError` at construction, a non-callable one is rejected with `PerCallConnection.finalize must be
callable.`, and a resource built with both a description and a pool, or with neither, raises
`ConnectionValidationError` from the constructor (FR-005, FR-014, SC-007).

## 5. Contract, wrapper, stubs and migrated call sites

```bash
uv run pytest packages/aoa-action-machine/tests/action_machine/resources/test_sql_resource.py packages/aoa-action-machine/tests/action_machine/resources/test_wrapper_sql_resource.py -q
uv run pytest packages/aoa-demo/tests/test_sql_resource_stubs.py -q
uv run pytest packages/aoa-action-machine/tests/action_machine/resources/test_resolve_connections.py packages/aoa-fastapi-adapter/tests/test_fastapi_endpoints.py packages/aoa-mcp-adapter/tests/test_mcp_handler.py -q
grep -rn "PerCallConnection(" packages examples docs
git diff --stat -- 'packages/aoa-demo/src/aoa/demo/model'
```

**Expected**: `close()` is a concrete harmless default; a resource holding no connection closes
without error; opening and closing again are safe (FR-006, FR-023, SC-010). The proxy refuses
`close`, `open`, `begin`, `commit`, `rollback` and context-manager use with
`TransactionProhibitedError`, exposes no `acquire`, and still satisfies `ProtocolSqlResource`
(FR-024, SC-011); a `rollup=True` run still rolls back (FR-027). The four existing per-call
declarations are migrated to the two-argument pair; every `PerCallConnection(` call site passes a
factory **and** a finalizer, with 0 single-argument constructions left (FR-041, SC-013, SC-018); the
eight demo stubs show no diff (FR-023, SC-012).

## 6. The examples and the demo

```bash
uv run python examples/step_17_connections/01_connections.py
uv run python examples/step_19_resource/01_resource.py
uv run pytest tests/examples/test_examples_run.py -q -k "step_17_connections or step_19_resource"
uv run pytest tests/examples/test_examples_run.py -q
uv run python -c "from importlib.metadata import requires; print('\n'.join(r for r in (requires('aoa-demo') or []) if 'asyncpg' in r or 'postgres' in r))"
uv run pytest packages/aoa-demo/tests -q
```

**Expected**: both scripts exit 0 with no live database and print the new pool-backed per-call case —
both the factory and the finalizer — beside the existing modes (FR-034, FR-035, SC-014). The runner
executes every `examples/**/*.py` with `sys.executable`, the repository root as cwd and a 60-second
timeout, asserts `returncode == 0`, and prints the script's stdout and stderr on failure; the four
known-broken LangGraph scripts stay strict `xfail`s and the whole-file run is green.

**For the demo**, `asyncpg` appears only inside the `postgres` extra's marker, so it imports with
the extra absent (FR-037). Its suite is green with no DSN and no PostgreSQL running, answering
through a connection stub and creating no pool; with the connection description the demo's own
README names supplied it is green too, and the identity domain's concurrency,
transaction-isolation, finalization and shutdown-pool-closure cases pass — still with no live server,
because the harness stands in for the driver (FR-036, FR-038, SC-015).

## 7. The documentation

```bash
grep -n "finaliz" docs/tutorials/step-17-connections.md
grep -n "^## \|^|" docs/tutorials/step-17-connections.md
grep -rn "no shared state\|a fresh resource is born\|fresh per request" docs packages
grep -rn "asyncpg.connect" packages/aoa-action-machine/src docs examples
```

**Expected**: the mode-2 section names the mandatory pair — the factory creates, the finalizer
closes, synchronous or asynchronous, after the run on success, exception and cancellation (FR-029);
the new section after "What to choose" carries the holder, the startup hook, the route, the resource
and the **three-case table** of who opens and who closes (FR-030, SC-020). The stale claims return 0
hits (FR-039, SC-016), and `asyncpg.connect` appears only where a connection is opened, never in a
route, a setup or at import; the Postgres and resource-authoring pages match the new contract
(FR-031, FR-032).

## 8. The closing check run

```bash
bash scripts/run_checks_with_log.sh
```

**Expected**: green from the repository root, with exactly two remarks standing — the Vite build's
chunk-size advisory and LangGraph's `LangChainPendingDeprecationWarning` — both named as accepted in
the script and the constitution's check-run section. Every other remark is fixed before the change
is called finished (SC-017, Principle VI).

**This script does not run the examples.** `scripts/run_checks_with_log.sh:168-178` runs
`tests/packaging` and the eight package suites and stops there, so `tests/examples/test_examples_run.py`
(§6) is a gate of its own and must be run explicitly — a broken example is invisible to the closing
check run.

## What "done" looks like

- 30 concurrent calls succeed with 0 shared-connection errors, with and without a pool; two
  concurrent transactions never interleave.
- A pool with a stated floor and ceiling is created once by the application's lifespan, closed once
  at shutdown, hands its third caller what the others released, and bounds the wait with the stated
  value rather than waiting forever.

- A per-call declaration is the mandatory pair; its finalizer runs exactly once on every path and
  never masks the run's own error.
- `close()` is in the contract as a harmless default, the wrapper refuses it, and no subclass needed
  an edit.
- Every example exits 0 with no database; the demo's suite is green with and without a connection
  description and with no PostgreSQL running.
- `bash scripts/run_checks_with_log.sh` is green with only the two accepted remarks.

## What would make this quickstart lie

- **A harness that does not enforce one-operation-at-a-time.** Without it the concurrency test stays
  green even after the adversarial break that shares one connection, so §1's RED cannot be produced
  and SC-019 is unverifiable. Running the same tests against a **real** PostgreSQL hides this the
  other way: the suite passes while proving nothing, and makes the feature look as if it needs a
  database.
- **Testing only sequential calls.** The defect is a concurrency defect; one call after another can
  never raise "another operation is in progress" and never interleaves two transactions.
- **A `-k` selection that matches nothing, or a mistyped demo DSN.** A selection with no matches
  exits 5 while the terminal looks calm, so confirm the node count; and a DSN whose setting name
  does not match the demo README silently selects the database-free branch, so the pool-backed path
  is never exercised.
