# Tasks: A domain reads all rows and one value through the driver's protected helpers

**Input**: Design documents from `specs/008-driver-fetch-helpers/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: included, because the specification's acceptance is behavioural (FR-001 … FR-010, FR-015 … FR-019) and the
issue asks for checks on the closed resource, the chained failure, the empty and several-row answers and the
parameter shapes. Every check runs with **no database**: the fake pool in
`packages/aoa-action-machine/tests/support/fake_pool.py` and the demo's own fake in
`packages/aoa-demo/tests/test_identity_postgres.py` are the instruments. Tests are written first and confirmed red
before the helper they cover exists.

**Organization**: one phase per user story, in priority order. The last phase is the constitution's tail, in its
order, and no other task absorbs it: the check run, the documentation, the changelog (Principle VI). User Story 5 is
verification and documentation, so its tasks carry `[US5]` inside the verification phase and inside the tail rather
than moving the tail out of order. Phases are commit units (house rule: one phase = one commit) — and nothing is
committed until the maintainer instructs it (Principle I).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: different files, no dependency on an incomplete task
- **[Story]**: US1…US5, mapping to `spec.md`
- Every task names the exact file path it touches

## Path Conventions

Repository root is `packages/` + `docs/` + `examples/` + `tests/`. Python packages are
`packages/<pkg>/src/aoa/<pkg>/` with tests in `packages/<pkg>/tests/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: the evidence every later phase is measured against, taken before anything moves.

- [x] T001 Record the baseline in `specs/008-driver-fetch-helpers/baseline.md`: the branch base `fe4c460e`, `asyncpg` 0.31.0, package version `1.0.1a4`, the two suite counts measured before the change (`test_postgres_helpers.py` 7 passed; `packages/aoa-demo/tests` 69 passed), and the four searches with their outputs — no `def _fetch`/`def _execute` in `packages/aoa-action-machine/src/aoa/action_machine/resources/sql/*.py`; exactly two query helpers on the driver; neither `_fetch` nor `_fetchval` on `WrapperSqlResource`; no `_fetchmany`/`_executemany`/`_fetchval_or`/`_fetchrow_or` among the driver's members, with the wide search's 36 hits classified rather than excused (all of them a module-level `_executemany` in Maxitor's `duckdb_graph_resource.py`, another resource's own helper). The baseline is what makes "four afterwards" a difference rather than a claim (SC-006, SC-009, SC-010; quickstart §1, §6) — **done**: [baseline.md](./baseline.md) carries every command with its output, and the wide forbidden-family search is classified there rather than claimed as a zero

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the test instrument the helper and demo phases run on.

**⚠️ CRITICAL**: no helper test can assert an answer, an empty result or a parameter until the fake can answer a page and a value.

- [x] T002 Extend `FakeConnection` in `packages/aoa-action-machine/tests/support/fake_pool.py`: a `rows: list[Any]` and a `value: Any` holding what the next read answers; async `fetch(query, *args)` returning `list(self.rows)` and async `fetchval(query, *args)` returning `self.value`, both going through the existing `_operate` guard so the one-operation-at-a-time rule and the closed check still apply, and both recording `(query, args)` in `calls`; each new method carries its one-line docstring, as the fake's existing methods do; update the module docstring's account of what the fake answers and keep `__all__` (FR-019; Principle V; quickstart §2). The machine's existing 7 helper tests must stay green afterwards — **done**: `rows` and `value` are set by the test, `fetch` answers a copy of `rows`, `fetchval` answers `value`, both record through the same `_operate` guard, and the 7 tests still pass

**Checkpoint**: the fake can make a helper test fail if the helper skips the connection, drops the parameters, returns a row instead of a list, or returns a row instead of a value.

---

## Phase 3: User Story 1 — a domain answers a page of rows (Priority: P1) 🎯 MVP half

**Goal**: a private read on a domain resource reaches the database once and receives every row in the driver's order,
with an empty list when nothing matched, without seeing the connection or the "is it open" check.

**Independent Test**: run the new cases in `test_postgres_helpers.py` — `[]` for no match, a list of one for one row,
all rows in order with and without `ORDER BY`, parameters forwarded — and confirm the existing suite is still green
(SC-001, SC-005).

