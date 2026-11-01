# Implementation Plan: Maxitor: One Card on Hover, and Tables That Collapse

**Branch**: `feature/issue-320-283-field-card-and-collapse` | **Date**: 2026-11-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/043-field-card-and-collapse/spec.md`

## Summary

One new read, `element-card`, gives what a card shows beyond the diagram: an element's kind, name and description. `list-entities` gains a row's lifecycle id. The client gets one `ElementCard`, opened by one hook that takes the hover the room already shares, so a person and a follower run the same path. A lifecycle miniature is the existing Graphviz path at card size, kept per version or pair. Collapsing is a filter of the rows `buildDotSource` draws, held in two page settings, so the address and the room carry it as they carry filters.

## Technical Context

**Language/Version**: Python 3.12 (Maxitor's server), TypeScript 5.7, React 19 (client)

**Primary Dependencies**: no new ones; `@hpcc-js/wasm-graphviz`, sigma, the existing `DiffCard` body, `usePageSetting`, `focusStore`

**Storage**: none; a miniature is kept in memory for the tab

**Testing**: pytest, vitest, the check run with `check-layout-determinism.ts`, a walk on `erd-full`

**Target Platform**: as Maxitor: desktop browsers and phone width

**Project Type**: web application (`packages/maxitor/front`, `client/`)

**Performance Goals**: no read and no draw for an element merely crossed; a second opening reads nothing

**Constraints**: endpoints only through actions; no test code in production; the protocol's published versions unchanged; FR-031's drawing the same apart from the control

**Scale/Scope**: the demo's ERD of hundreds of tables, 201 lifecycles, a map of tens of thousands of elements

## Constitution Check

| Rule | State |
|---|---|
| I. Maintainer decides | Pass: the maintainer asked for all tasks without waiting; no commit, push or pull request is made, those still need their word |
| II. English | Pass: only `tasks.ru_draft.md` and the documentation's Russian draft are not |
| III–V. Headers, AI-CORE, docstrings | Pass: applies to the new action and everything touched |
| VI. Tail | Pass: three reserved tasks, in order |
| API only through actions | Pass: `GetElementCardAction` |

Re-checked after design: no change.

## Project Structure

### Documentation

```text
specs/043-field-card-and-collapse/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── maxitor-api.md
│   └── ui.md
├── checklists/requirements.md
├── tasks.md
└── tasks.ru_draft.md
```

### Source Code

```text
packages/maxitor/front/
├── src/maxitor/front/model/diagrams/actions/
│   ├── get_element_card_action.py        # new: one element's kind, name, description, lifecycle
│   └── list_entities_action.py           # a row's lifecycle_id
├── tests/
└── client/
    ├── scripts/check-layout-determinism.ts  # collapsed pages
    └── src/
        ├── api/elementCard.ts               # new
        ├── components/history/DiffCard/     # its body is shared
        ├── components/diagrams/ElementCard/ # new: card, miniature
        ├── components/diagrams/ErdViewer/   # hover card, collapse, toolbar
        ├── components/diagrams/MapViewer/   # hover card
        ├── lib/useHoverCard.ts              # new: delay, stay, follow
        ├── lib/erdCollapse.ts               # new: which rows stay
        ├── lib/lifecycleMiniature.ts        # new: read, draw, keep
        ├── lib/buildDotSource.ts            # rows, control, hidden count
        ├── lib/erdCopy.ts                   # every name, no touch
        ├── lib/viewUrl.ts                   # two settings
        └── rooms/graphvizFocus.ts           # no label where a card stands
```

**Structure Decision**: The existing web application; new code beside what it extends.

## Phases, one commit each, each on the maintainer's word

1. The specification
2. One card for every field (#320)
3. The lifecycle miniature (#320)
4. Changes in the miniature (#320)
5. The card on the full graph (#320)
6. Collapse one table (#283)
7. Collapse all, and the layout check (#283)
8. Closing check run
9. Documentation
10. Changelog

## Complexity Tracking

None.
