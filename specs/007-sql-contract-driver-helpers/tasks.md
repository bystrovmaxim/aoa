# Tasks: The query surface leaves the SQL contract, and the driver keeps protected helpers

**Input**: Design documents from `specs/007-sql-contract-driver-helpers/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: included, because the specification's acceptance is a set of searches plus tests that must be red before
the change and green after it (FR-025 … FR-028, SC-001 … SC-018). Every test runs with **no database**: the fake
pool and the fake connection in `packages/aoa-action-machine/tests/support/fake_pool.py` are the instrument, and the
demo's suite keeps its database-free mode (FR-017).

**Organization**: one phase per user story, in priority order. The last three tasks are the constitution's tail, in
its order, and no other task absorbs them: the check run, the documentation, the changelog (Principle VI). Two of
the six stories have no phase of their own — User Story 5 **is** the documentation step and User Story 6 **is** the
changelog step — so their tasks carry `[US5]` and `[US6]` inside the tail rather than moving the tail out of
Principle VI's order. Phases are commit units (house rule: one phase = one commit) — and nothing is committed until
the maintainer instructs it (Principle I).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: different files, no dependency on an incomplete task
- **[Story]**: US1…US6, mapping to `spec.md`
- Every task names the exact file path it touches

## Path Conventions

Repository root is `packages/` + `docs/` + `examples/` + `tests/`. Python packages are
`packages/<pkg>/src/aoa/<pkg>/` with tests in `packages/<pkg>/tests/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: the evidence every later phase is measured against, taken before anything moves.

- [x] T001 Record the branch base `1e4c6b02` and run the four baseline searches from [quickstart.md](./quickstart.md) §1, §7 into the pull-request notes, with their counts: a public `execute` on a SQL shape; a call of it under `packages/*/src`; a page presenting it as the SQL query surface; a store deciding from statement text. The baseline is what makes "0 afterwards" a difference rather than a claim (SC-001, SC-010, SC-013, SC-017) — **done**, recorded with the commands and the counts in [baseline.md](./baseline.md), which becomes the "before" column of the pull request

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the test instrument both later test-bearing stories need.

**⚠️ CRITICAL**: US2's helper tests and US4's demo tests cannot be written without it

- [x] T002 Extend `FakeConnection` in `packages/aoa-action-machine/tests/support/fake_pool.py`: both `execute` and the new `fetchrow` record the statement **and** the positional parameters they were called with (today only the statement is kept), `fetchrow` returns the row it holds or `None`, and the one-operation-at-a-time guard `execute` already enforces stays on both — a second concurrent operation must still raise the interface error (FR-027, quickstart §2) — **done**: the two entry points share one `_operate` guard, `operations` keeps its string-only list and `calls` adds `(statement, parameters)`, and the machine's 2514 tests plus the demo's 60 pass

**Checkpoint**: the fake can make a helper test fail if the helper skips the connection, drops the parameters or loses the check.

---

## Phase 3: User Story 1 — a SQL resource is obliged to offer a lifecycle, not a query passthrough (Priority: P1) 🎯 MVP

**Goal**: the generic query member leaves the structural contract, the base, the nested-action proxy and the
driver's public surface; a subclass needs `open`, `begin` and `rollback` and nothing else; the demo's stubs stop
carrying a member that only ever returned a no-op; and the demo's own write path is repaired with it, because the
removal breaks the caller the demo wrote itself.

**Independent Test**: instantiate a SQL resource subclass that implements `open`, `begin` and `rollback` only; run
the machine's own suite; and run the source searches — no public query member on a SQL resource under `packages/`
(SC-001, SC-002, SC-011).

### Tests for User Story 1 (write first, confirm they fail before the implementation)

- [x] T003 [P] [US1] In `packages/aoa-action-machine/tests/action_machine/resources/test_sql_resource.py`: delete the "subclass missing `execute` cannot be instantiated" case; drop the member from `_TestConnectionManager` (:73) and `_NoSuperInitManager` (:105); run the lifecycle cases (:299-345) on `begin`/`commit`/`rollback` alone, dropping the recorded-statement assertions; add the guard that none of `ProtocolSqlResource`, `SqlResource` and `WrapperSqlResource` exposes a query member (FR-004, FR-025, SC-002)
- [x] T004 [P] [US1] In `packages/aoa-action-machine/tests/action_machine/resources/test_wrapper_sql_resource.py`: drop `execute` from `MockConnectionManager` (:95, :109); replace the three delegation cases (:272-300) with absence cases asserting `hasattr` is false for `execute`, `_execute` and `_fetchrow`; keep the refusals, `isinstance(wrapper, ProtocolSqlResource)` and the double and triple wrap (FR-011, FR-012, FR-025, SC-006)

