# Implementation Plan: Maxitor: Two Versions Side by Side, and Comparison in Rooms

**Branch**: `feature/issue-294-side-by-side` | **Date**: 2026-11-01 | **Spec**: [spec.md](spec.md)

## Summary

A page learns to hold two diagrams. A **half** is a React context that says which version a viewer draws and which of its settings, surface and reads are its own. One and Diff run with no half, exactly as today. Side by side renders each viewer twice under a half. Selection is a shared page setting; the view joins A and B on the room; pointers, positions and the room's check learn which half they belong to.

## Technical Context

**Language/Version**: TypeScript 5 + React (client), Python 3.12 (server)
**Primary Dependencies**: existing Graphviz wasm, canvas `MapEngine`, MUI; no new dependency
**Storage**: none new; the room's memory, the address
**Testing**: Vitest, pytest, `scripts/run_checks_with_log.sh`, a new real-mouse script beside `cardMechanics.ts`
**Target Platform**: desktop browsers of the check run's three engines; phone width by the existing `sm` breakpoint
**Project Type**: web application, `packages/maxitor/front`
**Performance Goals**: SC-005, Side by side opens within twice Diff's time
**Constraints**: `MAX_MESSAGE_BYTES` 4096; every endpoint through actions; One and Diff unchanged (FR-040)
**Scale/Scope**: four diagrams; stand `erd-full`

## Constitution Check

| Principle | Status |
|-----------|--------|
| I. Maintainer decides | Pass: commits, push and PR only on instruction |
| II. English | Pass: spec, code and commits in English; only `tasks.ru_draft.md` is Russian, ignored by git |
| III–V. Headers, AI-CORE, docstrings | Pass: applied to every Python module touched |
| VI. The tail | Pass: check run, documentation, changelog are three reserved tasks |

No violations. Re-checked after design: unchanged.

## Project Structure

```text
packages/maxitor/front/
├── client/src/
│   ├── lib/half.ts                     # new: HalfContext, useHalf, side projection
│   ├── lib/selection.ts                # new: shared selection, locator
│   ├── lib/pageSettings.ts             # half-own names
│   ├── lib/viewUrl.ts, urlState.ts     # mode=split, layout of each half
│   ├── lib/diffCounts.ts, changeStepping.ts  # pair-level owner
│   ├── api/client.ts + readers         # explicit read of a half
│   ├── app/App.tsx, useOpenHistory.ts  # the view
│   ├── components/diagrams/SideBySide/ # new: halves, half head, notes, A / B switch
│   ├── components/diagrams/*Viewer     # read through the half
│   ├── components/diagrams/MapViewer/mapEngine.ts  # kept view per side
│   ├── components/history/VersionPicker/  # Side by side switched on
│   └── rooms/                          # surfaces per half, protocol, page check
├── client/scripts/splitMechanics.ts    # new: real mouse, in the check run
└── src/maxitor/front/model/
    ├── rooms/                          # Room.view, half in relays, setting names
    └── diagrams/                       # sha of each graph in the comparison answer
```

## Phases (one phase, one commit)

1. The specification.
2. The half: context, reads, settings, surfaces per half, with no visible change.
3. Two halves on the ERD.
4. Locator, shared hover and selection on the ERD.
5. Use case and lifecycle.
6. Full graph.
7. Phone.
8. Rooms.
9. Closing check run. 10. Documentation. 11. Changelog.

## Acceptance

On the local stand `erd-full`, as `quickstart.md` says.
