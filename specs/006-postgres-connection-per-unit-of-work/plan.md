# Implementation Plan: One connection per unit of work, and one pool for the process

**Branch**: `feature/issue-215-postgres-connection-per-unit-of-work` | **Date**: 2026-10-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/006-postgres-connection-per-unit-of-work/spec.md`

## Summary

`PostgresResource` opens one connection for the whole process (`postgres_resource.py:84`) and every
method of the class shares it, so concurrent calls collide with the driver's "another operation is in
progress" error and a transaction that yields between `BEGIN` and `COMMIT` lets another caller's
statement, and another caller's `COMMIT`, into its session. The feature makes the resource **one unit
of work**: it takes a connection when it is opened — either its own or one borrowed from a pool — and
gives it back when it is closed. The pool is the application's object, created at startup and closed
at shutdown, and the framework gains only the general place where that code runs. A per-call
declaration becomes a mandatory pair, `PerCallConnection(factory, finalize)`, and the adapters apply
the pair through one new `connection_scope` in `aoa-action-machine`. `close()` enters the SQL
contract as a concrete no-op, so the eight demo stubs and the existing test doubles need no edit, and
the nested-action proxy refuses `close` and context-manager use as it already refuses transaction
control. The library also stops drawing a pool it does not create, the guidance gains the mandatory
pair and a general section on a long-lived pool behind a per-call resource, the examples show both
lambdas, and the demo extends its `identity` domain with a pool that works with no PostgreSQL
running. No new dependency is introduced anywhere: `asyncpg` is already the optional `postgres`
extra, and every test this feature adds runs against a fake pool.

## Technical Context

**Language/Version**: Python 3.12 (`requires-python = ">=3.12"` repo-wide; PEP 695 `type` aliases and generics already used)

**Primary Dependencies**: `asyncpg>=0.29,<1.0` — already the `postgres` extra of `aoa-action-machine`, not a new dependency; `fastapi`/`starlette` for the FastAPI adapter's `lifespan`; `mcp>=1.0,<2.0`, whose `FastMCP` accepts a `lifespan` context manager (measured); `pydantic>=2` for the demo's route models. **Nothing new is added to any package's dependencies.** For the tests: `pytest`, `pytest-asyncio` (`asyncio_mode = "auto"`), and plain-Python fakes.

**Storage**: PostgreSQL is the subject, not a requirement. The feature must be verifiable and demonstrable with **no database running**: tests supply a fake pool through the new `pool=` parameter, and the demo creates a pool only when a DSN is supplied

**Testing**: pytest per package (`testpaths = ["tests"]`, `pythonpath = ["src"]`, `asyncio_mode = "auto"`), driven by `bash scripts/run_checks_with_log.sh`. **The repository-wide examples runner is not part of that script** — `scripts/run_checks_with_log.sh:168-178` runs `tests/packaging` and the eight package suites and stops there — so `tests/examples/test_examples_run.py` (which executes every `examples/**/*.py` and requires a zero exit code) must be run explicitly as its own gate, and the plan gives it its own task. Example breakage is invisible to the closing check run unless that task runs.

**Target Platform**: the eight-package `uv` workspace on CPython 3.12; the adapters serve ASGI (FastAPI) and MCP (`FastMCP`) applications; the repository check run plus the examples runner are the gates

**Project Type**: a library change spanning three packages — `aoa-action-machine` (the resource, the per-call pair, the scope, the contract), `aoa-fastapi-adapter` and `aoa-mcp-adapter` (the boundary hook and the lifecycle option) — plus documentation, examples and the demo

**Performance Goals**: none beyond correctness. The change removes a per-request connection *only when a pool is used*; without a pool it opens exactly one connection per call as before, and adds one `connection_scope` frame per request. No latency or throughput target is introduced, and none is claimed

**Constraints**: the resource's transaction surface keeps its behaviour (FR-027); no new public query method appears — the generic query surface is [#216](https://github.com/bystrovmaxim/aoa/issues/216) (FR-026); the pool never enters `connections` (FR-012); a resource never closes a pool (FR-007); `machine.run` keeps receiving only `dict[str, BaseResource]` (FR-022); the public constructor is exactly the two documented forms plus `rollup`, with no test-only parameter (SC-022); Maxitor is untouched (FR-028); every `examples/**/*.py` script runs with no database (FR-035)

**Scale/Scope**: 4 new source modules (the connection scope, the pool's structural type, the demo resource, the demo action) and ~11 edited source modules across three packages; 1 new shared test-support module, 3 new test modules in the machine (one per story that owns tests), 2 in the adapters, 2 in the demo, plus 5 migrated declarations and 1 in the example; 8 demo stub files explicitly **not** touched; ~6 documentation files (each with its Russian draft where the maintainer reads it); 2 example scripts and their 2 notebooks; 2 changelog entries; the check run

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
| --- | --- | --- |
| I. The maintainer decides | No commit, push, pull request or merge is part of executing this plan without an explicit instruction in the current turn | PASS — the plan produces files only; the branch exists on the maintainer's instruction |
| II. English in commits, in git and in code | Every new module, docstring, comment, test, docstring page and changelog entry in English; the Russian drafts the maintainer reads are `*.ru_draft.md`, gitignored, and reported beside their English page | PASS — planned |
| III. Module headers | Each new module opens with its repository-relative path on line 1, a one-line `Name — purpose.`, the 79-column `═` sections, `PURPOSE` and `ARCHITECTURE / DATA FLOW` among them | PASS — planned; the three new source modules and the shared test-support module all carry headers |
| IV. AI-CORE blocks | `connection_scope` is a module-level function and gets `ROLE`/`CONTRACT`; `PerCallConnection` keeps its block and gains the `finalize` contract; no block in a module docstring, none on a method | PASS — planned |
| V. Short docstrings | Every new class, function and method gets its one-line docstring ending with a period, identifiers in double backticks | PASS — planned |
| VI. Check run, documentation, changelog | Exactly three closing tasks in that order, and no other task absorbs them | PASS — T039 (check run), T040 (documentation), T041 (changelog). The adversarial verification (T038) stands immediately before the tail, because the constitution requires the break to be made and restored while the code is still the implementation's, not the changelog's |
| Final step: the check run | `bash scripts/run_checks_with_log.sh` is run and taken to zero; the two accepted remarks (Vite chunk size, LangGraph pending deprecation) are the only ones allowed to stand | PASS — closing task, taken to zero |

**Three readings of the repository's own practice, recorded rather than silently resolved**:

1. **Which changelog.** Principle VI names `docs/CHANGELOG.md`, while the repository now keeps a
   per-package changelog: the last framework-level change wrote its package's file, and
   `docs/CHANGELOG.md` holds the framework-level article. This feature is a library change with a
   breaking change to a published contract, so the closing task writes **one** article in
   `packages/aoa-action-machine/CHANGELOG.md` (with `### Breaking changes`) and **one** entry in
   `packages/aoa-demo/CHANGELOG.md` — both under `## [Unreleased]`, since a dated heading is the
   maintainer's release act — and adds a `docs/CHANGELOG.md` line only if the maintainer
   judges the work framework-level. That is a question for the maintainer at that task, not a licence
   to write three articles.