### Implementation for User Story 1

- [x] T005 [P] [US1] Drop the `execute` member (:76) from `packages/aoa-action-machine/src/aoa/action_machine/resources/sql/protocol_sql_resource.py`, correct the `PURPOSE` sentence (:12) and the AI-CORE `CONTRACT` key (:43) (FR-001; Principles III, IV)
- [x] T006 [P] [US1] Drop the abstract `execute` (:148) from `packages/aoa-action-machine/src/aoa/action_machine/resources/sql/sql_resource.py`, correct the contract line (:11), the rollup walk-through that writes statements through it (:52-53) and the architecture diagram (FR-002; Principles III, IV)
- [x] T007 [P] [US1] Drop the delegating `execute` (:133-137) from `packages/aoa-action-machine/src/aoa/action_machine/resources/sql/wrapper_sql_resource.py` and correct its one-line description (:13) and diagram (:38); every refusal, `rollup` delegation and `get_wrapper_class()` (:140) stays (FR-003, FR-011; Principles III, IV)
- [x] T008 [US1] Rename `execute` to `_execute` in `packages/aoa-action-machine/src/aoa/action_machine/resources/postgres/postgres_resource.py` (:223-241) and correct the module diagram (:32); the check and the wrap it already has move with the rename unchanged — this phase removes the public member, US2 makes the check single. **After T006**: while the base still declares the member abstract, renaming it here leaves the driver abstract and every test that constructs it fails (FR-001, FR-004; Principles III, IV)
- [x] T009 [P] [US1] Drop the member and the `Any` import that existed only for it from the eight demo stubs: `packages/aoa-demo/src/aoa/demo/model/catalog/resources/search_sidecar.py`, `catalog/resources/object_store.py`, `messaging/resources/dlq_store.py`, `messaging/resources/outbox_primary.py`, `billing/resources/warehouse.py`, `billing/resources/read_replica.py`, `store/resources/db.py`, `store/resources/cache.py` (FR-014, SC-011)
- [x] T010 [US1] Correct the contract note (:19) and the module map (:38) in `packages/aoa-action-machine/tests/action_machine/resources/__init__.py` (FR-025; Principle III)
- [x] T011 [US1] Migrate every call site the removal breaks in the machine's own tests to `_execute`, keeping every assertion the previous feature wrote: the five at `packages/aoa-action-machine/tests/action_machine/resources/test_resource_unit_of_work.py:80`, `:171`, `:172`, `:203`, `:252` and the one at `packages/aoa-action-machine/tests/action_machine/resources/test_pool_bounds.py:45` (FR-026, SC-013)
- [x] T012 [P] [US1] In `packages/aoa-demo/tests/test_sql_resource_stubs.py`, assert the eight stubs satisfy the contract and close harmlessly now that the member is gone from them; the test keeps naming the eight existing stubs only (FR-014, SC-011)

- [x] T013 [US1] Repair the demo's write path, which the removal breaks: `packages/aoa-demo/src/aoa/demo/model/identity/resources/identity_store_base.py` declares `_write_login(person_id, at) -> None` as the primitive `record_login` calls; `identity_store.py` implements it through `_execute`; `identity_store_stub.py` implements it in memory and loses its `execute` and the statement-text test at :69 with it (SC-017); `packages/aoa-demo/tests/test_identity_postgres.py` drives that primitive inside the transaction the interleaving test owns, and the demo's own `_FakeConnection` records the parameters of a statement so the two units remain tellable apart. The read reshape stays in US4, which needs `_fetchrow` (FR-016, FR-024, SC-017, DH-6.1, DH-6.2)

**Checkpoint**: no public query member exists anywhere under `packages/`, the suite is green, and a subclass needs
three members. This alone is the MVP: the obligation the issue names is gone.

---

## Phase 4: User Story 2 — a domain resource runs statements through the driver's protected helpers (Priority: P2)