### Tests for User Story 1 (write first, confirm they fail before the implementation)

- [x] T003 [US1] In `packages/aoa-action-machine/tests/action_machine/resources/test_postgres_helpers.py`, add the `_fetch` cases and extend the module docstring's scenario list: no match answers `[]` (not `None`); one row arrives as a list of one (not the row); several rows arrive as all of them in the driver's order, checked both with an `ORDER BY` in the statement and without one and asserting the helper neither sorts nor truncates; the statement's parameters reach the connection positionally; `None` and `()` produce the same recorded call (FR-001, FR-002, FR-007, FR-019; SC-001, SC-005). Run the module and confirm the new cases fail for the missing member — **done**: 5 failed with `AttributeError: 'PostgresResource' object has no attribute '_fetch'` while the 7 existing cases stayed green

### Implementation for User Story 1

- [x] T004 [US1] Add `_fetch` to `packages/aoa-action-machine/src/aoa/action_machine/resources/postgres/postgres_resource.py`, directly after `_fetchrow`: `async def _fetch(self, query: str, params: tuple[Any, ...] | None = None) -> list[Any]`, the connection taken only from `self._require_connection()`, `rows: list[Any] = await conn.fetch(query, *params if params else ())`, and `except Exception as e: raise HandleError(f"SQL execution failed: {e}") from e`; the multi-line docstring states purpose, `Args`, `Returns` (every row, driver order, `[]` for no match, one row is a list of one) and `Raises` (FR-001, FR-002, FR-005, FR-006, FR-008, FR-010; contracts/fetch-helpers.md FH-1.1, FH-1.2, FH-2.1, FH-3.1; Principle V) — **done**: after the member landed the module is 12 passed, and the adversarial break that returns `self._conn.row` instead of the rows fails exactly the three answer-shape cases (empty, list of one, every row), leaving the two parameter cases green

**Checkpoint**: the page path works and can be read off the code; the two `_fetchval`-shaped cases still fail to exist.

---

## Phase 4: User Story 2 — a domain answers one value (Priority: P2) 🎯 MVP half

**Goal**: a private read asks for one number and receives the first value of the first row — not a row, not a tuple —
with nothing for no match, and the docstring says that a SQL `NULL` and "no row" cannot be told apart through it.

**Independent Test**: run the new `_fetchval` cases — the scalar rather than the row, `None` for no match, `None` for a
matched row whose first value is `NULL` — and confirm they pass and the rest of the module stays green (SC-002).

### Tests for User Story 2

- [x] T005 [US2] In `packages/aoa-action-machine/tests/action_machine/resources/test_postgres_helpers.py`, add the `_fetchval` cases: the answer is the first value of the first row, not the row and not a tuple containing it; no match answers `None`; a row whose first value is `None` answers `None` too, with a comment naming the documented ambiguity; the parameters are forwarded exactly as for the other three helpers (FR-003, FR-004, FR-007, FR-010; SC-002). Extend the module docstring's scenario list with the value-helper cases, as T003 does for the page. Confirm the new cases fail before the member exists — **done**: 4 failed with `AttributeError: … has no attribute '_fetchval'. Did you mean: '_fetch'?` while the other 12 stayed green

### Implementation for User Story 2

- [x] T006 [US2] Add `_fetchval` beside `_fetch` in `packages/aoa-action-machine/src/aoa/action_machine/resources/postgres/postgres_resource.py`: `async def _fetchval(self, query: str, params: tuple[Any, ...] | None = None) -> Any`, the same check and the same wrapping, `value: Any = await conn.fetchval(query, *params if params else ())`; the docstring states that the answer is the first value of the first row, that no match answers `None`, and that a matched row whose first value is `NULL` is indistinguishable through this helper (FR-003, FR-004, FR-005, FR-006, FR-010; FH-1.3, FH-1.4; Principle V) — **done**: the module is 16 passed and the resources suite 138; the adversarial break that answers the row instead of its value fails the two cases that tell them apart (the scalar and the `NULL`/no-row pair) and leaves the parameter case green

**Checkpoint**: both new paths exist and their acceptance cases are green. Together with US3 this is the MVP the issue asks for — half a pair would not satisfy it.

