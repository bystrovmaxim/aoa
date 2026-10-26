# Implementation Plan: A Built Graph Without the Indexes It Does Not Need

**Branch**: `feature/issue-268-graph-memory-indexes` | **Date**: 2026-10-26 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/025-graph-index-memory/spec.md` (issue #268)

## Summary

A built graph of the reference source takes 43.5 MiB, and 38 MiB of that is the 21 primary keys and 64 indexes the build creates. A measurement helper beside `payload_wire_metrics.py` records each graph's memory, build time, query timings and a fingerprint of every answer. `EXPLAIN` then showed that no plan reads through any index. Research R1 shows that a build with **no** primary key and **no** index reaches the target: 13.4 MiB against a target of 14.5; removing the indexes alone makes a graph larger. Measured from outside, the process gains 22.0 MiB per graph instead of 54.3. So the expected change is to remove both, guard duplicate node ids with one query after loading, and pin the result with a test that checks both the schema's shape and its memory. If an index proves necessary for the timings, the smallest variant that keeps them ships, even above a third. The schema stays only if nothing smaller is possible. The Linux image's process size is measured separately and written into the store's documentation.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: DuckDB 1.5.6 (locked), `aoa-action-machine` (actions are timed through `ActionProductMachine`), httpx (the helper reads a graph by URL)

**Storage**: one in-memory DuckDB database per built graph

**Testing**: pytest (`packages/aoa-maxitor/tests`); the payload and route tests already there prove that answers are unchanged

**Target Platform**: macOS for development; the stand's Linux image built from `packages/aoa-maxitor/Dockerfile` (`python:3.12-slim`, glibc) for FR-014

**Project Type**: web application. Only the backend's graph build changes; the client is untouched.

**Performance Goals**: one built reference graph ≤ a third of its starting memory (≤ 14.5 MiB on the 2026-10-26 figure; the target of FR-008, not a gate, per FR-009); the process size per held graph at least halved (54.3 → 22.0 MiB measured); every diagram query and the sidebar build stay within +20 % or +1 ms of their median, whichever is larger, and ≤ 50 ms

**Constraints**: diagram answers byte-for-byte identical; `aoa-maxitor` must not import `aoa-demo` (package boundaries), so the demo's graph reaches the helper as a file

**Scale/Scope**: in production, the schema and the duplicate check change in `duckdb_graph_resource.py`. Diagram actions under `model/diagrams/actions/` change only if a query without `ORDER BY` returns rows in another order (see Risks), and then only by that `ORDER BY`. Added: one test helper, two test modules, one example pair, the docs, and the saved reference graph.

## Constitution Check

*GATE: checked before Phase 0 and again after Phase 1.*

| Principle | How this plan meets it | Status |
|---|---|---|
| I. The maintainer decides | Every phase ends in a commit **prepared and shown**, not made. The index usage table goes to the issue as a comment only after the maintainer says so in the conversation, although the issue's own phase 2 asks for it. | Pass |
| II. English | Code, docstrings, tests, examples, commit messages, the issue comment: English. Russian only in `*.ru_draft.md`, which Git ignores. | Pass |
| III. Module headers | The new test helper and test modules open with the path line and a `Name — purpose.` docstring. `duckdb_graph_resource.py`'s header is corrected: it says `_install_database` creates the indexes, which is already untrue. | Pass |
| IV. AI-CORE blocks | `DuckDBGraphResource`'s block gains the invariant "a node id is unique within its table; the build refuses a duplicate". No block on a method or in a test helper. | Pass |
| V. Short docstrings | Every new function carries a one-line docstring. | Pass |
| VI. Tail | Three final tasks, in order: check run to zero, documentation (each case as a script and a notebook), changelog article. | Pass |
| Check run | No new step; the guard runs as an ordinary test, which only the local check run executes (CI does not run pytest). The two accepted remarks stay. | Pass |

Post-design re-check: no new package, no new dependency, no cross-package import (`check_package_boundaries.py` unaffected). Production code gains no test hook: the helper times the actions through the action machine, as the tests do. **Pass.**

## Project Structure

### Documentation (this feature)

```text
specs/025-graph-index-memory/
├── spec.md
├── plan.md              # this file
├── research.md          # R1–R7 and the measurements
├── data-model.md        # schema variants, measurement, index usage, duplicate check
├── quickstart.md        # end-to-end validation
├── contracts/
│   └── graph-build.md   # the duplicate refusal and the measurement report
├── index-usage.md       # phase 3 output: the EXPLAIN table (also posted to the issue)
├── data/
│   └── ref-graph-2026-10-26.json.gz   # the reference source as measured; "before" and "after" read this copy
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/resources/
└── duckdb_graph_resource.py       # no PRIMARY KEY, no CREATE INDEX (if phase 3 confirms); duplicate-id check after loading; header and AI-CORE corrected

