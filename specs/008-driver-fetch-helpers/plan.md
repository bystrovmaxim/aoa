# Implementation Plan: A domain reads all rows and one value through the driver's protected helpers

**Branch**: `feature/issue-222-fetch-helpers` | **Date**: 2026-10-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/008-driver-fetch-helpers/spec.md`

## Summary

`PostgresResource` exposes two of the driver's four answers to its subclasses — `_execute` for a status and
`_fetchrow` for the first row (`packages/aoa-action-machine/src/aoa/action_machine/resources/postgres/postgres_resource.py`,
members `_execute` and `_fetchrow` at the end of the class) — and nothing for **all rows** or **one value**. A domain
that answers a page or a `count(*)` therefore either loops the row helper and loses every row after the first, or
reaches past the helper into `self._conn`; the consumer bystrovmaxim/gameoffer#72 hit exactly this. The feature adds
the remaining two helpers, `_fetch` and `_fetchval`, with the shape the existing pair already has: connection taken
from `_require_connection()`, one driver call, one failure message (`SQL execution failed: …`) with the driver's error
chained. After it, the driver offers exactly four protected query members, and the SQL contract, the base resource and
the wrapper are untouched — nothing is added to a public or protected surface a nested action can see, and a 1.0.1a4
consumer needs no edit.

The pair is demonstrated where the issue asks: the demo's PostgreSQL store gains two private storage reads — an
ordered, bounded list of people through `_fetch`, and a count through `_fetchval` — with the demo's suite as their
caller. The driver-free base and the in-memory store do not change, per the maintainer's clarification, so the demo
still runs with no database and no driver extra. The two pages that teach the extension point list all four helpers
and show the page-and-count example; the changelog gains one `### Added` article under `## [Unreleased]`, with no
version bump and no breaking-change section, because nothing is removed.

## Technical Context

**Language/Version**: Python 3.12 (`requires-python = ">=3.12"`); the changed module already carries `from __future__ import annotations`, so a `list[Any]` annotation stays a string at import time and no runtime subscription of a driver type happens

**Primary Dependencies**: `asyncpg>=0.29,<1.0` (installed here: 0.31.0), already the `postgres` extra of `aoa-action-machine`. Nothing new is added to any package's dependencies. The two helpers delegate to `asyncpg.Connection.fetch` and `asyncpg.Connection.fetchval`, whose installed source was read for this plan: `fetch` answers `list` of `Record`, `fetchval` answers the value at `column=0` of the first row or `None` when the query matched nothing

**Storage**: PostgreSQL is the subject, not a requirement. Every check runs with **no database**: the helper tests drive `PostgresResource` over `FakePool`/`FakeConnection` in `packages/aoa-action-machine/tests/support/fake_pool.py`, and the demo's suite uses its own `_FakeConnection`/`_FakePool` in `packages/aoa-demo/tests/test_identity_postgres.py`

**Testing**: pytest per package (`testpaths = ["tests"]`, `pythonpath = ["src"]`, `asyncio_mode = "auto"`), run from the root as `uv run --extra dev pytest packages/…`. Baseline measured on this branch before the change: `test_postgres_helpers.py` 7 passed; the demo suite 69 passed. No check this feature adds needs a live database (spec FR-024)

**Target Platform**: the eight-package `uv` workspace on CPython 3.12; gates are the package suites, `vulture` as configured in `pyproject.toml`, and the repository check run

**Project Type**: a library change confined to `aoa-action-machine` (one class), plus the demo's own resource and suite, two documentation pages with their drafts, and the package changelog

**Performance Goals**: none introduced and none claimed. Both helpers delegate one for one: `_fetch` is one `fetch` call and one list, `_fetchval` is one `fetchval` call and one value. Neither adds a `LIMIT`, a loop, a conversion pass or a second round trip; the only per-row work in a domain is the mapping it chooses (the demo turns records into `dict`s, as its row helper already does)

