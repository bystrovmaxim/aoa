# Implementation Plan: The query surface leaves the SQL contract, and the driver keeps protected helpers

**Branch**: `feature/issue-216-sql-contract-driver-helpers` | **Date**: 2026-10-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/007-sql-contract-driver-helpers/spec.md`

## Summary

`execute(query, params=None)` sits in the SQL contract (`protocol_sql_resource.py:76`, `sql_resource.py:148`,
`wrapper_sql_resource.py:133`, `postgres_resource.py:223`) and therefore obliges every SQL resource to publish a
query passthrough that nothing in the framework calls. The feature removes it from the structural contract, from the
base resource and from the nested-action proxy, and moves the query surface onto the driver as **two protected
helpers**: `_execute` for a statement and `_fetchrow` for a row, both behind one `_require_connection` that today is
written four times in `PostgresResource` (`begin`, `commit`, `rollback` and the removed member). The proxy keeps
refusing the lifecycle and now has nothing to delegate, so a nested action cannot reach the connection at all by
construction; a domain that wants to hand a nested action something overrides `get_wrapper_class()` with its own
wrapper that delegates its own semantic methods — the shape `OcelStoreWrapper` already has, reached in exactly one
place in the runtime (`tools_box.py:191`). Removing the member leaves `isinstance(proxy, ProtocolSqlResource)` true,
because the protocol is `@runtime_checkable` and keeps every other member the proxy answers. The demo loses the
member in eight stubs and in its in-memory identity store, and the identity domain moves from a multi-row read to a
single-row one so that both helpers have a caller inside `packages/` and the in-memory store stops deciding what to
do by testing the text of a statement for `INSERT`. The tutorial case whose whole subject was the proxy running a
query is deleted with its notebook and its section, and the surviving half — a resource's own wrapper delegating its
own method — is demonstrated in the nested-action case, where the runtime supplies the proxy. The pages, the home
page and the examples that taught the passthrough are rewritten; the changelog carries one breaking-change entry
under `## [Unreleased]`. No new dependency, no new package, no compatibility shim, and no test that needs a database.

## Technical Context

**Language/Version**: Python 3.12 (`requires-python = ">=3.12"` repo-wide; PEP 695 generics and `from __future__ import annotations` already used)

**Primary Dependencies**: `asyncpg>=0.29,<1.0` — already the `postgres` extra of `aoa-action-machine` (installed here: 0.31.0), and the only dependency the changed code touches; nothing new is added to any package's dependencies. For the tests, `pytest` with `pytest-asyncio` (`asyncio_mode = "auto"`) and the plain-Python fakes the previous feature added

**Storage**: PostgreSQL is the subject, not a requirement. The feature is verifiable with **no database running**: the helper tests drive `PostgresResource` over the fake pool and fake connection in `packages/aoa-action-machine/tests/support/fake_pool.py`, and every example keeps its inline recording connection

**Testing**: pytest per package (`testpaths = ["tests"]`, `pythonpath = ["src"]`, `asyncio_mode = "auto"`), driven by `bash scripts/run_checks_with_log.sh`. **The repository-wide examples runner is not part of that script** — measured: `scripts/run_checks_with_log.sh:168` runs `tests/packaging` and then the eight package suites, and nothing under `tests/examples` — so `tests/examples/test_examples_run.py`, which executes every `examples/**/*.py` and requires a zero exit code, must run as its own gate, and this feature edits examples. `pylint` ignores `packages/*/tests/` (`pyproject.toml`, `ignore-paths`), so the migrated tests may call the protected helpers; the production rule they would otherwise trip is disabled repo-wide anyway (`W0212`)

**Target Platform**: the eight-package `uv` workspace on CPython 3.12; the gates are the repository check run plus the examples runner

**Project Type**: a library change confined to `aoa-action-machine` (the contract, the driver, the proxy), plus the demo's own resources, the documentation, the examples and the changelogs

**Performance Goals**: none introduced, and none claimed. The one measurable question was settled by reading the installed driver: `fetchrow` is `fetch` with the protocol's row cap set to one (`asyncpg/connection.py:666-760`: `_execute(query, args, 1, …)` against `fetch`'s `0`), so it appends no `LIMIT`, shares the same prepared statement and cannot be slower; the demo's read moves from a list to a single row, which is strictly less work

