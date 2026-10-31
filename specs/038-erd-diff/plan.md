# Implementation Plan: Maxitor Compares Two Versions on the ERD

**Branch**: `feature/issue-290-erd-diff` | **Date**: 2026-10-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/038-erd-diff/spec.md` (issue #290, step 5 of 9 of #273)

## Summary

A new standard-library module, `maxitor.graph_compare` in `packages/maxitor/core/`, compares two documents of the Open Gnomon Protocol by `id`: a status for every node and edge, every difference of a changed one by property path, the counts; `1.0` edges get #285's ids from a copy of the rule kept in step with AOA's by a test. `graph-builder`'s own `differences` becomes a formatter over it, so the package has one comparison. Maxitor's server keeps each held graph's JSON text, guards a second source `a` in the same middleware as `source`, and serves two AOA actions — the statuses and counts of a pair, and one element's differences — holding each pair's comparison once, keyed by content so a rebuilt Live recomputes by itself. The client turns Diff on: a range on the track with the pass-over rules, `mode`/`a`/`b` in the address and the room, the ERD drawn from A's and B's slices merged and marked, the counts on the version button, the card, the two messages and the versions between, the left panel's union, and the phone.

## Technical Context

**Language/Version**: Python ≥ 3.12 (comparison, server); TypeScript 5.7, React 19, MUI (client).

**Primary Dependencies**: none new. The comparison uses the standard library only; the server AOA (`aoa-action-machine`, `aoa-fastapi-adapter`), DuckDB as today; the client Graphviz WASM as today.

**Storage**: none new. Process memory: `GraphEntry.document`, `ComparisonStore` (32 pairs).

**Testing**: pytest (the module's own suite, graph_builder's unchanged suite, the front's suite with a stand-in port); vitest + Testing Library; the ERD style check scripts on the real WASM; the boundary checker; the check run.

**Target Platform**: Maxitor's server and its browser client, desktop and phone; the stand.

**Project Type**: a library part of the `maxitor` package plus the existing web application.

**Performance Goals**: two demo graphs (3 213 nodes, 4 841 edges) compared in under 1 s (measured ≈ 20 ms with parsing, research R6); a pair compared once whatever the readers; the compare read lists only changed elements.

**Constraints**: the module imports only the standard library (boundary checker + its own import test); every endpoint is an AOA action; every key and log rule of spec 037 holds for the second source; card values are text, never HTML; colour is never the only mark (`+ − ~`).

**Scale/Scope**: one new module (≈ 4 files) and its tests; ≈ 6 server modules touched or added; ≈ 12 client modules and components touched or added.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How the plan meets it | Status |
|---|---|---|
| I. The maintainer decides | Each phase is a commit made only on the maintainer's word; no push, PR or merge without it. | ✅ |
| II. English | Code, docs, commits in English; only `tasks.ru_draft.md` and the documentation page's `*.ru_draft.md` in Russian. | ✅ |
| III. Module headers | Every new Python module opens with its path, title, `PURPOSE`, `ARCHITECTURE / DATA FLOW`. | ✅ |
| IV. AI-CORE blocks | `compare`, `Comparison`, `GraphNotComparableError`, the two actions, `ComparisonStore` carry one; methods one line. | ✅ |
| V. Short docstrings | Every class, function and method, server and client. | ✅ |
| VI. Tail | Phase 9 is three commits: check run, documentation (how-to page with every case, an executed example as script and notebook, READMEs, Russian draft), changelog article. | ✅ |
| Final step: the check run | Taken to zero; the two accepted remarks stay. | ✅ |

House rules: endpoints only through actions — `CompareVersionsAction`, `CompareElementAction`, and the room's range through `SetRoomVersionAction`; the comparisons are held in a resource (`ComparisonStore`). ✅

No violations; Complexity Tracking stays empty. **Re-checked after Phase 1**: the contracts add no route outside an action and no import across a boundary; `graph_compare` depends on nothing. ✅

## Project Structure

### Documentation (this feature)

```text
specs/038-erd-diff/
├── spec.md, plan.md, research.md, data-model.md, quickstart.md
├── contracts/
│   ├── graph-compare.md   # compare(a, b), its result and refusals
│   ├── maxitor-api.md     # the two compare reads, `a` in the middleware
│   ├── room-protocol.md   # `a` in the room's `version`
│   └── ui.md              # the switch, button, track, messages, marks, card, left panel
├── checklists/requirements.md
└── tasks.md (+ tasks.ru_draft.md)
```

### Source Code

```text
packages/maxitor/
├── core/graph_compare/                      # new
│   ├── README.md
│   ├── pytest.ini
│   ├── src/maxitor/graph_compare/
│   │   ├── __init__.py                      # compare, Comparison, Status, Change, Difference, Counts, GraphNotComparableError
│   │   ├── comparison.py                    # the result types
│   │   ├── compare.py                       # compare(a, b)
│   │   ├── edge_ids.py                      # #285's rule for 1.0 edges
│   │   └── py.typed
│   └── tests/                               # every case of contracts/graph-compare.md; stdlib-only imports; demo pair < 1 s
├── tools/graph_builder/src/maxitor/graph_builder/differences.py   # a formatter over compare (R3)
├── pyproject.toml                           # the part in only-include, dev-mode-dirs, sources
├── front/src/maxitor/front/
│   ├── api/
│   │   ├── graph_store.py                   # GraphEntry.document
│   │   └── graph_source_middleware.py       # `a` guarded on /api/v1/compare*; current_base_entry()
│   └── model/
│       ├── core/actions/load_aoa_service_action.py   # the graph's text to the result
│       ├── diagrams/
│       │   ├── actions/compare_versions_action.py    # new
│       │   ├── actions/compare_element_action.py     # new
│       │   └── resources/comparison_store.py         # new
│       └── rooms/actions/set_room_version_action.py  # `a`, the range rules
│   └── tests/                                        # stand-in port; the two reads; Live recompute; edge rule = AOA's
└── front/client/src/
    ├── lib/
    │   ├── versionRange.ts                  # new: the range rules (R13)
    │   ├── urlState.ts                      # `mode`, `a`
    │   ├── erdDiff.ts                       # new: mergeErdPayloads, markErd, diagram counts (R10, R11)
    │   ├── sidebarDiff.ts                   # new: mergeSidebars (R15)
    │   └── buildDotSource.ts                # the marks, the retargeted line (R12)
    ├── api/compare.ts                       # new: the two reads, key header
    ├── components/history/
    │   ├── VersionTrack/                    # range mode: two handles, dark stretch, keys
    │   ├── VersionPicker/                   # Diff on; "needs two versions"
    │   ├── VersionButton/                   # A → B and the counts
    │   ├── VersionMessage/                  # reused twice
    │   ├── VersionsBetween/                 # new, with README and index.ts
    │   └── DiffCard/                        # new, with README and index.ts
    ├── components/diagrams/ErdViewer/       # Diff wiring, card on click
    ├── components/navigation/LeftSidebar/   # the union and its marks
    ├── app/App.tsx                          # the range state
    └── rooms/                               # protocol, roomStore, useRoomSession: `a`