**Goal**: one protected statement path, one protected row path, one "connection is open" check, one error policy —
so a domain method carries business meaning and no transport mechanics. The example scripts the removal broke are
migrated here, with the change that broke them, instead of staying red until the documentation step.

**Independent Test**: call each helper on a resource that never opened and on one already closed, and get
`HandleError("Connection is not open")` rather than an attribute error; make the connection fail and get `HandleError`
with the driver's error chained; run a statement and a read and get the status and the row; run the examples runner
and get a zero exit (SC-003, SC-004, SC-005, SC-009).

### Tests for User Story 2

- [ ] T014 [US2] Create `packages/aoa-action-machine/tests/action_machine/resources/test_postgres_helpers.py` driving `PostgresResource` over the fake pool, carrying the first-line path comment and the module docstring its neighbours carry: both helpers on a never-opened and on a closed resource raise the named failure; a connection that refuses a statement yields `HandleError` whose `__cause__` is the driver's error; parameters reach the connection positionally and `None` and `()` behave alike; `_fetchrow` returns the row and `None` (FR-010, FR-027, SC-003, SC-004)

### Implementation for User Story 2

- [ ] T015 [US2] Add `_require_connection` to `packages/aoa-action-machine/src/aoa/action_machine/resources/postgres/postgres_resource.py` and route `begin` (:146), `commit` (:167), `rollback` (:182) and `_execute` (:238) through it, so the check is written once; the lifecycle messages (`BEGIN failed: …`, `COMMIT failed: …`, `ROLLBACK failed: …`) stay exactly as they are (FR-006, SC-005, DH-2.1, DH-2.3)
- [ ] T016 [US2] Add `_fetchrow` beside `_execute` in `packages/aoa-action-machine/src/aoa/action_machine/resources/postgres/postgres_resource.py`, both with their one-line docstrings and one message, `SQL execution failed: …`, raising `HandleError` with the driver's error chained as `__cause__` (FR-005, FR-007, FR-010, DH-1.2, DH-3.1, DH-3.2; Principle V)
- [ ] T017 [US2] Update the module header and the AI-CORE block of `packages/aoa-action-machine/src/aoa/action_machine/resources/postgres/postgres_resource.py` so the diagram and the `CONTRACT` key name the two helpers as the extension point, and state that `_fetchrow` answers the *first* row (Principles III, IV; DH-1.5)
- [ ] T018 [US2] Migrate every example the removal broke, with its notebook, and run the runner: `examples/extensions/postgresql/02_concurrent.py`, `04_commit.py`, `05_rollback.py` and `07_rollup.py` reach the connection through a semantic method over the helpers; `14_failed_commit.py` overrides `_execute` instead of the removed member; `examples/step_17_connections/16_pool_lifespan.py` calls a semantic method; `examples/step_19_resource/07_nested_action.py` is repaired to the same shape (its domain wrapper follows in US3); and `examples/step_19_resource/04_wrapper_execute.py` with its notebook is **deleted**, because its whole subject — the proxy running a query — no longer exists, leaving a gap in the numbering rather than renaming every later case. Rebuild each notebook from the same blocks as its script, run every touched script, and finish with `uv run --extra dev pytest tests/examples -v` at a zero exit (FR-022, FR-023, SC-009, SC-018)

**Checkpoint**: every failure a domain method can meet has one name, the check is written once, and the examples
runner is green again — from here it stays green.

---

## Phase 5: User Story 3 — a nested action cannot reach the connection at all (Priority: P3)

**Goal**: the proxy offers nothing to run a statement with — by construction — and a domain that wants to hand a
nested action something declares its own wrapper that delegates its own semantic methods.

**Independent Test**: build a proxy and confirm no query member of any kind is reachable on it while every lifecycle
operation is refused and the contract still holds; then build a domain wrapper that delegates one semantic method
and confirm the nested path works through two and three levels while the lifecycle stays refused (SC-006, SC-007).

### Tests for User Story 3

- [ ] T019 [US3] Extend `packages/aoa-action-machine/tests/action_machine/resources/test_wrapper_sql_resource.py` with the domain-wrapper case: a resource whose `get_wrapper_class()` returns its own wrapper, that wrapper delegating one semantic method and refusing `open`/`begin`/`commit`/`rollback`/`close` and context-manager use; an error raised by the delegated method arrives as the domain's own error with the cause chained; the same holds at two and three levels of wrapping (FR-012, FR-013, FR-027, SC-007, NA-3.1, NA-3.2, NA-3.4)