---

## Phase 5: User Story 3 — the pair behaves exactly like the helpers it joins (Priority: P3)

**Goal**: one check, one message, one parameter shape and one kind of annotation across all four helpers; exactly four
query members on the driver and none on the wrapper; and the module documentation names the four rather than two.

**Independent Test**: run the full helper module — closed and never-opened resources, the chained driver failure, the
annotation, the exact member set, the wrapper's absence — and confirm all four helpers answer identically on every
path the existing pair is checked on (SC-003, SC-004, SC-005, SC-006).

### Tests for User Story 3

- [x] T007 [US3] In `packages/aoa-action-machine/tests/action_machine/resources/test_postgres_helpers.py`, add the shared-policy cases: both new helpers on a resource that never opened and on one closed after opening raise `HandleError("Connection is not open")` and no `AttributeError`; a refusing connection yields `HandleError` with the driver's error in `__cause__` for both; the return annotations of `_fetch` and `_fetchval` contain `list[Any]` and `Any` respectively and no `asyncpg` name; the driver exposes exactly the four query members and none of `_fetchmany`, `_executemany`, `_fetchval_or`, `_fetchrow_or`; `WrapperSqlResource` has neither `_fetch` nor `_fetchval` (FR-005, FR-006, FR-008, FR-009, FR-013; SC-003, SC-004, SC-006; contracts/sql-surface.md SS-1.1 … SS-1.4) — **done**: six cases added (never-opened, closed, chained cause, annotations, exact member set, wrapper absence); the module is 22 passed, the resources suite 144; the break that reads `self._conn` instead of `_require_connection()` fails exactly the never-opened and closed cases with `SQL execution failed: 'NoneType' object has no attribute 'fetch'`

### Implementation for User Story 3

- [x] T008 [US3] Correct the documentation inside `packages/aoa-action-machine/src/aoa/action_machine/resources/postgres/postgres_resource.py`: the module's `ARCHITECTURE / DATA FLOW` diagram gains `_fetch()` (every row) and `_fetchval()` (one value) beside the existing pair; the class's AI-CORE `CONTRACT` key names the four protected query members; the `_execute` docstring's "a subclass that reads rows uses `_fetchrow`" names both read helpers and when to choose between them (FR-011, FR-012; FH-5.3; Principles III, IV) — **done**: the diagram carries `_fetch()` and `_fetchval()`, the AI-CORE `CONTRACT` names the four as one per driver answer, and the `_execute` docstring now says `_fetch` for all rows, `_fetchrow` for the first

**Checkpoint**: the driver is one coherent extension point of four members, documented as such, and the contract and wrapper provably did not grow.

---

## Phase 6: User Story 4 — the demo's store calls both helpers in its own private reads (Priority: P4)

**Goal**: `IdentityStore` gains `_list_persons` through `_fetch` and `_count_persons` through `_fetchval`; the
driver-free base and the in-memory store do not change; the demo's suite is their caller and still needs no database.

**Independent Test**: run the demo suite with no database and confirm the list answers ordered mappings with a bound,
the count answers an int, and the faked connection recorded `fetch` and `fetchval` rather than being bypassed
(SC-007, SC-008).

### Tests for User Story 4

- [x] T009 [US4] In `packages/aoa-demo/tests/test_identity_postgres.py`, extend `_FakeConnection` with `rows` and `value` and the async `fetch`/`fetchval`, each with its one-line docstring, recording `(query, args)` through its existing `_operation` guard and seeded with person records; add cases that the list read answers plain `dict`s, that its recorded statement carries `ORDER BY display_name, id` and `LIMIT`/`OFFSET` with the parameters arriving positionally, that the count read answers an `int`, and that both calls are the ones the fake recorded (FR-015 … FR-017, FR-019; SC-007, SC-008; contracts/demo-reads.md DR-3.1 … DR-3.3). Confirm the new cases fail before the reads exist — **done**: 4 failed with `AttributeError` for the missing reads while the 8 existing cases stayed green; the fake now seeds `rows`/`value` and answers `fetch`/`fetchval` through the same `_operation` guard

### Implementation for User Story 4

