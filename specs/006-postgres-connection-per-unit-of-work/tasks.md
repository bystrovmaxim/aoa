# Tasks: One connection per unit of work, and one pool for the process

**Input**: Design documents from `specs/006-postgres-connection-per-unit-of-work/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: included, because this feature's acceptance is a test that must go red on the defect and
green on the fix (FR-042, FR-043, SC-001, SC-019). Every test runs with **no database**: the fake
pool and the one-operation-at-a-time connection are the instrument (FR-042).

**Organization**: one phase per user story, in priority order. The last three tasks are the
constitution's tail, in its order, and no other task absorbs them: the check run, the documentation,
the changelog (Principle VI). Phases are commit units (house rule: one phase = one commit) — and
nothing is committed until the maintainer instructs it (Principle I).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: different files, no dependency on an incomplete task
- **[Story]**: US1…US6, mapping to spec.md
- Every task names the exact file path it touches

## Path Conventions

Repository root is `packages/` + `docs/` + `examples/` + `tests/`. Python packages are
`packages/<pkg>/src/aoa/<pkg>/` with tests in `packages/<pkg>/tests/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: the two things every later phase needs and nothing else does.

- [x] T001 Adopt the package's **existing** test-support package as the harness home: extend the docstring of `packages/aoa-action-machine/tests/support/__init__.py` to name the connection harness it will carry, and create no second support package — the repository already keeps shared fixtures in `tests/support/` (Principle III)
- [x] T002 [P] Add the `postgres` extra to `packages/aoa-demo/pyproject.toml` — `postgres = ["asyncpg>=0.29,<1.0"]` — and confirm nothing in `packages/aoa-demo/src` imports the driver at import time (FR-037)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the contract's harmless `close()`, the pool's structural type, and the test instrument.
All six stories need these; none of them alone delivers a story.

**⚠️ CRITICAL**: no user story work can begin until this phase is complete

- [x] T003 Add a concrete no-op `close()` to the structural contract in `packages/aoa-action-machine/src/aoa/action_machine/resources/sql/protocol_sql_resource.py` (one-line docstring; body `...` is not enough — it must be a real default) (FR-023)
- [x] T004 Add a concrete no-op `close()` to `packages/aoa-action-machine/src/aoa/action_machine/resources/sql/sql_resource.py` beside `open`/`begin`/`commit`/`rollback` (FR-023)
- [x] T005 Create `PoolProtocol` with `acquire(*, timeout: float | None = None)` (an ordinary method, **not** `async def`), `await release(conn)`, `await close()` in `packages/aoa-action-machine/src/aoa/action_machine/resources/sql/pool_protocol.py` — with the module header and an AI-CORE block (FR-005, research R4, contracts/sql-resource.md §6)
- [x] T006 Implement the canonical fake pool and the one-operation-at-a-time connection in `packages/aoa-action-machine/tests/support/fake_pool.py`: re-entrant operation raises the interface error; `acquire` beyond `max_size` waits; the wait ends in a named failure at the stated bound; `release` returns the connection and a second release is refused; a high-water mark is recorded; `close()` refuses while connections are held (FR-042, SC-004)

**Checkpoint**: the contract compiles with the eight demo stubs unedited, and the fake pool can make a
shared-connection test fail.

---

## Phase 3: User Story 1 — one connection per unit of work (Priority: P1) 🎯 MVP

**Goal**: a resource holds one connection, only for its own unit of work, so concurrent calls stop
colliding and transactions stop interleaving.

**Independent Test**: run 30 concurrent units of work each with its own resource and confirm 0
one-operation-at-a-time failures and 0 rows committed by the wrong owner; then confirm an exception
and a cancellation both return the connection.

### Tests for User Story 1 (write first, confirm they fail before the implementation)

- [x] T007 [P] [US1] Concurrency test — 30 concurrent units of work, each its own resource, exactly 0 failures carrying the interface error — in `packages/aoa-action-machine/tests/action_machine/resources/test_resource_unit_of_work.py` (FR-002, FR-003, SC-001, SC-003)
- [x] T008 [US1] Transaction-isolation test — two concurrent `BEGIN`…`COMMIT` runs, 0 interleaved statements, 0 rows committed by the wrong owner — in `packages/aoa-action-machine/tests/action_machine/resources/test_resource_unit_of_work.py` (FR-002, SC-002)
- [x] T009 [US1] Exception and cancellation tests — a run that raises and a run that is cancelled both release the connection, 0 left unreturned — in `packages/aoa-action-machine/tests/action_machine/resources/test_resource_unit_of_work.py` (SC-004)
- [x] T010 [US1] Construction tests — both `connection_params` and `pool`, and neither, raise `ConnectionValidationError` at construction; `pool` is keyword-only — in `packages/aoa-action-machine/tests/action_machine/resources/test_resource_unit_of_work.py` (FR-005, SC-022)