packages/aoa-maxitor/tests/
├── graph_build_metrics.py         # NEW: memory by tag, process size per graph, build time, query medians, answer fingerprints, EXPLAIN index usage, RSS sequence; CLI over a URL or a JSON file (.json or .json.gz)
├── test_duckdb_duplicate_node_id.py   # NEW: duplicate refused with its id; repeat across tables accepted; refusal through the store
└── test_duckdb_graph_memory.py    # NEW: the regression guard (FR-013): schema shape from the catalogue + memory ceiling

examples/step_26_maxitor/
└── 03_graph_memory.py / .ipynb    # NEW: memory of a built graph; a duplicate refused; a repeat across tables accepted

docs/tutorials/step-26-maxitor.md (+ .ru_draft.md)   # a section on what a graph costs
packages/aoa-maxitor/README.md (+ .ru_draft.md)      # memory under MAXITOR_MAX_GRAPHS, the Linux finding
docs/CHANGELOG.md
```

**Structure Decision**: the measurement is test tooling, not product. It lives in `tests/` beside `payload_wire_metrics.py`, as the issue asks, and runs as `python -m tests.graph_build_metrics` from `packages/aoa-maxitor`. Production code changes in `duckdb_graph_resource.py`, plus an `ORDER BY` in a diagram action only where phase 5 finds one missing.

## Phases (one commit each)

The duplicate check lands **before** the primary keys go. That reverses the issue's phases 3 and 4, so that no commit ever builds a graph that accepts a duplicate node. While the primary keys are still there, the new test passes on either protection. It is verified adversarially by removing both protections locally: the test must then fail.

1. **Specification artifacts**: spec, checklist, plan, research, data model, contract, quickstart, tasks.
2. **Measurement**: `tests/graph_build_metrics.py`, and the baseline recorded for the reference source and the demo's graph, including the process size per graph (US1, FR-001, FR-002, FR-004).
3. **Which index does which query use**: `EXPLAIN` over every query; `index-usage.md`; the table posted to the issue (US1, FR-003). Research R2a already shows that no plan reads through any index on either graph; this phase records the proof in an empty table. It changes Phase 5 only if a plan names an index.
4. **Keep the duplicate-id check**: the check after loading, and its tests (US3, FR-010 to FR-012). Skipped only if phase 3 shows that the primary keys must stay, which R1 makes unlikely.
5. **Remove what is not needed**: the schema change; before/after figures, both the database's and the process's; the guard test (US2, FR-004 to FR-009, FR-013). If nothing smaller than today keeps the answers and timings (FR-009), this commit carries only the measurements, and no schema change.
6. **Memory on Linux**: the RSS sequence in the stand's image; settings tried; results recorded (US4, FR-014).
7. **Check run taken to zero.**
8. **Documentation**: example script and notebook, tutorial section, README note including FR-015, and their `.ru_draft.md`.
9. **Changelog**: one article.

## Risks recorded

- **The jump in table memory without indexes (R1) is not explained.** It does not affect the expected variant: one index on top of "nothing" was measured at 14.38 MiB. But a mix that keeps primary keys may land anywhere up to 50 MiB. Each candidate is therefore measured as a whole build, never estimated by subtraction.
- **The target has 1.1 MiB to spare** (13.38 MiB against 14.50), and it rests on an unexplained figure. The process-size measurement (R1, FR-004) confirms the direction from outside the database: 54.3 → 22.0 MiB per graph. The duplicate check adds no stored structure, but phase 5 measures the final build, not the variant of R1. Missing the third by a little no longer throws the work away (FR-009).
- **The database's figure is not the process's.** It falls 3.3 times while the process falls 2.5 times. Both are reported, and the changelog speaks in the process figure, which is what a stand operator sees.
- **A future DuckDB upgrade may change per-index costs.** The guard's memory layer then fails or passes for reasons unrelated to this repository. Its message names the measured value and the ceiling, so the person upgrading can re-measure and move the ceiling deliberately. Its shape layer is unaffected.
- **The guard runs only locally.** CI does not run pytest today, and the ceiling was measured on macOS. The test's docstring says both.
- **Linux may not be measurable locally.** If the image cannot be built or run, phase 6 records that, and the README says the Linux behaviour is unmeasured rather than guessing.
- **Answers that depend on row order.** Without a primary key, DuckDB may return rows in a different order where a query has no `ORDER BY`. The byte-for-byte comparison of phase 5 catches this. The fix is an explicit `ORDER BY` in that query, which changes no answer that was already ordered.

## Complexity Tracking

No constitution violations to justify.