```

Registration of the new part, outside the package: root `pyproject.toml` (source paths, `mypy_path`, `typecheck`, per-path Ruff entry), `scripts/check_run.py` (its tests), `scripts/package_boundaries.toml` (`[standalone.graph_compare]`; `graph_compare` in the front's and the port's `may_import`).

Outside: `docs/how-to/compare-two-versions.md` (+ `.ru_draft.md`), `examples/step_26_maxitor/17_compare_two_versions.{py,ipynb}`, the front's, the package's and the new part's READMEs, `docs/CHANGELOG.md`.

**Structure Decision**: the comparison is a part of its own under `core/`, beside `front/` and `tools/`, with the same `src`/`tests` shape as `tools/graph_builder/`; everything else extends the existing web application where its One-version counterpart lives.

## Phases → commits

| # | Phase (issue #290, §5) | Contents | Proof | Adversarial break |
|---|---|---|---|---|
| 0 | Design documents | `specs/038-erd-diff/` | — | — |
| 1 | The comparison of two graphs | `core/graph_compare` and its registration; `graph_builder.differences` over it; the front-side test that the copied edge rule equals AOA's | every status; two edges between one pair of nodes; a retarget is changed with `target_id`; a nested path; `1.0` vs `1.1`; a rename; equal graphs; refusals; stdlib-only imports; the demo pair < 1 s; graph_builder's tests unchanged | drop the `entity_relation` member from the copied rule → the `1.0` and keep-in-step tests fail; import `json` from a third-party shim → the import test fails; compare lists by item → the list-as-value test fails |
| 2 | Picking a range | `versionRange.ts`, `VersionTrack` range mode, `VersionPicker` Diff on, `urlState` `mode`/`a`, App's range state, rooms `a` (client and `SetRoomVersionAction`) | pass-over, drop on the other, Live only as B, keys with and without Shift, One ↔ Diff, a reversed link, a room move, a refused range | let a drop land on the other handle → the never-meet test fails |
| 3 | The comparison on the server | `GraphEntry.document`, `a` in the middleware, `ComparisonStore`, the two actions | statuses and counts; one element's differences; a second reader does not recompute; Live rebuilt → new comparison; a wrong key on `a` is `404`; no key or address in a log | key the store by source → the Live-recompute test fails; skip the guard on `a` → the wrong-key test fails |
| 4 | The ERD comparison | `api/compare.ts`, `erdDiff.ts`, `buildDotSource` marks, the retargeted line, the button's counts, "no changes", Live recompute on the client | marks per status on fixtures; a retarget is one amber link (two DOT edges, one dashed); counts = marks; "no changes" fades nothing; the style check on WASM | draw a retarget as removed + added → the one-amber-link test fails |
| 5 | The card | `DiffCard`, opened from marked tables and rows | every changed property with both values; added/removed wording; values as text | render values as HTML → the `<script>` test fails |
| 6 | The messages | two `VersionMessage`s, `VersionsBetween` | A left, B right; between newest first; a row opens whole; none when adjacent; Live's line on B's side | order between oldest first → its test fails |
| 7 | Pages in one version only | `sidebarDiff.ts`, the left panel's marks, a one-sided page | `+`/`−` marks; a page only in B all green | merge by label instead of page key → the union test fails |
| 8 | Phone | the button's short form, the sheet's stacked messages, 44 px handles | phone-width tests | 24 px handles → the touch-target test fails |
| 9a | Check run | `bash scripts/run_checks_with_log.sh` to zero | green log | — |
| 9b | Documentation | how-to with every case (statuses, paths, `1.0`, refusals, range rules, marks, "no changes", one-sided pages), example script + notebook (executed), READMEs, `.ru_draft.md` | the example runs | — |
| 9c | Changelog | one article | — | — |

## Complexity Tracking

No constitution violations.