### Implementation for User Story 1

- [x] T011 [US1] Change `PostgresResource.__init__` in `packages/aoa-action-machine/src/aoa/action_machine/resources/postgres/postgres_resource.py` to `(connection_params: dict[str, Any] | None = None, *, pool: PoolProtocol | None = None, rollup: bool = False)`, validate exactly one of the two with `ConnectionValidationError`, annotate the pool with `PoolProtocol` (never the driver), and add the class attribute `acquire_timeout: float | None = 30.0`; initialise `_in_transaction = False` (FR-004, FR-005, FR-009, FR-044)
- [x] T012 [US1] Rewrite `open()` in `packages/aoa-action-machine/src/aoa/action_machine/resources/postgres/postgres_resource.py`: return immediately when a connection is already held (idempotent, keeps the held connection); otherwise `await self._pool.acquire(timeout=self.acquire_timeout)` when a pool is held, else `asyncpg.connect(**self._connection_params)`; keep the `HandleError` wrapping, and maintain the transaction flag — `begin()` sets it, `commit()` and `rollback()` clear it on success, a rollup commit clears it through `rollback`, and a failed `COMMIT` leaves it set (FR-002, FR-004, FR-006, FR-010, FR-027, FR-044)
- [x] T013 [US1] Add `ResourceContractViolationError(RuntimeError)` in `packages/aoa-action-machine/src/aoa/action_machine/exceptions/resource_contract_violation_error.py` and `TransactionLeftOpenError` in `packages/aoa-action-machine/src/aoa/action_machine/exceptions/transaction_left_open_error.py` (its subclass), each with an AI-CORE block and a docstring saying plainly that this is the caller's code to fix and not a failure to catch — and add the real `close()` to `packages/aoa-action-machine/src/aoa/action_machine/resources/postgres/postgres_resource.py`: clear `self._conn` first (idempotent); if `_in_transaction` is set, issue `ROLLBACK` itself, clear the flag, then return the connection and raise `TransactionLeftOpenError`; otherwise `await self._pool.release(conn)` or `await conn.close()` with no error; never close the pool; harmless when no connection is held (FR-006, FR-007, FR-044)
- [x] T014 [US1] Update the module header and the AI-CORE block of `packages/aoa-action-machine/src/aoa/action_machine/resources/postgres/postgres_resource.py`: the architecture diagram shows `open()` taking a connection from the pool or the driver, `close()` returning it, and the stated `acquire_timeout` (FR-001, Principle III/IV)

**Checkpoint**: User Story 1 works on its own — a resource is one unit of work, and the four tests above pass with no database.

---

## Phase 4: User Story 2 — one pool for the process (Priority: P2)

**Goal**: the application creates one pool at startup and closes it at shutdown, its bounds stated,
and a request that arrives at the ceiling waits, bounded, instead of forever.

**Independent Test**: start an application with a pool, serve concurrent requests through a
pool-backed resource, stop it, and confirm the pool was created once, its ceiling was never exceeded,
and it was closed on shutdown.

### Tests for User Story 2

- [x] T015 [P] [US2] Pool-behaviour tests — ceiling 2 with 3 concurrent calls (the third completes after a release); a wait that never frees ends in a named failure at the stated bound; high-water mark never exceeds the ceiling; a borrowed connection returns to a still-open pool — in `packages/aoa-action-machine/tests/action_machine/resources/test_pool_bounds.py` (FR-010, FR-011, SC-004, SC-006)
- [x] T016 [P] [US2] FastAPI lifecycle test — the option's context manager runs at startup and its closing runs at shutdown, including when the startup body raises — in `packages/aoa-fastapi-adapter/tests/test_adapter_lifespan.py` (new) (FR-008, FR-038, SC-005)
- [x] T017 [P] [US2] MCP lifecycle test — `build(lifespan=…)` reaches `FastMCP`, and startup and shutdown run — in `packages/aoa-mcp-adapter/tests/test_adapter_lifespan.py` (new) (FR-008, FR-038)

### Implementation for User Story 2