2. **Which order the tail runs in.** Principle VI fixes the tail as check run → documentation →
   changelog, while the section *Final step: the check run* calls the run "the last step of any
   change". The tasks follow Principle VI, for a reason stronger than precedence: the run's first
   Python step is `ruff check --fix`, so the run must see the settled code; the documentation task
   writes Markdown and the Russian drafts, which the run does not read (it lints Python, not prose);
   and the changelog is prose that summarizes what the documented, checked code does. The example
   scripts are the one artefact that must run — and they are executed while they are written
   (Principle VI, point 6), which is why they belong to the implementation tasks, not to the tail.
   If the maintainer reads the two sections the other way, the tail becomes documentation →
   changelog → check run and T039–T041 are reordered; nothing else changes.
3. **Which pages owe a Russian draft.** The maintainer reads Russian, and a page written or
   substantially rewritten in this change is reported as both links. New pages get
   `<page>.ru_draft.md`; pages *edited* without changing their structure get the draft updated only
   where the change is reader-visible. The plan reserves the draft work in T040 rather than in each
   page's task, so that the two-language pair is produced together and reported together.

**Re-check after Phase 1 design**: no new dependency, no new package, no change to any action's
`@connection` declaration, no new public query surface, no file under `packages/aoa-maxitor/`, and no
test that needs a live database. Every gate above still passes, and **Complexity Tracking** stays
empty.

## Project Structure

### Documentation (this feature)