**Constraints**: additive only — no member added to `ProtocolSqlResource`, `SqlResource` or `WrapperSqlResource` (spec FR-013); the existing pair, the connection check and the lifecycle unchanged (FR-014); exactly four protected query members, no convenience member beside them (FR-009); one error message per failure, and no third message introduced (FR-006); no runtime guard for a mapping of named parameters (clarification answer); no version bump and no dated changelog heading (FR-023); no new dependency; no live database (FR-024)

**Scale/Scope**: 1 edited source module in `aoa-action-machine`, 1 edited test-support module and 1 edited test module; 1 edited source module in the demo, 1 edited demo test module and 1 edited demo README; 2 documentation pages edited with their 2 Russian drafts; 1 new example script with its notebook, executed by `tests/examples`; 1 changelog; the closing check run

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
| --- | --- | --- |
| I. The maintainer decides | No commit, push, pull request or merge is part of executing this plan without an explicit instruction in the current turn | PASS — the plan produces files only; the branch, the spec, the clarification round and this plan exist on the maintainer's instruction |
| II. English in commits, in git and in code | Every docstring, comment, test, page and changelog entry in English; the two Russian drafts are `*.ru_draft.md`, gitignored, and reported beside their English page | PASS — planned; both touched pages have a draft today and are updated with it |
| III. Module headers | `postgres_resource.py` keeps its line-1 path, one-line title and 79-column `═` sections; its `PURPOSE` and `ARCHITECTURE / DATA FLOW` sections gain the two helpers; `identity_store.py` keeps its header and its diagram gains the two reads | PASS — planned |
| IV. AI-CORE blocks | `PostgresResource`'s `CONTRACT` key names the helper set and must name four members, not two; no block goes onto a method and none moves into a module docstring | PASS — planned |
| V. Short docstrings | The two helpers get the existing multi-line style (purpose, args, return, Raises) because they are the extension point, exactly as `_execute` and `_fetchrow`; the demo's two private reads get one line ending with a period, identifiers in double backticks | PASS — planned |
| VI. Check run, documentation, changelog | Exactly three closing tasks in that order, and no other task absorbs them | PASS — the tail: the check run taken to zero, then the documentation, then the changelog. The adversarial break and restore stands immediately before the tail |
| Final step: the check run | `bash scripts/run_checks_with_log.sh` is run and taken to zero; the Vite chunk-size advisory and LangGraph's pending-deprecation warning are the only remarks allowed to stand | PASS — closing task, taken to zero |

**Three readings settled here, each because the repository's own practice has two sides**:

1. **The tail order.** Principle VI fixes the tail as check run → documentation → changelog, while the section *Final step: the check run* calls the run "the last step of any change". The plan follows Principle VI, for the reason the previous plan recorded and which still holds: the run's first Python step is `ruff check --fix`, so it must see settled code; documentation writes Markdown the run does not read; the changelog summarizes what the documented, checked code does. If the maintainer reads the two sections the other way, the tail becomes documentation → changelog → check run and nothing else changes.
2. **Which changelog, and under which heading.** One article in `packages/aoa-action-machine/CHANGELOG.md` under `## [Unreleased]`, no dated heading and no version bump — the maintainer confirmed the [#215](https://github.com/bystrovmaxim/aoa/issues/215) reading in the clarification session, against the issue's literal "version and journal entry". `packages/aoa-demo/CHANGELOG.md` is not touched: the demo's new reads are private, its base and in-memory store do not change, and its public surface is exactly what it was.
3. **What `vulture` can and cannot prove.** `pyproject.toml` runs it at `min_confidence = 80`, and an unused method carries 60 %, so the check would pass even with an uncalled helper. The threshold is not lowered: the evidence that each helper has a caller is the demo's private reads and the search over `packages/`, and SC-009 is worded that way. What the check does catch is an unused import, which this change adds none of.

## Project Structure

### Documentation (this feature)

```text
specs/008-driver-fetch-helpers/
├── plan.md              # This file (/speckit-plan output)
├── spec.md              # The capability, clarified (3 questions, 3 answers)
├── research.md          # Phase 0 output: the decisions behind the design
├── data-model.md        # Phase 1 output: the shapes, their answers and the validation rules
├── quickstart.md        # Phase 1 output: how to prove it works, with no database
├── checklists/
│   └── requirements.md  # Spec quality checklist (16/16 passing)
├── contracts/           # Phase 1 output: the two new members and the surface that does not move
│   ├── fetch-helpers.md     # the pair: signatures, answers, the one check, the one error
│   ├── sql-surface.md       # what stays exactly as in 1.0.1a4, and the search that shows it
│   └── demo-reads.md        # the two private reads that call the pair
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
packages/aoa-action-machine/
├── src/aoa/action_machine/resources/postgres/
│   └── postgres_resource.py        # EDIT: add `_fetch` and `_fetchval` after `_fetchrow`; the module
│                                   #       DATA FLOW diagram and the AI-CORE CONTRACT name four helpers;
│                                   #       the `_execute` docstring sends a row-reading subclass to
│                                   #       both read helpers, not to `_fetchrow` alone
└── tests/
    ├── support/fake_pool.py        # EDIT: `FakeConnection` gains `rows` and `value`, and the two driver
    │                               #       calls `fetch` and `fetchval`, recording statement and params
    └── action_machine/resources/
        └── test_postgres_helpers.py# EDIT: the module docstring's scenario list gains the pair; new cases
                                    #       for the empty list, the list of one, several rows in driver
                                    #       order with and without `ORDER BY`, the scalar, no match,
                                    #       the closed resource, the chained failure, the parameter shapes,
                                    #       and the annotation carrying no driver type

packages/aoa-demo/
├── src/aoa/demo/model/identity/
│   ├── resources/identity_store.py # EDIT: two private reads — `_list_persons` through `_fetch`,
│   │                              #       `_count_persons` through `_fetchval`; the module diagram names
│   │                              #       them; the driver-free base and the in-memory store untouched
│   └── README.md                   # EDIT: what the PostgreSQL store reads, and through which helpers
└── tests/
    └── test_identity_postgres.py   # EDIT: `_FakeConnection` gains `fetch`/`fetchval` and seeded rows;
                                    #       cases for the list (mappings, order, bound) and the count (a number)

docs/
├── extensions/postgresql.md (+ .ru_draft.md)              # EDIT: the helper list carries four, and the
│                                                          #       page-and-count example is added
└── how-to/authoring-resource.md (+ .ru_draft.md)          # EDIT: same, in the section that sends a
                                                           #       subclass to the protected helpers

examples/extensions/postgresql/
├── 15_fetch_and_fetchval.py       # NEW: the page-and-count case over the recording harness
└── 15_fetch_and_fetchval.ipynb    # NEW: the same case, cell by cell

packages/aoa-action-machine/CHANGELOG.md                   # EDIT: one `### Added` article under
                                                           #       `## [Unreleased]`
```

**Structure Decision**: the two helpers live on `PostgresResource` and nowhere else. That is the only class in the
repository that holds a connection and knows what the driver's errors look like; putting them on `SqlResource` would
put driver-shaped members back into a contract a nested action receives, and adding them to the wrapper would
recreate the reach-through by another name. The pair therefore extends the driver's private surface, and the
public/protected contract is untouched by construction — the wrapper does not inherit from `PostgresResource`, so a
nested action cannot reach the new members even by inheritance.

The demo's demonstration is deliberately the smallest one that satisfies the issue: two private reads on the
PostgreSQL store, called by the demo's suite. Widening it — a public operation, an action, a route — would grow the
demo's surface for a library change and is recorded as out of scope in the spec.

## Test design

Every case below runs with no database and lives beside the existing pair's cases.

| Case | Where | Proves | Adversarial break that must make it fail |
| --- | --- | --- | --- |
| `_fetch` on a resource that never opened | `test_postgres_helpers.py` | FR-005, SC-003 | drop the `_require_connection()` call — the test then sees `AttributeError` |
| `_fetchval` on a resource that never opened | same | FR-005, SC-003 | same |
| both on a resource closed after opening | same | FR-005, SC-003 | return the stale `_conn` instead of asking the check |
| driver refusal arrives chained, both | same | FR-006, SC-004 | raise the driver's error directly instead of wrapping it |
| `_fetch` answers `[]` for no match | same | FR-002, SC-001 | answer `None`, or `self.row` |
| `_fetch` answers a list of one for one row | same | FR-001, SC-001 | answer the row itself |
| `_fetch` answers all rows in order, with `ORDER BY` | same | FR-001, SC-001 | return `rows[:1]` |
| `_fetch` answers all rows without an ordering | same | FR-001, SC-001 | sort the answer, which the helper must not do |
| `_fetchval` answers the first value of the first row | same | FR-004, SC-002 | answer the row, or a tuple of it |
| `_fetchval` answers nothing for no match | same | FR-004, SC-002 | answer `0` |
| parameters forwarded positionally; `None` equals `()` | same | FR-007, SC-005 | drop the `*params if params else ()` and pass `params` as one argument |
| `_fetch`'s annotation names no driver type | same | FR-008 | annotate `list[asyncpg.Record]` |
| exactly four query helpers | same | FR-009, SC-006 | add `_fetchmany` |
| demo's `_list_persons` answers mappings, in order, bounded | `packages/aoa-demo/tests/test_identity_postgres.py` | FR-015 … FR-017, SC-007 | return raw records; drop `ORDER BY`/`LIMIT`; call `self._conn.fetch` directly |
| demo's `_count_persons` answers a number | same | FR-016, SC-007 | return the record; reach for the connection |
| the pair is absent from the wrapper | `test_postgres_helpers.py` | FR-013 | inherit `PostgresResource` on the wrapper |

The parameter cases mirror `test_parameters_reach_the_connection_positionally` and
`test_none_and_an_empty_tuple_are_the_same_call`, which already exist for the pair; the new ones extend the same
`FakeConnection.calls` assertion rather than inventing a second instrument.

## Documentation design

- `docs/extensions/postgresql.md`, section **Installation and construction**: the bullet list that today names
  `_execute` and `_fetchrow` names four helpers, and the paragraph beneath it states the one check and the one error
  for all four. The section gains the worked example: a page through `_fetch(query, (limit, offset))` and a count
  through `_fetchval("SELECT count(*) …")`, showing that a count answers a number and that a domain that must tell
  "no row" from a SQL `NULL` asks for the row instead.
- The page gains a case section of its own — `## 15. Reading a page and a count through the protected helpers` — with
  the `[Python](…)` and `[Notebook](…)` links its other cases carry. It shows every answer the pair introduces, not
  the happy path alone: the page with rows, the page with no match (`[]`), the count (`2`), and a count of no match
  (`None` from the helper, `0` at the call site). Principle VI.4 makes "each answer appears, named as a case" binding,
  and `[]` and `None` are the two answers a reader is most likely to get wrong.
- `docs/how-to/authoring-resource.md`, section **If the implementation uses PostgreSQL**: the paragraph that
  presents "two protected helpers" presents four, and the example method list gains the page and the count.
- Because constitution principle VI requires every case as a script **and** a notebook, the page-and-count case is
  also added as `examples/extensions/postgresql/15_fetch_and_fetchval.py` with its `.ipynb`: the same
  `RecordingConnection`/`RecordingPool` harness the neighbouring cases use, extended with `fetch`/`fetchval`, and a
  domain resource whose `list_notes` and `count_notes` call the two helpers. The script is run with the repository's
  environment while the page is written, and `tests/examples` is the gate that executes it — the check run does not
  run the examples runner, so it is run as its own command.
- Both pages have a `*.ru_draft.md` beside them; the draft is updated with the same content and stays uncommitted.
- `packages/aoa-action-machine/CHANGELOG.md`: one article under `## [Unreleased]` / `### Added`, in plain words —
  a domain resource can now read a list of rows and a single value through the driver it holds, without a query
  member entering the SQL contract, and without any change needed by an existing consumer.

## Complexity Tracking

No constitution gate is violated and no structural compromise is taken: one class gains two methods, one fake
connection gains two driver calls, the demo gains two private reads, two pages gain a listing and an example, and
one example pair is added for the case the pages teach. Nothing needs justification, so this table is empty by
design.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