### Implementation for User Story 3

- [ ] T020 [US3] Enrich `examples/step_19_resource/07_nested_action.py` and its notebook: `NotesResource` gains one semantic method built on the driver's protected helper and overrides `get_wrapper_class()` with a wrapper class that delegates that method and refuses the lifecycle; the child action calls it successfully and its `close` attempt still ends in `TransactionProhibitedError`, so the case shows both halves (FR-013, FR-022, NA-3.1, NA-3.2, NA-4.2)

**Checkpoint**: nested access is impossible by default and possible only where a domain declares it, and the case
that shows it runs.

---

## Phase 6: User Story 4 — the demo lives the pattern, and still runs without a database (Priority: P4)

**Goal**: the identity domain states its two operations once on a driver-free base and its read becomes one row — a
person or nothing, through the driver's row helper in PostgreSQL and from memory without a driver — so the demo
installs, imports and passes its suite with no PostgreSQL and no driver extra. Its write primitive already landed
in US1, which is the phase that broke its caller.

**Independent Test**: run the demo's suite with no DSN and no database; read the identity store and confirm the read
goes through the row helper, the write through the statement helper, and that no store inspects statement text
(SC-008, SC-017).

### Tests for User Story 4

- [ ] T021 [P] [US4] Update `packages/aoa-demo/tests/test_identity_postgres.py` for the reshaped read: it answers one person or `None` through the row helper, and the read on a closed resource raises `HandleError("Connection is not open")` rather than the base's own error. The write path and the interleaving test's call site already moved in US1, and the write still commits inside the transaction `record_login` owns (FR-016, FR-027, SC-008)

### Implementation for User Story 4

- [ ] T022 [US4] Give `packages/aoa-demo/src/aoa/demo/model/identity/resources/identity_store_base.py` its read primitive — `_read_person(person_id) -> dict[str, Any] | None`, declared abstract beside the write one that landed in US1 — and rewrite `read_person` on top of it so it answers one person or nothing; the transaction stays in `record_login`, where US1 left it; correct the AI-CORE `CONTRACT` key (:54) and the diagram (:30) (FR-009, FR-015, DH-6.1; Principles III, IV)
- [ ] T023 [US4] Rewrite the read half of `packages/aoa-demo/src/aoa/demo/model/identity/resources/identity_store_stub.py`: implement `_read_person` over the dictionaries, keep the lifecycle members harmless, and leave the write primitive US1 added (which is also where `execute` and its statement-text test went) (FR-016, SC-017, DH-6.1)
- [ ] T024 [US4] Rewrite the read primitive in `packages/aoa-demo/src/aoa/demo/model/identity/resources/identity_store.py`: `_read_person` through `_fetchrow` with the record converted to a plain mapping, the module's own `RuntimeError` check (:55-56) deleted so a closed resource yields the framework's named failure, and the write primitive US1 added left as it is (FR-016, DH-6.1, DH-6.2)
- [ ] T025 [US4] Update `packages/aoa-demo/src/aoa/demo/model/identity/actions/identity_lookup.py` (:94-105) for the reshaped read: one row instead of a list, `found` decided by `is None`, and the route's answer unchanged (FR-015)
- [ ] T026 [P] [US4] Update `packages/aoa-demo/README.md` and `packages/aoa-demo/src/aoa/demo/model/identity/README.md`: the domain's two operations, the shape its read answers in, the helpers it uses, and the database-free mode (FR-017, SC-008)

**Checkpoint**: the pattern a reader copies is in the demo, and the demo still needs no database.

---

## Phase 7: Adversarial verification (before the tail)

**Purpose**: prove the new tests catch what they exist for — break the code, watch exactly those go red, restore
(FR-028, SC-015).

- [ ] T027 Break the code three times, one at a time, from a byte-for-byte backup, and record both directions: (a) add a delegating `execute` back to `packages/aoa-action-machine/src/aoa/action_machine/resources/sql/wrapper_sql_resource.py` — expect the absence tests in `test_wrapper_sql_resource.py` red and nothing else; (b) make `_require_connection` return `self._conn` without testing it in `packages/aoa-action-machine/src/aoa/action_machine/resources/postgres/postgres_resource.py` — expect the closed-resource tests in `test_postgres_helpers.py` and the demo's closed-resource test red; (c) raise `HandleError` without `from e` in the helper — expect exactly the cause assertion red. After each restore, `diff -q` against the backup is clean and the suite is green (FR-028, SC-015)

