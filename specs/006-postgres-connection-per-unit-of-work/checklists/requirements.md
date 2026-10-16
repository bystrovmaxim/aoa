# Specification Quality Checklist: One connection per unit of work, and one pool for the process

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-16
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- **Type of feature, stated plainly**: this is an internal framework-and-library change whose "users" are the developers who build against the framework. There is no end-user business flow to describe, so the specification uses the library's public vocabulary — resource, connection, pool, unit of work, boundary, factory, finalizer — deliberately and states so in the Clarifications section. The two checklist items about "implementation details" and "non-technical stakeholders" are read in that light: no language, framework, database driver or file path appears as a requirement, but the concepts the feature is made of do, because they *are* the contract the feature changes.
- **Concrete engine names** appear only where the scope must name the concrete driver whose defect is being fixed (the resource, the pool, the driver's defaults) and where a related issue is excluded. No success criterion is phrased in terms of a driver's internals: every SC is counted in calls, rows, connections, failures or exit codes.
- **Clarifications section** carries twenty-two decisions in two dated sessions: twelve taken from the issue, five taken while writing this specification, and five taken in the clarification round (`### Session 2026-10-16 — clarification`, each as a question and an answer). The decisions written during drafting resolve the points the issue left open — the version choice (release what the metadata already claims), the demo's database-free mode, the number and location of the boundary hook points, the four requirements that follow implicitly from the issue's invariants (an unfilled holder, an exhausted pool, a failed opening, a resource reaching a pool it was not given), when the "exactly one of the two" construction error is raised, and why the two-pools edge does not contradict the out-of-scope bullet.
- **Clarification round (five questions, all answered)** settled the four areas the scan found Partial and one that planning could not choose on its own. The adapter gains **one general lifecycle option** — `build(lifespan=...)`, an asynchronous context manager run at startup and closed at shutdown, with nothing database-specific in it (FR-038, SC-021); the framework **does not create, configure or close the pool** — the application does, and the option only gives it a place to run that code. Tests reach **a fake pool and a fake connection through `pool=`**, the resource's public constructor stays exactly the shape the issue states and gains no substitution parameter (FR-042, SC-022). A factory returning **one shared resource** is neither forbidden nor detected: the finalizer still runs exactly once per call, and the rule is documented rather than policed (FR-014, Edge Cases). The demo **extends its existing `identity` domain** rather than adding a new one (FR-036), and the examples and demo carry **`min_size=1, max_size=10, timeout=30`** as the stated pool values (FR-009, Edge Cases).
- **Review pass after the first draft** compared the specification line by line with the issue and closed ten gaps: the constructor's default and its keyword rule; the finalizer's sync-or-async callable shape and where a declaration is validated; the boundary holding both the resources and their finalizers while the run still receives only the resources; the four per-call test declarations named as a migration requirement (FR-041) with its own success criterion (SC-018); the demo's startup-hook gap and how it is closed (FR-038); the demo's own README and the demo README (FR-036); the new section's title, placement and closing exercise (FR-030); the package description's false pool drawing (FR-032); the changelog's dated house form (FR-040); and the adversarial procedure as an explicit requirement (FR-043, SC-019).
- **Related issues** are named as scope boundaries: [#213](https://github.com/bystrovmaxim/aoa/issues/213) (closed — Maxitor is not migrated here), [#214](https://github.com/bystrovmaxim/aoa/issues/214) (several graphs per process, unrelated) and [#216](https://github.com/bystrovmaxim/aoa/issues/216) (the public query surface leaves the contract there, not here).
- **Coverage of the issue's own test list**: the issue names 30 concurrent requests, exhaustion at a ceiling of 2, an exception inside a unit of work, task cancellation, the finalizer running exactly once on each of the three paths, a failing finalizer not masking the original error and surfacing on success, two concurrent transactions not interleaving, the held-connection count never exceeding the ceiling, repeated open/close, `rollup=True`, and the wrapper's refusals. All of them are mapped to FR-014 … FR-027 and SC-001 … SC-012, so planning inherits the whole list rather than a summary of it.
- **The adversarial requirement is carried verbatim**: SC-001 is worded so that the check must be red on the old code — the connection harness has to enforce the one-operation-at-a-time rule, or the new test cannot fail before the fix (Assumptions, first bullet).
- **The constitution's tail is reserved, not absorbed**: FR-040 covers the changelog and the version pair; FR-035 and SC-014 cover the running examples; SC-017 covers the closing check run. Planning must still reserve the three closing tasks in the constitution's order — the check run, then the documentation, then the changelog.
- **Sections deliberately absent** from the spec: `Key Entities` is present (pool, resource, unit of work, boundary, per-call declaration, finalizer, proxy, holder); a separate `Dependencies` section is not, because there is no external service to depend on — the feature must work with no database at all, which is itself a requirement (FR-035, FR-037).
- **Not done, and not this command's job**: the specification does not reserve tasks, does not choose the file layout, and does not write the documentation. `/speckit-clarify` has run (five questions, all answered, integrated above) and `/speckit-plan` has run, producing `plan.md`, `research.md`, `data-model.md`, `contracts/per-call-connection.md`, `contracts/sql-resource.md`, `contracts/boundary.md` and `quickstart.md`. `/speckit-tasks` follows, and only it reserves the closing three tasks in the constitution's order.
- **Checklist re-validation after the clarification round**: 12/12 items passing, before and after; no item changed state, so no marker was toggled. The clarification round added requirements and success criteria rather than removing ambiguity from a failing item: FR-009 gained the stated pool values, FR-014 gained the "not policed" rule, FR-036/FR-038 gained the domain and the lifecycle option, FR-042 gained the fake-pool substitution rule, and SC-021/SC-022 were added for the two new contract points.
- **Adversarial review after the plan was written**, and what it corrected. An independent pass checked every artifact against the spec and against the code, and found three blockers, which are fixed: (1) `connection_scope` originally opened *every resolved* resource — including a ready one — which would have opened what the lifespan owns; the scope now walks the declaration per entry and opens only what a `PerCallConnection` created (FR-019). (2) That same flattened resolve would have lost the resources created before a later factory raised; the per-entry walk keeps them and finalizes them (FR-021). (3) The wait bound had no owner: the driver's `create_pool` accepts no such parameter, so the size bounds are stated at creation and the wait bound is stated where the wait happens — the resource's `acquire_timeout` class attribute, `30.0` by default, which keeps the constructor exactly the two forms plus `rollup` (FR-005, FR-009, FR-010, SC-022). Five majors were also closed: the pool annotation is the machine's `PoolProtocol` (no driver import at import time, FR-037); double `open()` is settled as idempotent and keeping the held connection, with the repository's existing `ConnectionAlreadyOpenError` convention recorded as deliberately not followed; the closing failure has a mechanism (`add_note`) and cancellation is shielded; the MCP hook is applied inside `_execute_tool_call`, which already holds the route record, so no signature changes; and the two line-number/function-name claims about the adapters were corrected. FR-041's "four" declarations were in fact five in the tests plus one in the examples, and SC-021's search was written against driver names rather than the word `connection` — both corrected in the spec.
- **`/speckit-analyze` pass, and what it corrected.** Cross-checking spec ↔ plan ↔ tasks found eight issues, all fixed. The two that mattered: (1) six tasks carried `[P]` while all writing the same test module, and two more while writing the same demo module — the `[P]` contract means *different files*, so the lifecycle tests were split into one module per story (`test_resource_unit_of_work.py`, `test_pool_bounds.py`, `test_connection_scope.py`) and the stub check moved to `packages/aoa-demo/tests/test_sql_resource_stubs.py`, with the `[P]` markers corrected; (2) eleven functional requirements and three success criteria had no task that named them, so FR-002/FR-003/FR-019/FR-025/FR-026/FR-028 and SC-003/SC-013/SC-022 were attached to the tasks that carry them, and the guard requirements (no new public query method, the home page untouched, no file under `packages/aoa-maxitor/`) are now asserted by the check-run task. The remaining six: the US4 stub test no longer reads as depending on the new demo resource (it asserts the eight existing stubs only); the module-header, AI-CORE and docstring obligations are stated on each task that creates a module; the plan's file tree gained the pool's structural type and the two new test modules; the plan's scale figures were corrected; the docs tail lists its requirements explicitly instead of as a range; and the quickstart gained the stub-suite command. Coverage after the pass: 43/43 functional requirements and 22/22 success criteria named by at least one task, 41 tasks, no `[P]` file collision.
- **Maintainer decision taken after the plan: closing with an open transaction fails fast.** The maintainer chose strictness over convenience — code that opened a transaction closes it, and a framework that quietly repairs the omission lets the omission drift. Recorded across the artifacts as FR-044, SC-023, a Clarifications answer, a new Edge Case, a resource state (`_in_transaction`), transition rows, the error table, the resource contract (SR-2.5 to SR-2.7), the per-call contract (PC-5.4), the plan's settled points (1a) and the tasks (T011, T012, T013, T021, T030). One interpretation is mine and is stated plainly so it can be corrected: the resource **cleans up before it raises** — it issues `ROLLBACK`, returns the connection, and only then raises `TransactionLeftOpenError`. A raise that left the connection unreturned would leak it and would break FR-017, FR-021 and the precedence rule of FR-020, so fail-fast here means "the caller is told", not "the connection is abandoned". The driver's own rollback on release or disconnect is measured and recorded in research R4 as background, and deliberately not relied on.
- **The fail-fast principle applied to the precedence, on the maintainer's instruction.** The first
  reading of the decision left the violation recorded beside the run's error on a failed run; the
  maintainer rejected that as a way of wrapping the error and hiding what has to be fixed. The rule is
  now: a close that finds a transaction open raises `TransactionLeftOpenError` — a
  `ResourceContractViolationError`, the family meaning the caller's code broke the contract — and that
  error is the one the caller sees **on both paths**, with the run's error chained as its cause and
  never demoted to a note. FR-020 and SC-009 keep their old precedence for **operational** closing
  failures only, and cancellation is the single case where the violation gives way, because replacing
  a `CancelledError` would break cancellation itself. Recorded in spec.md (Clarifications, FR-020,
  FR-044, SC-009, SC-023, Out of scope), both contracts, data-model.md, research.md R4, plan.md 1a and
  the tasks (T013, T021, T030). One limitation is recorded rather than hidden: the FastAPI adapter's
  catch-all answers every uncaught exception with a generic server error and logs nothing, so the
  message is read where the resource or the scope is driven directly; logging it is [#218](https://github.com/bystrovmaxim/aoa/issues/218), filed on the maintainer's instruction while this specification was being written.
- **The cancellation exception was challenged and kept, with the circumstances measured.** Asked who
  can cancel a call at all, the answer was checked in the installed sources rather than asserted:
  uvicorn cancels a request task only on shutdown after its grace period
  (`uvicorn/server.py:289-297`); an MCP client's cancellation notification cancels the in-flight tool
  call (`mcp/shared/session.py:404-406`); application code may bound a call with `asyncio.timeout`
  (no such call site exists in this repository); and any parent task cancels its children. Recorded in
  research.md R4 together with what does **not** cancel: an HTTP client disconnect, this repository's
  own code, and the adapters' catch-all (which catches `Exception`, not the `BaseException`-derived
  `CancelledError`). The maintainer confirmed option A: the cancellation stays a cancellation, and the
  violation is recorded beside it, made visible in a log by [#218](https://github.com/bystrovmaxim/aoa/issues/218).
- **A latent defect in the driver, exposed the moment a test imports it.** `PostgresResource` was
  the only class under `resources/` carrying neither `@meta(...)` nor `@exclude_graph_model` — every
  neighbour has the exclusion (`ExternalServiceResource`, `WrapperSqlResource`, `SqlResource`,
  `BaseStorage`, `BaseGateway`, `BaseController`). Nothing had imported the class in the test suite
  before, so the defect stayed invisible; the first test module that imports it makes
  `ActionProductMachine()` try to emit a `ResourceGraphNode` for it and die on
  `MissingMetaError: ... has no usable @meta 'description'`. The suite went from 2476 passed to 127
  failed and 153 errors. Fixed with the one line its neighbours have — `@exclude_graph_model` — and
  the suite is back to green at **2485 passed** (2476 existing + 9 new). This is a library fix the
  feature needs rather than a scope addition: the tests it adds cannot run without it, and anyone who
  imports the driver and builds a machine today hits the same crash. The changelog article (T041)
  should carry the user-visible half of it: importing `PostgresResource` and building a machine no
  longer fails.
- **The adversarial check, both directions recorded (FR-043, SC-019).** With the suite green at
  **2514 / 60 passed**, `PostgresResource.open()` was temporarily returned to the old shape — one
  connection for the whole process, held in a module-level variable (`_shared_conn`) and handed to
  every resource. The break was placed before the class decorator, because a module-level assignment
  between `@exclude_graph_model` and `class PostgresResource` is a syntax error — the first attempt
  proved it (two collection errors), which is itself a reminder that the break must still compile.
  Under the break: **13 failed, 2501 passed** in `aoa-action-machine` and **2 failed, 58 passed** in
  `aoa-demo`. Every failure is in a module this feature added — `test_resource_unit_of_work.py`,
  `test_pool_bounds.py`, `test_identity_postgres.py` — and **not one pre-existing test failed**, which
  is the "nothing else newly fails" half of the check. The failures carry the defect's own words:
  `tests.support.fake_pool.InterfaceError: another operation is in progress`, and through the resource
  `HandleError: BEGIN failed: another operation is in progress` — the same symptom the issue reports,
  now caught by the tests rather than by production. The file was then restored from a byte-for-byte
  backup (`diff -q` clean, `grep -c "_shared_conn\|ADVERSARIAL BREAK"` → 0), and the suite returned to
  **2514 / 60 passed**. The concurrency test in particular is red under the break and green after the
  restore, which is what SC-019 asks for.
- **Documentation (T040).** Written with the check run already green, and every claim carries a
  real run. The connections chapter now states the pair, and the two contradictory claims are
  gone (`grep -c "no shared state\|a fresh resource is born"` → 0); the new section, "A long-lived
  pool behind a per-call resource", carries the holder, the startup hook, the route, the resource,
  the table of who opens and who closes, its own invariants and questions, and two exercises. The
  three-case output pasted into the chapter is the example's own: `step_17_connections` was extended
  first, run (`uv run python examples/step_17_connections/01_connections.py`, exit 0), and its output
  copied verbatim. The PostgreSQL page gained the pool, closing, ownership and the fail-fast order;
  the how-tos gained `close` among the wrapper's refusals and the per-call pair; the resource page
  gained the closing obligation; the package docstring no longer draws a pool it does not create.
  Both touched examples and both notebooks carry the new case — the notebooks were rebuilt from the
  scripts by slicing the same blocks, then executed cell by cell. The whole example runner was run:
  **115 passed, 4 xfailed, 2 failed** — and both failures were proved to pre-date this work by
  stashing every change and running them at HEAD, where they fail identically (`AccessDenied` by
  `CHECK_ROLES` in `step_25_context/01_context.py`, a `StopIteration` over an ERD field in
  `step_21_relations/13_specialization_erd.py`); neither imports anything this feature touched. The
  sweep for the old shape found one real fragment beyond the chapter: the custom-adapter how-to and
  the cookie-auth example still resolved connections with the flat step, which with the new contract
  would never open or finalize a per-call resource — all five files (page, two scripts, two
  notebooks) now apply `connection_scope`. Russian drafts of both rewritten pages are beside them:
  `docs/tutorials/step-17-connections.ru_draft.md` and `docs/extensions/postgresql.ru_draft.md`,
  both ignored by `.gitignore:86 (*_draft.md)` and absent from `git status`.
- **Changelog (T041).** One article per package, both under `## [Unreleased]`. The first attempt
  dated them (`## [1.0.1a3] – 2026-10-17`, `## [1.0.1] – 2026-10-17`) on the reading that the
  version in `pyproject.toml` meant a release; the maintainer corrected it — **the release has not
  happened**. `948a2e66` ("Release: aoa-action-machine 1.0.1a3, aoa-maxitor 1.2.0, aoa-demo 1.0.1
  (#207)") raised three `pyproject.toml` versions and touched no changelog, so a version in metadata
  names the version **under development**, and the dated heading is the maintainer's release act.
  Both files were returned to `## [Unreleased]` with the article inside; the diff against `HEAD`
  proves nothing else moved — **0 deleted lines** in each file, every pre-existing bullet still
  present exactly once (`Entity specialization`, `Access-control cascade`, `CancelOrderAction`).
  The same correction was carried through the artifacts that had repeated the mistake: FR-040, the
  specification's clarification note, R10 in `research.md`, the two changelog lines in `plan.md` and
  the text of T041. The machine's article is the breaking-change story a reader needs — one
  connection per unit of work, the required pair, `close()` on the contract, the two-source
  constructor with keyword-only `rollup`, closing with a transaction open — followed by `### Added`,
  `### Changed`, `### Documentation`; the demo's is its own: an identity domain that answers with or
  without a database. All ten touched pages were link-checked (0 broken targets, both new anchors
  resolve).
- **The closing check run (T039).** `bash scripts/run_checks_with_log.sh` finished with **exit 0**
  and every step `OK` — the `__getattr__` ban, the Maxitor README check and its Vite build, ruff
  (the auto-fix step changed nothing outside this feature's files), mypy over **831 source files**,
  pylint, the production import boundaries, the pyproject dependency matrix, **eight wheel/sdist
  builds** and the packaging install smoke, vulture, the Maxitor public-API samples, all **eight
  package suites**, and both radon passes. The log (`archive/logs/check-all.txt`, 800+ lines) holds
  zero `FAIL` lines and exactly the two accepted remarks: the Vite chunk-size advisory and
  LangGraph's pending-deprecation warning. The scope guards the task asks for were checked against
  the branch base `61abe951`, not against `HEAD`: over the whole branch the SQL contract gained
  **no** read method (the added definitions are `acquire`, `release`, `close`, the wrapper's
  `__aenter__`/`__aexit__` and its refusal helper — `grep` for added `fetch`/`query`/`execute`
  definitions finds none), `README.md` is untouched (0 lines of diff), nothing under
  `packages/aoa-maxitor/` changed (0 lines), and every suite above ran without a live database.