- [x] T018 [US2] Add the one keyword-only lifecycle option to `FastApiAdapter.build()` in `packages/aoa-fastapi-adapter/src/aoa/fastapi/adapter.py` (default `None`) and pass it as `FastAPI(..., lifespan=...)`, adding the argument only when the option is not `None` (FR-038, SC-021)
- [x] T019 [US2] Add the same keyword-only option to `McpAdapter.build()` in `packages/aoa-mcp-adapter/src/aoa/mcp/adapter.py` and pass it as `FastMCP(self._server_name, tools=tools, lifespan=...)` (FR-038, SC-021)
- [x] T020 [US2] Update the docstrings of `packages/aoa-fastapi-adapter/src/aoa/fastapi/adapter.py` and `packages/aoa-mcp-adapter/src/aoa/mcp/adapter.py` for the new option: state that the hook runs when the application or server starts and stops, and that the framework, not the adapter, defines how long its closing takes and where it sits relative to shutdown (FR-038)

**Checkpoint**: User Stories 1 and 2 both work — correctness without a pool, economy with one.

---

## Phase 5: User Story 3 — a per-call declaration must say how it is closed (Priority: P3)

**Goal**: `PerCallConnection(factory, finalize)` is mandatory, and the boundary applies the pair on
every path through one `connection_scope`.

**Independent Test**: declare a per-call resource with a factory and a finalizer, run a route on a
success path, a failing path and cancellation, and confirm the finalizer ran exactly once each time
and never masked the run's error.

### Tests for User Story 3

- [x] T021 [P] [US3] Finalizer tests — exactly once on success, on exception and on cancellation; a failing finalizer surfaces on a clean run and is appended with `add_note` on a failed run; a resource with no `open` is never opened but is finalized; a factory that raises leaves the earlier created resources finalized — in `packages/aoa-action-machine/tests/action_machine/resources/test_connection_scope.py` (FR-017, FR-018, FR-020, FR-021, FR-044, SC-008, SC-009, SC-023): including a close with a transaction open — the connection is back in the pool **and** `TransactionLeftOpenError` is the raised error, on a clean run and on a failed run alike, with the run's error as its cause; an **operational** closing failure keeps the old precedence; cancellation still propagates
- [x] T022 [P] [US3] Declaration tests — a missing `finalize` is a construction error; a non-callable `finalize` is rejected by validation; a factory returning a shared resource is neither rejected nor detected — in `packages/aoa-action-machine/tests/action_machine/resources/test_resolve_connections.py` (FR-014, SC-007)

### Implementation for User Story 3

- [x] T023 [US3] Add the mandatory second field `finalize: Callable[[BaseResource], Awaitable[None] | None]` to `PerCallConnection` in `packages/aoa-action-machine/src/aoa/action_machine/resources/per_call_connection.py` (order `factory, finalize`, `frozen=True`), and check `callable(value.finalize)` in `validate_connection_entries`; update the module docstring (FR-014, FR-015)
- [x] T024 [US3] Create `connection_scope` in `packages/aoa-action-machine/src/aoa/action_machine/resources/connection_scope.py` exactly as contracts/per-call-connection.md §4: walk the declaration per entry, open only what a `PerCallConnection` created (if it has `open`), yield the mapping, in a `finally` finalize each created resource exactly once (opened first, then the rest, declaration order; await an awaitable result), shield each finalize on cancellation, and append a closing failure to a propagating run error with `add_note`. The new module carries its line-1 path, a `Name — purpose.` first line, the 79-column `═` sections with `PURPOSE` and `ARCHITECTURE / DATA FLOW`, and an AI-CORE `ROLE`/`CONTRACT` block on the module-level function (FR-016–FR-022, FR-019, FR-025; Principles III, IV, V)
- [x] T025 [US3] Replace `resolve_connections(record.connections)` with `async with connection_scope(record.connections) as connections:` at the three sites in `packages/aoa-fastapi-adapter/src/aoa/fastapi/adapter.py` (`_make_endpoint_with_body` :299, `_make_endpoint_with_query` :369, `_make_endpoint_no_params` :468), leaving each endpoint body below unchanged (FR-016, FR-017)
- [x] T026 [US3] Apply the scope inside `_execute_tool_call` in `packages/aoa-mcp-adapter/src/aoa/mcp/adapter.py` around its `machine.run` (:407–:410), without changing any signature or the JSON envelope (FR-016, FR-017)
- [x] T027 [US3] Migrate the five one-argument declarations to the pair: `packages/aoa-fastapi-adapter/tests/test_fastapi_endpoints.py:200`; `packages/aoa-action-machine/tests/action_machine/resources/test_resolve_connections.py:37`, `:56`, `:88`; `packages/aoa-mcp-adapter/tests/test_mcp_handler.py:756` — each keeps the behaviour it was written to prove (FR-041, SC-018)
- [x] T028 [US3] Add an adapter-level test that a route's per-call resource is created, opened, finalized exactly once, and that `machine.run` still receives only `dict[str, BaseResource]` — in `packages/aoa-fastapi-adapter/tests/test_fastapi_endpoints.py` (FR-022, SC-008)