---

## Phase 8: Closing sequence (constitution VI — exactly three tasks, in this order)

**Purpose**: the constitution's last three steps, and nothing else may absorb them (FR-031). The documentation task
carries `[US5]` and the changelog task carries `[US6]`, because each of those stories *is* that step; the check run
is not story work. Nothing in this phase is reordered except by the maintainer's instruction.

- [ ] T028 Run `bash scripts/run_checks_with_log.sh` from the repository root and fix **every** remark it reports, to zero; the only remarks allowed to stand are the Vite chunk-size advisory and LangGraph's pending-deprecation warning. This script does **not** run the examples (quickstart §6 — the runner is a separate gate), so the run is paired with what it cannot see: the examples runner of T018 and the scope guards and sweeps — no public query member was added anywhere under `packages/`; nothing under `packages/aoa-maxitor/` changed; the four baseline searches of T001 now return 0 (or only the deliberately untouched pages); the count of stores deciding from statement text is 0; and every suite is green with no live database (FR-008, FR-024, SC-001, SC-005, SC-010, SC-012, SC-013, SC-016, SC-017, Principle VI, Final step)
- [ ] T029 [US5] Documentation — the constitution's second step, which also delivers User Story 5. In this order: (a) `docs/tutorials/step-19-resource.md` — delete the section `## A wrapper can execute a statement` (:225) and its notebook links, state in `## A wrapper for nested operations` (:209) that the proxy offers nothing to run a query with, and show the domain wrapper in `## A real nested action receives a restricted view` (:324) as the case now runs; (b) `docs/extensions/postgresql.md` — replace the query-surface paragraph (:35) with the two helpers and their semantics (the row helper answers the first row), and stop saying at :650 that the wrapper delegates the member; (c) `docs/how-to/authoring-resource.md` — name the helpers as how a domain runs a statement and reads a row, with the deliberate wrapping pattern, and correct :118 so the proxy delegates nothing; (d) `docs/how-to/choosing-action-aspect-resource.md` — the proxy paragraph (:50) stops claiming the proxy executes commands; (e) root `README.md` — the resource example (:604-618) shows a semantic method over the helper; (f) confirm against FR-029 that every case the feature introduces is shown by a script **and** its notebook, naming the ones that already carry a case — `examples/step_17_connections/03_without_open.py` (a resource that was never opened), `04_failed_call.py` (a failing unit of work), `08_close_failure.py` (a failing close) — and add a case only where one of FR-029's shapes (the driver's helpers, the closed-resource failure, a driver failure wrapped by a domain method, the proxy with nothing to call, the domain wrapper) has no home; the scripts themselves were migrated in T018 and T020, so only genuine gaps are filled here; (g) check `docs/how-to/migrating-legacy.md:42` and correct it only if it presents the removed member as the framework's query surface, leaving the unrelated ledger and OCEL members untouched; (h) run every touched example and the whole examples runner `uv run --extra dev pytest tests/examples -v` to a zero exit; (i) update the Russian drafts beside the four pages that have one and report both links; (j) sweep for stale fragments (`execute(query`, `delegates execute`, `super().execute`) across `docs/` and `examples/` (FR-018, FR-019, FR-020, FR-021, FR-022, FR-023, FR-024, FR-029, SC-009, SC-013, SC-018, SC-020, Principle VI points 4-7)
- [ ] T030 [US6] Changelog — the constitution's third and last step, as **one article** under `## [Unreleased]` in `packages/aoa-action-machine/CHANGELOG.md` with a `### Breaking changes` section stating that the generic query member left the public SQL contract and naming both replacements: the protected helpers on the driver a domain resource holds, and the resource's own public method for anyone who still wants a passthrough. Add the demo's own short `### Breaking changes` entries under `## [Unreleased]` in `packages/aoa-demo/CHANGELOG.md` for what its public surface lost (`IdentityStoreStub.execute`, the read's shape). **No dated version heading and no version bump** — cutting the release is the maintainer's act. Plain words, no technical detail, no per-file account (FR-030, SC-014, Principle VI point 9)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies; it records the baseline everything is measured against.
- **Foundational (Phase 2)**: after Setup; blocks US2's helper tests and US4's demo tests.
- **US1 (Phase 3)**: after Foundational; it is the removal, and every later story assumes it. It carries the demo's
  write path too (T013), because the removal breaks the demo's own caller and a phase that left it broken would not
  be a commit. Within it, **T008 requires T006**: the base must stop declaring the member abstract before the
  driver renames it, or the driver becomes abstract and every test that constructs it fails.
