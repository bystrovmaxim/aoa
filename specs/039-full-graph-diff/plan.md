# Implementation Plan: Maxitor Compares Two Versions on the Full Graph

**Branch**: `feature/issue-291-full-graph-comparison` | **Date**: 2026-10-31 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/039-full-graph-diff/spec.md`

## Summary

In Diff the full graph draws the union of A and B with its own layout, marks nodes and edges from the comparison, counts the drawn nodes on the version button, opens the card on a marked node, and gets a filter panel in One and in Diff. The server gives edges their protocol ids and nodes their type slug; everything else is client code, built like the ERD's Diff. Acceptance is on the extended `erd-full` stand; gameoffer's numbers are checked after the merge. Decisions: [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.12 (Maxitor's server), TypeScript 5.7, React 19 (client)

**Primary Dependencies**: AntV G6 5, d3-force-3d, MUI; `maxitor.graph_compare`; AOA actions

**Storage**: IndexedDB (remembered arrangements, unchanged); DuckDB per held version, unchanged

**Testing**: pytest, vitest, Playwright cross-engine script, `scripts/run_checks_with_log.sh`

**Target Platform**: Chromium, Firefox, WebKit, Safari; desktop and phone width

**Project Type**: web application (`packages/maxitor/front`, `client/`)

**Performance Goals**: no bound of its own: a union takes about one layout of the graph, as One; a pair's second opening runs no layout (SC-004)

**Constraints**: same positions on every engine; no test code in production; endpoints only through actions

**Scale/Scope**: about 3 200 nodes and 4 800 edges

## Constitution Check

| Rule | State |
|---|---|
| I. Maintainer decides | Pass: nothing committed without an instruction; each phase's commit waits for it |
| II. English | Pass: code and spec in English; only `tasks.ru_draft.md` and the documentation's Russian draft are not |
| III–V. Headers, AI-CORE, docstrings | Pass: applies to the touched `full_graph_action.py`; new TypeScript follows its file header style |
| VI. Tail | Pass: three reserved tasks, in order; the documentation shows every case as script and notebook |
| API only through actions | Pass: no new endpoint |

Re-checked after design: no change.

## Project Structure

### Documentation

```text
specs/039-full-graph-diff/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── maxitor-api.md
│   └── ui.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code

```text
packages/maxitor/front/
├── src/maxitor/front/model/diagrams/actions/full_graph_action.py   # edge ids, type_slug
├── tests/                                                          # the answer's shape and ids
└── client/
    ├── scripts/check-layout-determinism.ts                         # a two-version history
    └── src/
        ├── api/fullGraph.ts                                        # read for a base; domainMembers
        ├── lib/fullGraphDiff.ts                                    # new: union, visibility, counts
        ├── lib/diffCounts.ts, lib/erdDiff.ts                       # edgesMarked
        ├── lib/erdDiffCard.ts, components/history/DiffCard/        # a node's card
        ├── lib/viewUrl.ts                                          # the filters in the address
        ├── components/ui/ErdFilterPanel/                           # kindsTitle
        ├── components/ui/NodeTypeLegend/                           # removed
        └── components/diagrams/FullGraphViewer/                    # marks, click, panel, README
```

**Structure Decision**: no new package; the pure logic goes to `lib/fullGraphDiff.ts`, beside `erdDiff.ts`.

## Phases

Each is one commit, on the maintainer's word; the spec is committed first, as for #290.

0. The specification.
1. The union on the full graph: edge ids, type slug, union, layout, cache entry, cross-engine check.
2. Drawing the comparison: marks, edges, fading, counts, card.
3. Filters: the panel, visibility, address, room.
4. Closing: check run, documentation, changelog (three commits).

The stand is extended before phase 2's walk, out of git. Phase 3 is not in the issue yet.

## Complexity Tracking

None.
