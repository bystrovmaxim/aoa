# Implementation Plan: Maxitor Compares Two Versions on Use-Case Diagrams

**Branch**: `feature/issue-292-use-case-diff` | **Date**: 2026-10-31 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/041-use-case-diff/spec.md`

## Summary

A pure function walks each action's parts in both graph documents and says which changed; the comparison store keeps its answer per pair, and one new read gives it. The client reads the use-case diagram of A and of B, merges them as the ERD merges its slices, marks each element from the comparison and from "changed inside", and draws with the existing Graphviz path. The card, the stepper and the filter panel are the ERD's, reused.

## Technical Context

**Language/Version**: Python 3.12 (Maxitor's server, `graph_compare`), TypeScript 5.7, React 19 (client)

**Primary Dependencies**: no new ones; `@hpcc-js/wasm-graphviz`, the existing `ErdFilterPanel`, `DiffCard`, `ChangeStepper`

**Storage**: none new; the answer is held beside the comparison in `ComparisonStore`, in memory, per pair

**Testing**: pytest, vitest, the check run, a walk in the browser on `erd-full`

**Target Platform**: as Maxitor: desktop browsers and phone width

**Project Type**: web application (`packages/maxitor/front`, `client/`, `packages/maxitor/core/graph_compare`)

**Performance Goals**: the new computation stays within the comparison's bound by a test on the demo's graph; a diagram opens as fast as the ERD in Diff

**Constraints**: endpoints only through actions, storage only through a resource, no test code in production, the ERD's and the map's marks untouched

**Scale/Scope**: the demo's graph: 61 actions, a domain's diagram in tens of elements

## Constitution Check

| Rule | State |
|---|---|
| I. Maintainer decides | Pass: each phase's commit waits for the maintainer's word |
| II. English | Pass: only `tasks.ru_draft.md` and the documentation's Russian draft are not |
| III–V. Headers, AI-CORE, docstrings | Pass: applies to every new module and to what is touched |
| VI. Tail | Pass: three reserved tasks, in order; every case as a script and a notebook |
| API only through actions, storage through a resource | Pass: one new action, the store extended |

Re-checked after design: no change.

## Project Structure

### Documentation

```text
specs/041-use-case-diff/
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
packages/maxitor/core/graph_compare/
├── src/maxitor/graph_compare/changed_inside.py     # new: the walk, pure
└── tests/test_changed_inside.py                    # new
packages/maxitor/front/
├── src/maxitor/front/model/diagrams/
│   ├── actions/changed_inside_action.py            # new: GET /api/v1/compare/changed-inside
│   ├── actions/domain_use_case_diagram_action.py   # each link gets its protocol id
│   ├── actions/domain_use_case_diagram_action_schema.py
│   └── resources/comparison_store.py               # holds the walk's answer per pair
├── src/maxitor/front/api/app.py                    # the route
├── tests/test_changed_inside_read.py               # new
└── client/src/
    ├── api/compare.ts                              # the new read
    ├── lib/useCaseDiff.ts                          # new: union, marks, counts, changes
    ├── lib/useCaseDiff.test.ts                     # new
    ├── lib/buildDomainUseCaseDotSource.ts          # marks and fading in the DOT
    ├── lib/filterUseCaseDiagramByDomains.ts        # the Changes filter
    ├── components/history/DiffCard/DiffCard.tsx    # parts, grouped
    └── components/diagrams/UseCaseDiagramViewer/   # Diff, card, stepper, panel
```

**Structure Decision**: the walk lives in `graph_compare`, beside `compare`, because it is a pure question about two documents; the union lives in the client, because that is where the ERD's lives and the viewer already reads a diagram per version.

## Phases (one commit each)

1. The server says what changed inside.
2. Marks and counts on the diagram.
3. The card.
4. The stepper.
5. The filter panel with the gear shift.
6. The closing three: check run, documentation, changelog.

The issue lists three phases; 1, 4 and 5 are added to it before implementation.

## Complexity Tracking

None.