- **US2 (Phase 4)**: after US1 — the path it polishes is the renamed member, and the example migration (T018) is the
  repair of what US1 broke.
- **US3 (Phase 5)**: after US2; the domain-wrapper test (T019) and the enrichment (T020) work with the helpers
  present.
- **US4 (Phase 6)**: after US2 — the demo's primitives are the helpers' only callers, and the reshape of the read is
  what keeps the helper set at two.
- **Adversarial (Phase 7)**: after US1–US4; it breaks code all four stories produced.
- **Closing (Phase 8)**: after everything; T028 → T029 → T030 is the constitution's order and is not permuted. The
  examples runner is green from T018 onwards, and both T028 and T029(h) re-run it.

### Within Each Story

Tests are written first and must fail before the implementation (FR-027, FR-028); the contract before its driver;
the base's primitives before each store; the store before the action that reads it; a broken example is repaired in
the phase that broke it, not in the documentation step.

### Parallel Opportunities

- T003 and T004 are two different test files and can be written together.
- T005, T006, T007 and T009 touch four disjoint sets of files; T008 touches the driver alone but depends on T006.
- T021 and T026 are different files; T022 → T023/T024 → T025 are one domain and are sequential (the base's shape is
  what the stub, the store and the action follow).
- Across stories: after US1, US2 and US3 can be worked by two people (US3's test touches a file US1 also edited, so
  it starts after T004 lands).

---

## Parallel Example: User Story 1

```bash
# Two test files, written first and expected to fail:
Task: "T003 rewrite the contract and lifecycle cases in test_sql_resource.py"
Task: "T004 replace the delegation cases with absence cases in test_wrapper_sql_resource.py"

# Three disjoint source files, in parallel (T008 follows T006):
Task: "T005 drop the member from protocol_sql_resource.py"
Task: "T006 drop the abstract member and fix the prose in sql_resource.py"
Task: "T007 drop the delegating member and fix the prose in wrapper_sql_resource.py"
Task: "T009 drop the member and the Any import from the eight demo stubs"
```

## Parallel Example: User Story 4

```bash
# Independent files once the base's primitives are fixed (T022):
Task: "T023 rewrite the in-memory store without the statement-text test"
Task: "T024 rewrite the PostgreSQL store onto the helpers"
Task: "T026 update the demo's own READMEs"

# Then, one file:
Task: "T025 switch the action to the single-row read"
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Phase 1 Setup and Phase 2 Foundational (T001–T002).
2. Phase 3, User Story 1 (T003–T012).
3. **STOP and VALIDATE**: the searches return nothing, a three-member subclass instantiates, and every suite is green
   with no database — the machine's, the demo's, and the five others. The obligation the issue names is gone, and the
   demo's write path was repaired in the same phase because the removal broke it. The examples runner is still red at
   this point, deliberately and for one phase only: US2 repairs it.

### Incremental Delivery

1. US1 → the contract obliges a lifecycle; the demo's stubs shrink. Demo it.
2. US2 → the two helpers with one check and one error name, and the examples green again. Demo it.
3. US3 → nested access by construction, and the domain wrapper that replaces the deleted case. Demo it.
4. US4 → the demo's identity domain on the helpers, still database-free. Demo it.
5. Adversarial verification → the three breaks, both directions recorded.
6. Closing sequence → the check run to zero, the documentation with its Russian drafts, the changelog.

### Notes

- `[P]` means different files and no dependency on an incomplete task.
- Every test runs with no database; a test that needs one is wrong (SC-008, SC-013).
- The helpers are exactly two and each has a caller under `packages/` — a third added "for completeness" is a defect
  of this change, not a courtesy (FR-008, DH-5.2).
- Never commit, push or open a pull request without an explicit instruction in the current conversation
  (Principle I).