```text
specs/006-postgres-connection-per-unit-of-work/
├── plan.md              # This file (/speckit-plan output)
├── spec.md              # The capability, clarified (5 questions, 5 answers)
├── research.md          # Phase 0 output: the decisions behind the design
├── data-model.md        # Phase 1 output: ownership, states, validation rules
├── quickstart.md        # Phase 1 output: how to prove it works
├── checklists/
│   └── requirements.md  # Spec quality checklist (12/12 passing)
├── contracts/           # Phase 1 output: the four surfaces this change fixes
│   ├── per-call-connection.md   # the mandatory pair, the scope, error precedence
│   ├── sql-resource.md          # the two construction forms, open/close, the pool's shape
│   └── boundary.md              # the four hook sites and the lifecycle option
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
packages/aoa-action-machine/
├── src/aoa/action_machine/exceptions/
│   ├── resource_contract_violation_error.py  # NEW: the family `ResourceContractViolationError(RuntimeError)`
│   └── transaction_left_open_error.py    # NEW: its subclass, raised by `close()` after rollback and return
├── src/aoa/action_machine/resources/
│   ├── per_call_connection.py            # EDIT: mandatory `finalize`; callable check
│   ├── connection_scope.py               # NEW: open what has a lifecycle, finalize in a finally
│   ├── sql/pool_protocol.py              # NEW: the pool's structural type the resource relies on
│   ├── sql/protocol_sql_resource.py      # EDIT: `close()` in the structural contract
│   ├── sql/sql_resource.py               # EDIT: concrete no-op `close()`
│   ├── sql/wrapper_sql_resource.py       # EDIT: refuse close / __aenter__ / __aexit__
│   ├── postgres/postgres_resource.py     # EDIT: (connection_params=None, *, pool=None, rollup=False)
│   │                                     #       open() takes the connection, close() returns it
│   └── postgres/__init__.py              # EDIT: the package description stops drawing a pool
├── tests/
│   ├── support/fake_pool.py              # NEW: the fake pool and the one-operation-at-a-time connection
│   │                                     #      (beside the existing tests/support/ fixtures)
├── tests/action_machine/resources/
│   ├── test_resource_unit_of_work.py    # NEW [US1]: concurrency, isolation, exception, cancellation
│   ├── test_pool_bounds.py              # NEW [US2]: ceiling, waiting, timeout, borrow and return
│   ├── test_connection_scope.py         # NEW [US3]: finalize once, precedence, cancellation
│   ├── test_resolve_connections.py       # EDIT: the per-call declarations gain `finalize`
│   ├── test_sql_resource.py              # EDIT: `close()` contract, no-op default
│   └── test_wrapper_sql_resource.py      # EDIT: the refusals, `isinstance`, no `acquire`
└── CHANGELOG.md                          # EDIT: the article under ## [Unreleased], with ### Breaking changes (T041)

packages/aoa-fastapi-adapter/
├── src/aoa/fastapi/adapter.py            # EDIT: the lifecycle option; three call sites use the scope
├── tests/test_fastapi_endpoints.py       # EDIT: :200 gains `finalize`; the lifecycle tests
└── tests/test_adapter_lifespan.py        # NEW: startup runs, shutdown runs, a failing run still closes

packages/aoa-mcp-adapter/
├── src/aoa/mcp/adapter.py                # EDIT: the lifecycle option; one call site uses the scope
└── tests/
    ├── test_mcp_handler.py               # EDIT: :756 gains `finalize`
    └── test_adapter_lifespan.py          # NEW: `build(lifespan=…)` reaches FastMCP; startup and
                                          #      shutdown run; the tool path finalizes

packages/aoa-demo/
├── pyproject.toml                        # EDIT: the `postgres` extra
├── src/aoa/demo/fastapi_mcp_services/
│   ├── infrastructure.py                 # EDIT: the pool holder, created only when a DSN is given
│   ├── app_fastapi_service.py            # EDIT: the lifespan option on build()
│   ├── app_mcp_service.py                # EDIT: the same lifespan reaches FastMCP
│   └── actions/__init__.py               # EDIT: register the identity action's route beside the others
├── src/aoa/demo/model/identity/
│   ├── actions/identity_lookup.py        # NEW: the identity domain has no actions/ today; this is the
│   │                                     #      first one, declaring @connection(IdentityStore, key="identity")
│   ├── resources/identity_store.py       # NEW: the Postgres resource — a read and a transactional method
│   └── README.md                         # NEW/EDIT: what the domain demonstrates, and the no-DSN mode
├── tests/test_identity_postgres.py       # NEW: concurrency, isolation, finalize, pool closed on shutdown
├── tests/test_sql_resource_stubs.py      # NEW: the eight existing stubs pass with no edit
├── README.md                             # EDIT: the database-free mode
└── CHANGELOG.md                          # EDIT: its own article under ## [Unreleased] (T041)

docs/
├── extensions/postgresql.md              # EDIT: the pool, open/close, ownership, the held transaction
├── tutorials/step-17-connections.md      # EDIT: the mandatory pair; the new section and its exercise
├── tutorials/step-19-resource.md         # EDIT: the wrapper does not expose closing
├── how-to/authoring-resource.md          # EDIT: closing among the obligations
└── how-to/choosing-action-aspect-resource.md  # EDIT: the per-call pair and the pool

examples/
├── step_17_connections/01_connections.py (+ .ipynb)   # EDIT: the pool-backed per-call case, both lambdas
└── step_19_resource/01_resource.py (+ .ipynb)         # EDIT: the same case beside the wrapper
```