**Checkpoint**: mode 2 is a pair; the three stories together give correctness, economy and a closed lifecycle.

---

## Phase 6: User Story 4 — closing in the contract, and the nested action that cannot close (Priority: P4)

**Goal**: every SQL resource answers `close()`, the driver really releases its connection, and a
nested action's proxy refuses to close what it does not own.

**Independent Test**: close a driver-backed resource from outside and see the connection released;
close a resource that holds nothing and see it harmless; call `close` and enter the wrapper as a
context manager and see both refused while it still satisfies the SQL resource contract.

### Tests for User Story 4

- [x] T029 [P] [US4] Wrapper tests — `close`, `open`, `begin`, `commit`, `rollback` and `async with` are all refused, `acquire` is not exposed, and `isinstance(wrapper, ProtocolSqlResource)` stays true — in `packages/aoa-action-machine/tests/action_machine/resources/test_wrapper_sql_resource.py` (FR-024, SC-011)
- [x] T030 [P] [US4] Contract tests — a resource that holds no connection closes harmlessly; open → close → open → close is safe; `rollup=True` still rolls back on the held connection; the no-op default means the existing doubles need no edit — the contract default in `packages/aoa-action-machine/tests/action_machine/resources/test_sql_resource.py`, and the PostgreSQL fail-fast cases in `packages/aoa-action-machine/tests/action_machine/resources/test_resource_unit_of_work.py` (where the fake pool is) (FR-006, FR-023, FR-025, FR-027, FR-044, SC-010, SC-023): including a close with a transaction open — rollback issued, connection returned, `TransactionLeftOpenError` raised and outranking the run's error — and a second close that raises nothing and returns nothing twice
- [x] T031 [P] [US4] Stub-subclass test — the eight `SqlResource` subclasses under `packages/aoa-demo/src/aoa/demo/model/` (catalog/search_sidecar.py, catalog/object_store.py, messaging/dlq_store.py, messaging/outbox_primary.py, billing/warehouse.py, billing/read_replica.py, store/db.py, store/cache.py) still instantiate and satisfy the contract **with no edit to any of them** — in `packages/aoa-demo/tests/test_sql_resource_stubs.py` (FR-023, SC-012); it asserts the eight **existing** stubs only, so it does not depend on the new demo resource

### Implementation for User Story 4

- [x] T032 [US4] Forbid `close`, `__aenter__` and `__aexit__` in `packages/aoa-action-machine/src/aoa/action_machine/resources/sql/wrapper_sql_resource.py` with `TransactionProhibitedError` and the same explanatory wording as the existing refusals; expose no `acquire`; update the module header's list of forbidden operations (FR-024, FR-026)

**Checkpoint**: the private-connection reach-through has no reason left, and the proxy is a closed door.

---

## Phase 7: User Story 6 — the demo shows the pattern and needs no database (Priority: P6)

**Goal**: the demo's identity domain shows a pool-backed per-call resource end to end, and its suite
is green with no PostgreSQL and without the driver installed.

**Independent Test**: install the demo without its `postgres` extra, run its suite, and confirm it is
green with no database; then run it with a DSN supplied and confirm concurrency, isolation,
finalization and shutdown.

### Tests for User Story 6

- [x] T033 [P] [US6] Demo tests — concurrent calls do not fail, transactions do not interleave, the finalizer is called for each call, the pool closes on shutdown, and the holder raises a named failure before it is filled — in `packages/aoa-demo/tests/test_identity_postgres.py` (FR-013, FR-038, SC-015)

### Implementation for User Story 6

