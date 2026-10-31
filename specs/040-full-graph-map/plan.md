# Implementation Plan: Maxitor's Full Graph as a Map

**Branch**: `feature/issue-319-full-graph-map` | **Date**: 2026-10-31 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/040-full-graph-map/spec.md`

## Summary

The full graph becomes a map of three levels. The server lays each domain out with Graphviz, keeps the areas' places per history, and answers an overview and one area at a time; the comparison and its counts come from the server too. The browser draws with Sigma.js 4 and WebGL, reading only what is near the view. The filter panel gains the gear shift on the full graph, and moving it opens its section on every diagram with the panel. A prototype on 96 thousand nodes met most thresholds and missed three, recorded in [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.12 (Maxitor's server), TypeScript 5.7, React 19 (client)

**Primary Dependencies**: new: `sigma` 4, `graphology`, `@sigma/node-border`, `@sigma/node-image`, native Graphviz. Removed once unused: `@antv/g6`, `@antv/layout`.

**Storage**: the map of a version and the places of a history, stored through a resource

**Testing**: pytest, vitest, the Playwright cross-engine check, the measured session on the generated graph

**Target Platform**: Chromium, Firefox, WebKit, real Safari; desktop and phone width

**Project Type**: web application (`packages/maxitor/front`, `client/`)

**Performance Goals**: SC-001 – SC-006 on about 100 000 nodes and 150 000 links

**Constraints**: endpoints only through actions, storage only through a resource, no test code in production, no Python or AOA assumptions in the map beyond what the graph file says

**Scale/Scope**: 100 thousand nodes now; a level for services comes later and must not be ruled out

## Constitution Check

| Rule | State |
|---|---|
| I. Maintainer decides | Pass: each phase's commit waits for the maintainer's word |
| II. English | Pass: code and spec in English; only `tasks.ru_draft.md` and the documentation's Russian draft are not |
| III–V. Headers, AI-CORE, docstrings | Pass: applies to every new module and to what is touched |
| VI. Tail | Pass: three reserved tasks, in order; every case as a script and a notebook |
| API only through actions, storage through a resource | Pass |

Re-checked after design: no change.

## Project Structure

### Documentation

```text
specs/040-full-graph-map/
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
packages/maxitor/core/graph_map/                 # new: areas, homes, levels, bundles, from a graph document
packages/maxitor/front/
├── Dockerfile                                   # Graphviz in the image
├── src/maxitor/front/model/diagrams/
│   ├── actions/map_overview_action.py           # new
│   ├── actions/map_area_action.py               # new
│   └── resources/map_store.py                   # new: layouts, places, maps
└── client/
    ├── scripts/                                 # the generator, the measured session, the cross-engine check
    └── src/
        ├── api/map.ts                           # new
        ├── components/diagrams/MapViewer/       # new, replaces FullGraphViewer
        ├── components/ui/ErdFilterPanel/        # the section follows the gear shift; kindsTitle
        └── lib/viewUrl.ts, lib/diffCounts.ts    # filters in the address, counts
```

**Structure Decision**: what reads a graph document goes to `packages/maxitor/core/`, like `graph_compare`, so it needs nothing of AOA. The viewer is a new component: nothing of G6 is worth carrying.

## Phases

Each is one commit, on the maintainer's word.

0. The specification and the plan.
1. The gear shift opens its section, on the ERD: small and on its own.
2. The layout on the server: areas, homes, Graphviz, places, the store.
3. Reading in parts: the two actions, the generated graph, the measuring session.
4. The map: the viewer, levels, zoom, first paint. **The look gate: the maintainer approves it here, before going on.**
5. The comparison on the map: the union and counts on the server, the marks, the card, stepping through changes.
6. Filters, paint and rooms on the map; phones; real Safari.
7. Closing: check run, documentation, changelog (three commits).

The thresholds missed so far are taken in phases 4 and 6. If one cannot be reached, the steps down are #319's, §5.

## Risks

| Risk | Where it is settled |
|---|---|
| The look comes out plainer than today | phase 4, the gate |
| Filters over 50 ms beyond about 3 000 loaded nodes | phase 4 |
| First paint: a block of up to 1 s | phase 4 |
| Real Safari | phase 4, not left to the end |
| Places of the areas are untested | phase 2 |
| Native Graphviz differs from WebAssembly | phase 2 |

## Complexity Tracking

| What | Why it is needed | Simpler option rejected because |
|---|---|---|
| A store of places per history | `sfdp` per version moved 571 of 571 areas for one removed field | laying out per version breaks FR-016 |
| A new package in `core/` | the map must not depend on AOA or DuckDB | inside the front it would need the front's graph store |