**Structure Decision**: the per-call lifecycle goes into `aoa-action-machine`, beside the declaration
it governs, because that is the only package both adapters depend on and because
`action_machine` may import nothing (`scripts/package_boundaries.toml`). The pool is **not** a
framework type: the framework relies on the shape it uses — an awaitable acquire, an awaitable
release, an awaitable close, and stated bounds — and the concrete pool is the driver's, created by
the application. The adapter gets one option, not a Postgres vocabulary, and it hands that option to
the framework that owns a startup hook: `FastAPI(lifespan=…)` and `FastMCP(…, lifespan=…)`.

The tests are split by subject rather than by file count. The fake pool is shared support, because
concurrency, exhaustion, cancellation and finalization all need the same instrument, and a second
copy of the one-operation-at-a-time rule would be a second thing to keep true. The lifecycle tests
live in the machine (where the scope lives), the request-level tests in the FastAPI adapter (where
the boundary lives), and the end-to-end tests in the demo (where an application does).

**Two measurements this plan relies on, recorded with their source**: the FastAPI adapter has
exactly three `resolve_connections` sites and the MCP adapter exactly one (found by searching for the
call, listed in [research.md](./research.md) R6); and `mcp.server.fastmcp.FastMCP.__init__` accepts
`lifespan`, with no `run_async` method (measured against the installed package, R5). The second one
is what removes the issue's open choice between a new adapter option and an `app.router` wrapper: the
MCP server has a startup hook of its own, so the option is enough in both adapters.

**Three points the design phase settled, because a contract cannot leave them open**:

1. **Opening an already-open resource is idempotent and keeps the connection it holds.** `open()`
   returns immediately when a connection is already held; it does not replace it, because replacing
   would leak the connection it dropped. With `close()` this gives the pair the property the spec
   asks for (Edge Cases): open, close, open again are all safe. This also matches how the class reads
   today — every operation already refuses to run without a connection (`begin()` at
   `postgres_resource.py:95-96`), so "no connection" and "open" are the two states, and `open()` is
   the transition into the second.
1a. **A transaction left open at closing fails fast, after the connection is returned.** The
   maintainer's decision, taken after this plan was drafted: the resource tracks `_in_transaction`
   (`begin` sets it; a successful `commit`/`rollback` clears it — a rollup commit clears it through
   `rollback`; a failed `COMMIT` leaves it set, because the resource cannot claim the transaction
   ended). `close()` that finds it set issues `ROLLBACK` itself, returns the connection to the pool
   or closes it, and **then** raises `TransactionLeftOpenError` from new
   `exceptions/transaction_left_open_error.py` and `exceptions/resource_contract_violation_error.py`.
   Fail-fast is applied to the precedence as well: the violation is the raised error **even when the
   run already failed**, with the run's error chained as its cause — it is never demoted to a note,
   because that would hide what the developer has to fix. Cleaning up before raising is what keeps
   fail-fast from becoming a leak: the connection is back, so FR-017 and FR-021 still hold. The one
   exception is cancellation: a `CancelledError` still propagates and the violation is recorded beside
   it (FR-044, `ResourceContractViolationError`). A second
   `close()` finds an empty resource and stays silent (FR-006). The driver's own rollback on release
   or disconnect is measured and recorded in [research.md](./research.md) R4 as background — the
   explicit `ROLLBACK` is the mechanism, and relying on the driver's reset is the drift the decision
   refuses.