**Constraints**: a clean break with no alias and no deprecation window (spec FR-001 … FR-004); exactly two helpers, each with a caller (FR-008); no new public query member anywhere under `packages/`; no new dependency; the transaction surface, rollup and closing keep the behaviour [#215](https://github.com/bystrovmaxim/aoa/issues/215) gave them; the unrelated `execute` methods of custom domain resources are not touched (FR-024); every example runs with no database (FR-023); Maxitor is untouched

**Scale/Scope**: 4 edited source modules in `aoa-action-machine` (the protocol, the base, the proxy, the driver) and 4 in the demo (the driver-free base, the in-memory store, the PostgreSQL store, the action) plus the demo's READMEs; 1 edited test-support module and 1 new test module; 3 edited test modules in the machine plus that package's test-module map docstring, and 2 in the demo; 5 documentation pages edited (four of them with a Russian draft) and 1 checked and left alone, plus the two demo READMEs; 7 example scripts and their 7 notebooks migrated with the change that breaks them, and 1 script with its notebook deleted; 2 changelogs; the check run and the examples runner

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
| --- | --- | --- |
| I. The maintainer decides | No commit, push, pull request or merge is part of executing this plan without an explicit instruction in the current turn | PASS — the plan produces files only; the branch exists on the maintainer's instruction, and the spec was written and clarified on the maintainer's instruction |
| II. English in commits, in git and in code | Every edited docstring, comment, test, page and changelog entry in English; the Russian drafts the maintainer reads are `*.ru_draft.md`, gitignored, and reported beside their English page | PASS — planned; four touched pages have a draft today and are updated with it |
| III. Module headers | Every module this feature edits keeps its line-1 path, one-line title and 79-column `═` sections; the four modules whose `PURPOSE` text describes the removed member (`protocol_sql_resource.py`, `sql_resource.py`, `wrapper_sql_resource.py`, `postgres_resource.py`) have that text corrected, including the diagram in `sql_resource.py` | PASS — planned |
| IV. AI-CORE blocks | `ProtocolSqlResource`'s `CONTRACT` key names the member set (`protocol_sql_resource.py:43`) and stops naming the removed member; no block is added to a method, and none moves into a module docstring | PASS — planned |
| V. Short docstrings | The two helpers, the driver-free primitives and every function the migration touches get one line ending with a period, identifiers in double backticks | PASS — planned |
| VI. Check run, documentation, changelog | Exactly three closing tasks in that order, and no other task absorbs them | PASS — the closing three tasks: the check run taken to zero, then the documentation, then the changelog. The adversarial break and restore stands immediately before the tail, while the code is still the implementation's |
| Final step: the check run | `bash scripts/run_checks_with_log.sh` is run and taken to zero; the Vite chunk-size advisory and LangGraph's pending-deprecation warning are the only remarks allowed to stand | PASS — closing task, taken to zero |

**Three readings of the repository's own practice, recorded rather than silently resolved**:

1. **Which changelog, and under which heading.** The question was put to the maintainer in the clarification
   session and answered: one article in `packages/aoa-action-machine/CHANGELOG.md` under `## [Unreleased]`, with a
   `### Breaking changes` section, and **no dated heading and no version bump** — the issue's wording ("a version
   bump and a dated entry") is superseded by the correction the maintainer made while
   [#215](https://github.com/bystrovmaxim/aoa/issues/215) was being written. `packages/aoa-demo/CHANGELOG.md` gets
   its own short `### Breaking changes` entries, because the demo is a published package and its public surface does
   change (`IdentityStoreStub.execute` disappears, the domain's read answers one row instead of a list).
   `docs/CHANGELOG.md` is not touched: it holds framework-level dated articles, and this feature writes none.
2. **Which order the tail runs in.** Principle VI fixes the tail as check run → documentation → changelog, while
   the section *Final step: the check run* calls the run "the last step of any change". The tasks follow Principle
   VI, for the reason recorded in the previous plan and still true: the run's first Python step is `ruff check --fix`,
   so it must see the settled code; the documentation writes Markdown, which the run does not read; the changelog
   summarizes what the documented, checked code does. The one artefact that must execute — the example scripts — is
   run while it is written (Principle VI, point 6), which is why the examples belong to the implementation tasks and
   not to the tail. If the maintainer reads the two sections the other way, the tail becomes documentation →
   changelog → check run and nothing else changes.
3. **Which pages owe a Russian draft.** Of the pages this feature touches, four have a draft today —
   `docs/extensions/postgresql.ru_draft.md`, `docs/how-to/authoring-resource.ru_draft.md`,
   `docs/how-to/choosing-action-aspect-resource.ru_draft.md`, `docs/tutorials/step-19-resource.ru_draft.md` — and
   each is updated in the same task as its English page, because the two are reported as a pair. The root
   `README.md` has no draft and none is invented for an edited section; if the maintainer wants one, it is one task,
   not a plan change.

**Re-check after Phase 1 design**: no new dependency, no new package, no new public member anywhere under
`packages/` (the two helpers are protected, and the one net change to a public surface is a removal), no file under
`packages/aoa-maxitor/`, and no test that needs a live database. Every gate above still passes, and
**Complexity Tracking** stays empty.

## Project Structure

### Documentation (this feature)

```text
specs/007-sql-contract-driver-helpers/
├── plan.md              # This file (/speckit-plan output)
├── spec.md              # The capability, clarified (5 questions, 5 answers)
├── research.md          # Phase 0 output: the decisions behind the design
├── data-model.md        # Phase 1 output: the shapes, their states and the validation rules
├── quickstart.md        # Phase 1 output: how to prove it works
├── checklists/
│   └── requirements.md  # Spec quality checklist (16/16 passing)
├── contracts/           # Phase 1 output: the three surfaces this change fixes
│   ├── sql-resource.md      # what the contract, the base and the driver are afterwards
│   ├── driver-helpers.md    # the extension point: two helpers, one check, one error policy
│   └── nested-access.md     # the proxy that delegates nothing, and the domain wrapper that does
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
packages/aoa-action-machine/
├── src/aoa/action_machine/resources/sql/
│   ├── protocol_sql_resource.py     # EDIT: drop the `execute` member (:76); correct the PURPOSE
│   │                                #       sentence (:12) and the AI-CORE CONTRACT (:43)
│   ├── sql_resource.py              # EDIT: drop the abstract member (:148); correct the contract
│   │                                #       line (:11) and the rollup example (:52-53)
│   └── wrapper_sql_resource.py      # EDIT: drop the delegating member (:133-137); correct the
│                                    #       module docstring (:13) and the diagram (:38)
├── src/aoa/action_machine/resources/postgres/
│   └── postgres_resource.py         # EDIT: `execute` (:223) becomes `_execute`; add `_fetchrow` and
│                                    #       the single `_require_connection`; the four repeated
│                                    #       checks (:146, :167, :182, :238) become one
├── tests/support/fake_pool.py       # EDIT: `FakeConnection.fetchrow` records the statement and its
│                                    #       parameters and returns one row or None
└── tests/action_machine/resources/
    ├── test_postgres_helpers.py     # NEW [US2]: a helper on a closed resource; a driver failure
    │                                #           arriving chained; parameters forwarded; one row
    ├── test_sql_resource.py         # EDIT: the two doubles lose the member; the "missing execute"
    │                                #       case is deleted; the lifecycle cases run without it;
    │                                #       a guard asserts the contract exposes no query member
    ├── test_wrapper_sql_resource.py # EDIT: the delegation cases become absence cases; the lifecycle
    │                                #       refusals, `isinstance` and the double and triple wrap
    │                                #       stay; the domain wrapper gains a case
    ├── test_resource_unit_of_work.py# EDIT: five `resource.execute(...)` calls become `resource._execute(...)`
    └── __init__.py                  # EDIT: the contract note (:19) and the module map (:38)

packages/aoa-demo/
├── src/aoa/demo/model/identity/
│   ├── resources/identity_store_base.py  # EDIT: the read primitive answers one row; a write primitive
│   │                                     #       joins it; `record_login` calls the primitive
│   ├── resources/identity_store_stub.py  # EDIT: drop `execute`; implement both primitives in memory
│   ├── resources/identity_store.py       # EDIT: implement both primitives through `_fetchrow`/`_execute`
│   ├── actions/identity_lookup.py        # EDIT: one row instead of a list; `found` from `is None`
│   └── README.md                         # EDIT: the shape of the read and the helpers it uses
├── tests/test_identity_postgres.py       # EDIT: the read assertions and the close-path call site
├── tests/test_sql_resource_stubs.py      # EDIT: the eight stubs are asserted without the removed member
├── README.md                             # EDIT: the two operations and the driver-free mode
└── CHANGELOG.md                          # EDIT: its own breaking-change entries (closing task)

docs/
├── extensions/postgresql.md (+ .ru_draft.md)          # EDIT: the helpers replace the query-surface paragraph
├── how-to/authoring-resource.md (+ .ru_draft.md)      # EDIT: the helpers are how a domain runs a statement;
│                                                      #       the proxy does not delegate
├── how-to/choosing-action-aspect-resource.md (+ .ru_draft.md)  # EDIT: the proxy runs no command
├── tutorials/step-19-resource.md (+ .ru_draft.md)     # EDIT: the "wrapper can execute" section is deleted;
│                                                      #       the nested case gains the domain wrapper
└── how-to/migrating-legacy.md                         # CHECK ONLY: it shows pre-AOA code

README.md                                              # EDIT [US5]: the resource example stops teaching the passthrough
examples/                                              # the seven scripts below call the removed member, so the
                                                       # change that removes it breaks them: each is migrated in
                                                       # US2, with its notebook, and the runner is the check
├── step_17_connections/16_pool_lifespan.py (+ .ipynb) # MIGRATE [US2]: a semantic method replaces the passthrough
├── step_19_resource/04_wrapper_execute.py (+ .ipynb)  # DELETE [US2]: its subject no longer exists
├── step_19_resource/07_nested_action.py (+ .ipynb)    # MIGRATE [US2], then ENRICH [US3]: the domain wrapper
│                                                      #       delegates its own method
└── extensions/postgresql/02_concurrent.py, 04_commit.py, 05_rollback.py, 07_rollup.py,
    14_failed_commit.py (+ their .ipynb)               # MIGRATE [US2]: each case reaches the connection through
                                                       #       the driver's helpers, not through the removed member
```

**Structure Decision**: the two helpers live on `PostgresResource` and nowhere else, because the driver is the only
class in the repository that holds a connection and knows what the driver's errors look like; putting them on
`SqlResource` would put an asyncpg-shaped member back into the contract, and putting them on the proxy would
recreate the reach-through by another name. The proxy therefore heads in the opposite direction — it loses its last
delegating member — and the only way to give a nested action access becomes a domain's own wrapper, chosen through
`get_wrapper_class()` and constructed in exactly one place in the runtime (`tools_box.py:191`), which is also why
`isinstance(proxy, ProtocolSqlResource)` must keep holding: the framework's own propagation depends on that shape.

The demo's split is the same split the previous feature drew, sharpened: the driver-free base states the domain's
two operations and the transaction they share, each store supplies the storage primitives, and the PostgreSQL store
is where the driver's row type becomes a plain mapping. The reshape of the read — one row instead of a list — is the
price of keeping the helper set at the two members the issue names while giving both a caller, and it buys the
removal of the in-memory store's statement-text sniffing.

The tests are split by subject: the helpers in a new module beside the driver's other tests, so that the
closed-resource and chained-failure cases read as one subject; the contract and the proxy in the two modules that
already own them; the demo's own domain in the demo's own suite.

**Six points the design phase settled, because the plan cannot leave them open**:

1. **One check, one message per failure.** `_require_connection()` returns the held connection or raises
   `HandleError("Connection is not open")`; `begin`, `commit`, `rollback`, `_execute` and `_fetchrow` all call it.
   The three lifecycle failures keep their current wording (`BEGIN failed: …`, `COMMIT failed: …`,
   `ROLLBACK failed: …`), and the helper's failure keeps the driver's current wording (`SQL execution failed: …`,
   `postgres_resource.py:241`). The proxy's old delegation wording (`SQL execution error: …`) disappears with the
   member, and the tests that asserted it are deleted rather than migrated — there is nothing left to wrap.
2. **The helpers are exactly two and carry no policy beyond the check and the wrap.** `_execute(query, params=None) -> str`
   and `_fetchrow(query, params=None) -> asyncpg.Record | None`, with `params: tuple[Any, ...] | None`, where `None`
   and an empty tuple mean the same thing (`*params if params else ()`, as today). No `_fetch`, no `_fetchval`, no
   `executemany`: after the demo's read becomes single-row, nothing in the repository needs them, and the issue's
   rule is that such a member appears only with a caller. Neither helper opens a transaction, converts a row into a
   mapping, or writes a message of its own — those belong to the domain method, which wraps deliberately in one
   `except` with the helper's error chained as its cause.
3. **The proxy keeps every member it has except the delegating one.** It still refuses `open`, `begin`, `commit`,
   `rollback` and `close`, still refuses context-manager use, still answers `rollup` and `check_rollup_support`,
   and still returns itself from `get_wrapper_class()`, so a second and a third wrap behave as the first. The
   protocol is `@runtime_checkable` (`protocol_sql_resource.py:38`), so `isinstance` keeps holding once the member
   is gone from both sides: the member leaves the protocol and the proxy in the same change.
4. **A domain gives a nested action access by overriding `get_wrapper_class()`.** The framework builds the proxy in
   exactly one place (`tools_box.py:191`) and hands it whatever class the resource returns, so a domain resource
   that wants nested access returns its own wrapper class, whose delegated members are its own semantic methods —
   the shape `OcelStoreWrapper` already has (`packages/aoa-ocel/src/aoa/ocel/resource/ocel_store_wrapper.py`: it
   delegates `add_event` and refuses `open`/`close`). `SqlResource.get_wrapper_class()` keeps returning
   `WrapperSqlResource` as the safe default. The pattern is demonstrated in the nested-action example and taught on
   the resource-authoring page; the tutorial case that demonstrated the old delegation is deleted outright, with its
   notebook and its section, because its subject no longer exists.
5. **The demo's base owns the transaction, each store owns the primitives.** `IdentityStoreBase` declares
   `_read_person(person_id) -> dict[str, Any] | None` and `_write_login(person_id, at) -> None`; `read_person` and
   `record_login` are written once on top of them, `record_login` keeping the `begin`/`commit`/`rollback` it owns
   today. `IdentityStore` implements both through `_fetchrow` and `_execute` and converts the driver's record into a
   plain mapping at that boundary; `IdentityStoreStub` implements both in memory, and its removed member takes the
   statement-text sniffing (`identity_store_stub.py:67-71`) with it. `read_person` returns one person or nothing, so
   `identity_lookup.py:94` tests `is None` rather than the truthiness of a collection, and the route's two outcomes
   are unchanged.
6. **What the plan deliberately does not resolve**: the changelog's prose (written at the tail, from the finished
   code), the exact names of any test module this plan does not name, whether the maintainer wants a
   `docs/CHANGELOG.md` article for a change of this size (the answer recorded above is no), and the question of a
   Russian draft for the root `README.md`.

## Test design

| Module | New/Edited | What it proves |
| --- | --- | --- |
| `tests/support/fake_pool.py` | EDIT | `FakeConnection` answers `fetchrow` as the driver does — the statement and its parameters recorded, one row or `None` returned, the one-operation-at-a-time rule unchanged |
| `tests/action_machine/resources/test_postgres_helpers.py` | NEW | A helper on a resource that never opened and on one already closed raises `HandleError("Connection is not open")` and never an attribute error; a connection that fails turns into `HandleError` with the driver's error as `__cause__`; parameters reach the connection; `_fetchrow` returns the row and `None` |
| `test_sql_resource.py` | EDIT | A subclass implementing only `open`/`begin`/`rollback` instantiates and `commit` comes from the base; the incomplete-subclass cases still refuse; the contract exposes no query member; the lifecycle cases run without a statement |
| `test_wrapper_sql_resource.py` | EDIT | The proxy has no `execute`, no `_execute` and no `_fetchrow`; it still refuses the lifecycle and context-manager use; `isinstance` holds; two and three wraps behave as one; a domain wrapper delegates its own semantic method and still refuses the lifecycle; an error from a delegated method arrives as the domain's own error |
| `test_resource_unit_of_work.py` | EDIT | The five calls the previous feature wrote now drive the helper, and the unit-of-work behaviour it asserts is unchanged |
| `packages/aoa-demo/tests/test_identity_postgres.py` | EDIT | The domain's read answers one person or nothing through the driver's helper; a closed resource yields the framework's named failure rather than the base's own error |
| `packages/aoa-demo/tests/test_sql_resource_stubs.py` | EDIT | The eight stubs still satisfy the contract and still close harmlessly, now without the removed member |

Two checks cannot be tests and are carried by the closing task instead, as the specification's own success criteria
ask: the source searches (no public query member on a SQL resource, no caller of the removed one under `packages/`,
no page presenting it as the query surface) and the count of places where a store without a database inspects
statement text. They are `grep` runs against the branch base, recorded in the pull request.

## Documentation design

| Page | What changes |
| --- | --- |
| `docs/extensions/postgresql.md` (+ `.ru_draft.md`) | The query-surface paragraph (:35) is replaced: the contract is the lifecycle, the driver offers its subclasses a statement helper and a row helper, a domain resource supplies its own reading methods, and a generic passthrough is something a resource may publish itself. The paragraph that describes the proxy (:650) stops saying it delegates the member and says it delegates only rollup inspection. The four example blocks that call the removed member (:207, :400, :432, :467) and the custom-resource block that overrides it (:609-614) are rewritten onto semantic methods over the helpers, and the row helper's semantics are stated: it answers the *first* row, which is the only row when the query is keyed. |
| `docs/how-to/authoring-resource.md` (+ `.ru_draft.md`) | The helpers are named as the way a domain resource runs a statement and reads a row, with the deliberate wrapping pattern; the sentence that the proxy delegates the removed member (:118) is corrected to say the proxy delegates nothing and that a domain wrapper is how nested access is given. The unrelated in-memory-ledger `execute(entry)` is left alone. |
| `docs/how-to/choosing-action-aspect-resource.md` (+ `.ru_draft.md`) | The proxy paragraph (:50) stops claiming the proxy executes permitted commands; it says the proxy runs nothing and the caller's semantic methods remain the caller's. |
| `docs/tutorials/step-19-resource.md` (+ `.ru_draft.md`) | The section `## A wrapper can execute a statement` (:225) and the code it shows are deleted; the section `## A wrapper for nested operations` (:209) absorbs the one sentence that matters — the proxy offers nothing to run a query with; and `## A real nested action receives a restricted view` (:324) gains the domain wrapper: the resource declares its own wrapper class and its own semantic method, the nested action calls it successfully, and `close` is still refused. The notebook links for the deleted case go with it. |
| Root `README.md` | The resource example (:604-618) stops teaching a resource that calls the removed member on the driver as the ordinary way to write SQL; it shows the semantic method over the helper instead. |
| `docs/how-to/migrating-legacy.md` | Checked, not assumed: it shows pre-AOA code (:42). If its snippet presents the removed member as the framework's query surface it is corrected; if it shows a pre-AOA client, it is left as history. |
| **Not touched, deliberately** | The `execute` methods of custom domain resources: the ledger in `docs/how-to/authoring-resource.md`, `examples/how_to/06_custom_resource.py`, `examples/step_06_dependencies/01_depends.py`, `docs/tutorials/step-06-dependencies.md`, and the OCEL store and its wrapper. Those are a resource's own members; the OCEL wrapper is cited as the pattern to copy, not migrated (FR-024). |

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No constitution violations — the table is intentionally empty. The three readings recorded in the Constitution
Check are questions of practice inside the constitution's own text: the changelog question was settled by the
maintainer in the clarification session, the tail order follows Principle VI, and the Russian drafts follow the rule
that a touched page with a draft is updated with it. None of them adds a task the plan does not already carry.