- [x] T010 [US4] Add the two private reads to `packages/aoa-demo/src/aoa/demo/model/identity/resources/identity_store.py`: `_list_persons(limit: int = 20, offset: int = 0) -> list[dict[str, Any]]` calling `_fetch` with `SELECT id, email, display_name FROM identity_person_hub ORDER BY display_name, id LIMIT $1 OFFSET $2` and mapping each row with `dict(...)`; `_count_persons() -> int` calling `_fetchval` with `SELECT count(*) FROM identity_person_hub` and answering `0 if total is None else int(total)`; both get one-line docstrings, and the module's data-flow diagram names them (FR-015, FR-016, FR-017, FR-018; DR-1.1 … DR-1.4; Principle V). `identity_store_base.py` and `identity_store_stub.py` are not touched (DR-2.1, DR-2.2) — **done**: the page runs `ORDER BY display_name, id LIMIT $1 OFFSET $2` and maps records with `dict(...)`, the count runs `SELECT count(*) FROM identity_person_hub` and answers `0 if total is None else int(total)`; the module diagram names both reads; the base and the stub are unchanged

- [x] T011 [P] [US4] Update `packages/aoa-demo/src/aoa/demo/model/identity/README.md`: state what the PostgreSQL store reads now — the row, the page and the count — and through which helper each goes, keeping the driver-free base described as two operations (FR-020; DR-2.3, DR-2.4) — **done**: the table names the two private reads, a paragraph says they are storage reads rather than domain operations with no route publishing them, and the test list now names the page, the count and the zero

- [x] T012 [US4] Run `packages/aoa-demo/tests` with no database and no `postgres` extra import at module load, and confirm the previous 69 cases plus the new ones are green (SC-008). If the demo's suite needs the extra for the import, that is a defect in the case, not a reason to add a dependency — **done**: 73 passed (the previous 69 plus 4), no database, and the driver import stays behind `pytest.importorskip` in the cases that need it

**Checkpoint**: each new helper has a caller inside `packages/`, the demo still runs with no database, and the demonstration did not grow a public operation, an action or a route.

---

## Phase 7: Verification (cross-cutting, before the tail)

**Purpose**: prove the change is what the issue and the contracts say, and that the new checks catch the defects they
exist for.

- [x] T013 [P] [US5] Run the contract searches from [quickstart.md](./quickstart.md) §1 and §6 and record them as the "after" column of `specs/008-driver-fetch-helpers/baseline.md`: exactly four `async def _execute|_fetchrow|_fetch|_fetchval` lines in the driver; no forbidden convenience member on the driver — the wide search's 36 Maxitor hits are the same unrelated module-level function and must be unchanged; no `def _fetch|def _execute` in `resources/sql/*.py`; `WrapperSqlResource` has neither new member; and `test_sql_resource.py` plus `test_wrapper_sql_resource.py` pass **unedited** (FR-013, FR-014, FR-009; SC-006, SC-011, SC-012) — **done**: measured and recorded in `baseline.md` §"After": S1 0, S2 4 (`:231`, `:255`, `:279`, `:303`), S3 0, S4 0 with the wide 36 unchanged, S5 0, S6 10 mentions (two members, two reads); the two contract suites carry no diff and pass at 65