- [x] T034 [US6] Create the identity resource in `packages/aoa-demo/src/aoa/demo/model/identity/resources/identity_store.py`: a `PostgresResource` subclass with one read method and one transactional method, annotated `pool: PoolProtocol | None` (never the driver), with a stated `acquire_timeout`; the module carries its line-1 path and 79-column sections, the class carries an AI-CORE block, and every method a one-line docstring (FR-036, FR-037; Principles III, IV, V)
- [x] T035 [US6] Create the identity action in `packages/aoa-demo/src/aoa/demo/model/identity/actions/identity_lookup.py` (new package `__init__.py` beside it) declaring `@connection(IdentityStore, key="identity", …)`, and register its route in `packages/aoa-demo/src/aoa/demo/fastapi_mcp_services/actions/__init__.py`; both new modules carry their line-1 path, a `Name — purpose.` first line, 79-column sections, an AI-CORE block on the action class, and one-line docstrings (FR-036; Principles III, IV, V)
- [x] T036 [US6] Add the pool holder to `packages/aoa-demo/src/aoa/demo/fastapi_mcp_services/infrastructure.py`, created only when a DSN is present with `min_size=1, max_size=10` stated at creation and the wait bound stated where the wait happens, with a named failure when read unfilled, and wire the lifespan into `app_fastapi_service.py` and `app_mcp_service.py` through the new adapter option (FR-008, FR-012, FR-013, FR-038)
- [x] T037 [US6] Write the database-free mode and the pattern into `packages/aoa-demo/README.md` and the domain README `packages/aoa-demo/src/aoa/demo/model/identity/README.md`: what the domain demonstrates, the DSN setting's name, and what happens without it (FR-036, FR-037, SC-015)

**Checkpoint**: all six stories are functional; only the tail remains.

---

## Phase 8: Adversarial verification (before the tail)

**Purpose**: prove the new test catches the defect, the way the constitution requires verification —
break the code, watch exactly that test go red, restore.

- [x] T038 Adversarial verification: break `packages/aoa-action-machine/src/aoa/action_machine/resources/postgres/postgres_resource.py` so that **only** the new concurrency test in `packages/aoa-action-machine/tests/action_machine/resources/test_resource_unit_of_work.py` goes red (the sharpest break — make every resource share one connection), confirm exactly that test fails and nothing else newly fails, record both directions, and restore (FR-043, SC-019)

---

## Phase 9: Closing sequence (constitution VI — exactly three tasks, in this order)

**Purpose**: the constitution's last three steps, and nothing else may absorb them. T040 is both the
constitution's documentation step **and** the delivery of User Story 5, which is why it carries the
`[US5]` label; the check run and the changelog are not story work.

- [x] T039 Run `bash scripts/run_checks_with_log.sh` from the repository root and fix **every** remark it reports, to zero; the only remarks allowed to stand are the Vite chunk-size advisory and LangGraph's pending-deprecation warning. Note that this script does **not** run the examples (FR-026, FR-028, SC-013, SC-017, Principle VI, Final step): the check run also proves the scope guards — no new public query method was added anywhere and the home page's read examples are untouched (a `git diff` over the SQL contract and `README.md`), no file under `packages/aoa-maxitor/` changed, and the whole suite is green with no live database
- [x] T040 [US5] Documentation — the constitution's second step, which also delivers User Story 5. In this order: (a) `docs/tutorials/step-17-connections.md` — mode 2 stated as the mandatory pair (factory creates, finalize closes, sync or async, called after the run on success, exception and cancellation) and the two contradictory claims deleted ("a fresh instance per request", "no shared state between requests"); (b) the new section **"A long-lived pool behind a per-call resource"** placed immediately after **"What to choose"**, general rather than Postgres-specific, with the holder, the startup hook, the route, the resource, the three-case table, the invariants, review questions, the two exercises, and a cross-link to `postgresql.md`; (c) `docs/extensions/postgresql.md` — the pool, `open`/`close`, ownership, the transaction on the held connection; (d) `docs/how-to/authoring-resource.md` and `docs/how-to/choosing-action-aspect-resource.md` — closing among the obligations, the two construction forms, the per-call pair; (e) `docs/tutorials/step-19-resource.md` — the wrapper exposes no closing; (f) `packages/aoa-action-machine/src/aoa/action_machine/resources/postgres/__init__.py` — stop drawing a pool the code does not create; (g) extend `examples/step_17_connections/01_connections.py` and `examples/step_19_resource/01_resource.py` with the pool-backed per-call case showing **both** lambdas, migrate the example's one-argument declaration, and keep both notebooks in step; (h) run every touched example and the whole examples runner `uv run pytest tests/examples/test_examples_run.py -q` to a zero exit; (i) sweep for stale fragments (`PostgresResource`, `_conn`, `asyncpg.connect`, `create_pool`, `acquire`, `PerCallConnection`) and fix each; (j) write the Russian drafts beside every page this change writes or substantially rewrites (`*.ru_draft.md`, gitignored) and report both links (FR-029, FR-030, FR-031, FR-032, FR-033, FR-034, FR-035, FR-039, SC-014, SC-016, SC-020, Principle VI points 1–8)
- [x] T041 Changelog — the constitution's third and last step, as **one article** under `## [Unreleased]` in `packages/aoa-action-machine/CHANGELOG.md` with a `### Breaking changes` section naming what replaces the single shared connection and what the constructor now is (pool as a keyword, `rollup` keyword-only); add `aoa-demo`'s own article under `## [Unreleased]` in `packages/aoa-demo/CHANGELOG.md`. **No dated version heading and no version bump** — cutting the release is the maintainer's act. Write in plain words what the work created and the nuances a user needs — no technical detail, no per-file account (FR-040, SC-017, Principle VI point 9)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies.
- **Foundational (Phase 2)**: after Setup; blocks every story.
- **US1 (Phase 3)**: after Foundational; needs T005 (`PoolProtocol`) and T006 (fake pool).
- **US2 (Phase 4)**: after Foundational; the pool tests need US1's `PostgresResource` pool path (T011–T013).
- **US3 (Phase 5)**: after Foundational; independent of US2 in code, but the pool-backed end-to-end check reads best with US2 done.
- **US4 (Phase 6)**: after Foundational; independent of US1–US3 except that the stub-subclass test (T031) wants T034's demo resource to exist — run it after T034 or keep the assertion to the eight stubs.
- **US6 (Phase 7)**: after US1–US3 (it wires the pool and the scope into the demo).
- **Closing (Phases 8–9)**: after everything; T038 (the adversarial proof) precedes the tail, and
  T039–T041 keep the constitution's order: check run, documentation, changelog.