2. **A failing factory has nothing to finalize.** `factory()` runs before the resource exists, so a
   raise there propagates and no finalizer for that entry runs — "exactly once" is *exactly once per
   resource that was created*, not once per declaration. The resources of the same call that were
   already created are still finalized (FR-021).
3. **The adapter adds no timeout and no ordering of its own to the lifecycle hook.** The context
   manager's closing is the framework's own startup/shutdown contract: `FastAPI(lifespan=…)` runs it
   as the application's lifespan, and `FastMCP(…, lifespan=…)` runs it for the server. The adapter's
   obligation under FR-038 is to say exactly that — the hook runs when the application or server
   starts and stops, and how long that takes and in what order relative to the server's own shutdown
   is the framework's, not a bound this repository invents.

**One correction to the issue's sketch, recorded rather than followed.** The issue writes
`pool = await asyncpg.create_pool(**connection_params, min_size=1, max_size=10, timeout=30)`. In the
installed driver (`asyncpg 0.31.0`) `create_pool` has **no** `timeout` parameter — the wait bound is
passed to `acquire(timeout=…)` — and `Pool.acquire` is not a coroutine function but a context object
that supports both `await` and `async with`. The feature therefore keeps the issue's intent (stated
size, stated wait bound, connection acquired in `open()`) while using the interface the driver
actually has. [research.md](./research.md) R4 records the signature and both call forms.

## Documentation design (FR-029 to FR-035)

The documentation is not a task list item to be improvised; these are the prose changes the spec
requires, and the plan fixes them so the documentation task writes rather than decides.

| Page | What changes |
| --- | --- |
| `docs/tutorials/step-17-connections.md`, mode-2 section | State the mandatory pair: `factory` creates, `finalize` closes; the finalizer may be sync or async; the boundary calls it after the run on success, on exception and on cancellation. **Delete two claims**: that a per-call resource is "a fresh instance per request" (the factory may return anything) and that it has "no shared state between requests" (false while mode 2 was used to reach shared application state). |
| `docs/tutorials/step-17-connections.md`, new section **"A long-lived pool behind a per-call resource"**, placed immediately after **"What to choose"** | General, not Postgres-specific: holder, startup hook, route, resource; the three-case table (ready → lifespan opens and closes; per-call with `open` → boundary opens, finalize closes; per-call without `open` → nobody opens, finalize closes); the invariants; review questions; the exercise — replace the pool-backed resource with a DSN-backed one and say what changed in cost but not in correctness, then drop the wait bound with `max_size` below the number of concurrent callers and say what happens. Cross-link `postgresql.md`. |
| `docs/extensions/postgresql.md` | The pool, `open`/`close`, who owns the connection, and that a transaction runs on the held connection with `begin`/`commit` unchanged. |
| `docs/how-to/authoring-resource.md`, `docs/how-to/choosing-action-aspect-resource.md` | Closing among the contract's obligations; the two construction forms; the per-call pair. |
| `docs/tutorials/step-19-resource.md` | The wrapper does not expose closing, and why a nested action must not close its caller's connection. |
| `packages/aoa-action-machine/.../resources/postgres/__init__.py` | Stop drawing "asyncpg pool / connections" that the code does not create. |
| Root `README.md` | Untouched: its read examples run through the generic query surface, whose rewrite belongs to [#216](https://github.com/bystrovmaxim/aoa/issues/216) (FR-026). |

## Application-layer pieces the plan fixes

- **The holder** (FR-013) is not a framework type: it is the application's own small object beside the
  app, and reading it before it is filled raises a named `HandleError`, not an `AttributeError`. The
  demo's `infrastructure.py` is where the pattern is implemented and tested; the connections chapter
  is where it is taught.
- **The shared test instrument** (FR-042): the canonical fake pool and the one-operation-at-a-time
  connection live in `packages/aoa-action-machine/tests/support/fake_pool.py`;
  the FastAPI adapter's and the demo's tests carry a small stub (acquire/release/high-water mark),
  because their subject is wiring and lifecycle, not contention; the examples inline a minimal stub so
  they run with no database and no test-support import.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No constitution violations — the table is intentionally empty. The three readings recorded in the
Constitution Check are questions of practice inside the constitution's own text, not violations, and
each costs at most one decision at the task where it lands.