- [x] T014 Run the adversarial breaks in [quickstart.md](./quickstart.md) §8 one at a time, confirming that exactly the named cases fail and no others, then restoring each file and re-running to green: `_fetch` returns `self.row`; `_fetchval` returns the row; both read `self._conn` directly; the driver error is raised unwrapped; `params` is passed as one argument; the wrapper gains a delegating `_fetch`; the demo's list read drops `ORDER BY`/`LIMIT`; the demo's count read returns the record (SC-001 … SC-008; the repository's rule that verification is adversarial) — **done**: all eight run and restored, each failing exactly its named cases — 3 (page answers), 2 (value vs row), 2 (the connection check), 1 (the wrap), 3 (parameters), 1 (the wrapper), 1 (the demo page), 2 (the demo count). The parameter break was measured at **three**, not two: `((),)` is not `()`, so the `None`/`()` equality case falls with the forwarding ones, and `quickstart.md` §8 now says so

- [x] T015 [P] Run `uv run --extra dev vulture` (the configuration in `pyproject.toml`, `min_confidence = 80`) and confirm it is green, then record in `specs/008-driver-fetch-helpers/baseline.md` that the check does **not** prove the callers — the evidence is T013's search and the demo's reads — and that the threshold was not lowered (SC-009) — **done**: `vulture` exits 0 with no output at `min_confidence = 80`; `baseline.md` records that the check cannot prove a caller, that the caller under `packages/` is the evidence, and that neither the threshold nor a `# noqa` was touched

**Checkpoint**: every claim in the pull request has a command and an output behind it, and the new checks have been shown to fail on the defects they guard.

---

## Phase 8: Tail (constitution principle VI — in this order, and no other task absorbs it)

- [x] T016 **The check run, taken to zero**: run `bash scripts/run_checks_with_log.sh` from the repository root and fix every remark it reports. The Vite chunk-size advisory and LangGraph's pending-deprecation warning are the only two allowed to stand, per the constitution's check-run section (Principle VI.1; the constitution's Final step) — **done**: `bash scripts/run_checks_with_log.sh` exits 0 with every step OK (ruff, mypy, pylint, boundaries, metadata, eight builds, packaging, vulture, samples API, all eight suites, radon); the log is `archive/logs/check-all.txt`, and the two allowed remarks are its only non-blocking lines

- [x] T017 [US5] **The documentation**: in `docs/extensions/postgresql.md` (section **Installation and construction**) name all four helpers, state the one check and the one error for all four, and add the worked page-and-count example that names the `NULL`/no-row ambiguity and points to `_fetchrow` for a caller that must tell them apart. Add a case section of its own — `## 15. Reading a page and a count through the protected helpers` — with the `[Python](…)` and `[Notebook](…)` links the page's other cases carry, showing every answer this pair introduces rather than one happy path: the page with rows, the page with no match (`[]`), the count (`2`), and a count of no match (`None` from the helper, `0` at the call site). Then make the same change in `docs/how-to/authoring-resource.md` (section **If the implementation uses PostgreSQL**), update both `*.ru_draft.md` counterparts with the same content (the drafts stay uncommitted), and add the case as a script and a notebook: `examples/extensions/postgresql/15_fetch_and_fetchval.py` and `15_fetch_and_fetchval.ipynb`, using the neighbouring `RecordingConnection`/`RecordingPool` harness extended with `fetch`/`fetchval`, and a domain resource whose `list_notes` and `count_notes` call the two helpers and print those four answers (FR-021, FR-022, FR-025; FH-5.1, FH-5.2; Principle VI.2, VI.4 … VI.7) — **done**: the helper list names four on both pages; the PostgreSQL page gains "A page through `_fetch` and a count through `_fetchval`" with the Python and notebook links, the body of `main()` and the observed output, including `[]`, `2`, the `0` for an absent value and `Connection is not open`; the authoring page carries the same four helpers and the two methods; both `*.ru_draft.md` counterparts carry the same content and stay uncommitted

- [x] T018 Run the example the documentation now teaches: `uv run python examples/extensions/postgresql/15_fetch_and_fetchval.py`, then `uv run --extra dev pytest tests/examples -q`, and confirm both are green. The repository check run does not execute examples, so this is its own gate; the example is executed with the repository's environment and what the page shows is what it printed (FR-025, SC-013; Principle VI.6; quickstart §9) — **done**: `uv run python …/15_fetch_and_fetchval.py` prints exactly the six lines the page shows, and `pytest tests/examples -k 15_fetch` passes. The full examples gate is **151 passed, 4 xfailed, 2 failed** — both failures in files this branch does not touch (`git diff` empty): `step_21_relations/13_specialization_erd.py` (StopIteration) and `step_25_context/01_context.py` (AccessDenied by CHECK_ROLES), the two pre-existing failures #007 already recorded. The repository check run does not execute examples, so it stays green

- [x] T019 **The changelog**: add one article under `## [Unreleased]` / `### Added` in `packages/aoa-action-machine/CHANGELOG.md`, in plain words — a domain resource can now read a list of rows and a single value through the driver it holds, without a query member entering the SQL contract — with no dated heading, no version bump and no `### Breaking changes` section; `packages/aoa-demo/CHANGELOG.md` stays untouched, because the demo's public surface did not change (FR-023; Principle VI.3, VI.8, VI.9) — **done**: one `### Added` article under `## [Unreleased]` in `packages/aoa-action-machine/CHANGELOG.md`, in prose, with no dated heading, no version bump and no `### Breaking changes`; the demo's changelog is untouched

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies; must be taken first so the later searches have a "before"
- **Foundational (Phase 2)**: depends on Phase 1; **blocks** Phases 3–6 — no answer can be asserted before the fake can answer
- **US1 (Phase 3)**: depends on Phase 2; blocks US3's annotation and member-set cases
- **US2 (Phase 4)**: depends on Phase 2, and its tests touch the same module as US1's, so it follows US1 rather than running beside it
- **US3 (Phase 5)**: depends on US1 and US2 — the shared-policy cases need all four members to exist
- **US4 (Phase 6)**: depends on US2 (the count needs `_fetchval`) and on US3's tested policy; T011 can go in parallel with T010's review, T012 closes the phase
- **Verification (Phase 7)**: depends on Phases 3–6
- **Tail (Phase 8)**: depends on Phase 7, strictly in the order T016 → T017 → T018 → T019

### Within Each User Story

- Tests first, confirmed red, then the member they cover
- Documentation of a member goes with the member; the module-level listing (T008) goes after both members exist
- The phase is complete only when its checkpoint's command is green

### Parallel Opportunities

- **T011** (demo README) is the only task in Phase 6 that can run beside another file's work
- **T013** and **T015** are different commands against a settled tree and may be run together
- Everything else shares `postgres_resource.py` or `test_postgres_helpers.py` with an earlier task and is sequential by file

---

## Parallel Example: Verification

```bash
# Two independent readings of the same settled tree:
Task T013: the contract searches and the unedited contract suites
Task T015: `uv run --extra dev vulture` and the note on what it cannot prove
```

---

## Implementation Strategy

### MVP

Phases 1–5: the two helpers with one policy, exactly four members, and the module documentation naming them. That is
the smallest slice that satisfies the issue — a page helper alone would leave the consumer's `count(*)` still reaching
for the connection.

### Incremental delivery

1. Phase 1 + 2 → the instrument and the baseline
2. Phase 3 → the page path works and is tested
3. Phase 4 → the value path works and is tested
4. Phase 5 → one policy across four members, documented
5. Phase 6 → the demonstration, with the freeze on which helper has a caller
6. Phase 7 → adversarial verification, contract searches, `vulture`
7. Phase 8 → the check run, the documentation, the changelog — in that order

### Coverage

| Requirement | Tasks |
| --- | --- |
| FR-001, FR-002 | T003, T004 |
| FR-003, FR-004 | T005, T006 |
| FR-005, FR-006 | T004, T006, T007 |
| FR-007 | T003, T005, T007 |
| FR-008 | T004, T007 |
| FR-009 | T007, T013 |
| FR-010 | T004, T006, T007 |
| FR-011, FR-012 | T008 |
| FR-013, FR-014 | T007, T013 |
| FR-015 … FR-018 | T009, T010 |
| FR-019 | T002, T009, T012 |
| FR-020 | T010, T011 |
| FR-021, FR-022 | T017, T018 |
| FR-023 | T019 |
| FR-025 | T017, T018 |
| FR-024 | every test task; T016 is the only gate that touches a real environment and it opens no database |
| SC-001, SC-002 | T003, T005, T014 |
| SC-003 … SC-005 | T007, T014 |
| SC-006, SC-009 … SC-012 | T001, T013, T015 |
| SC-007, SC-008 | T009, T012, T014 |
| SC-013 | T018 |

---

## Notes

- [P] tasks = different files, no dependency on an incomplete task
- Tests are written first and confirmed red; a test that passes before its member exists is not testing the member
- No task adds a public query member to `ProtocolSqlResource`, `SqlResource` or `WrapperSqlResource`
- No task changes `_execute`, `_fetchrow`, `_require_connection`, `open`, `begin`, `commit`, `rollback` or `close`
- Any commit, push, pull request or merge waits for the maintainer's explicit instruction