### Within Each Story

Tests are written first and must fail before the implementation (FR-042, FR-043); models before
services; the contract before its driver.

### Parallel Opportunities

- T002 is independent of T001.
- T003 and T004 touch different files and can go together; T005 and T006 too.
- Within US1, the four test tasks (T007–T010) all extend **one** file and are therefore sequential —
  only T007 carries `[P]`, and it is parallel against the other stories' new files, not against
  T008–T010. T011–T013 are one source file and are sequential too.
- Within US2, T015/T016/T017 are three independent test files; T018 and T019 are two packages.
- Within US4, T029–T031 are three independent test files; T032 is one source file.
- Across stories: after Foundational, US1, US2 and US3 can be worked by three people; US4 is
  independent too.

---

## Parallel Example: User Story 1

```bash
# US1's four tests land in one new file, so they are written in order:
Task: "Concurrency test — 30 concurrent units of work, 0 interface errors"
Task: "Transaction-isolation test — two concurrent BEGIN…COMMIT, 0 interleaved statements"
Task: "Exception and cancellation tests — connection returned on both paths"
Task: "Construction tests — both forms and neither raise ConnectionValidationError"

# In parallel with US1, once the pool path exists (three different files):
Task: "Pool-behaviour tests in packages/aoa-action-machine/tests/action_machine/resources/test_pool_bounds.py"
Task: "FastAPI lifecycle test in packages/aoa-fastapi-adapter/tests/test_adapter_lifespan.py"
Task: "MCP lifecycle test in packages/aoa-mcp-adapter/tests/test_adapter_lifespan.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Phase 1 Setup, Phase 2 Foundational (T001–T006).
2. Phase 3, User Story 1 (T007–T014).
3. **STOP and VALIDATE**: the concurrency and isolation tests pass with no database, and the
   adversarial break makes the concurrency test red.
4. That alone fixes the data-corruption defect; the pool is economy, not correctness.

### Incremental Delivery

1. Setup + Foundational → the contract compiles with the eight stubs unedited.
2. US1 → correctness (the defect is gone). Demo it.
3. US2 → the pool and the startup/shutdown option. Demo it.
4. US3 → the mandatory pair and the boundary hook. Demo it.
5. US4 → closing in the contract and the closed wrapper.
6. US6 → the demo, documentation and examples alongside; US5's guidance is the documentation step.
7. Closing sequence → adversarial proof, the check run to zero, the documentation, the changelog.

### Notes

- `[P]` means different files and no dependency on an incomplete task.
- Every test must run with no database; if a test needs one, it is wrong (FR-042, SC-013).
- Never commit, push or open a pull request without an explicit instruction in the current
  conversation (Principle I).
