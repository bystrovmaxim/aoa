# Implementation Plan: The version track shows where the graph changed

**Branch**: `feature/issue-345-version-track` | **Date**: 2026-11-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/051-version-track-graph-changes/spec.md`

## Summary

Maxitor's server starts carrying what the port says about a history's version file, and a public address gains `version_link=` and `version_key=`. The track then draws a point's size from `graph_changed`, takes numbers from the file, and offers a personal checkbox that hides the points that did not change the graph. Hiding is drawing only: it filters what the track lays out, never what is chosen.

## Technical Context

**Language/Version**: Python 3.12 and 3.14; TypeScript with React in the client

**Primary Dependencies**: the action machine, `httpx`, React, MUI. Nothing new.

**Storage**: `HistoryStore` in memory; `localStorage` for the viewer's checkbox

**Testing**: pytest with the stand-in port (`web/tests/fixtures/stand_in_port.py`); vitest for the client

**Target Platform**: Maxitor's server and browser client

**Project Type**: web application

**Performance Goals**: on 500 points, choosing and toggling respond in under one second

**Constraints**: the port does not change. A room never carries the checkbox. Names of versions (`#57`) keep their place in the whole history, hidden points included.

**Scale/Scope**: the track, its legend and card, the picker, the history's address on both sides, four server actions

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How this plan keeps it |
|---|---|
| I. The maintainer decides | Nothing is committed, pushed or opened without an instruction |
| II. English in code and history | All code, comments and commits are in English |
| III–V. Headers, AI-CORE, docstrings | Every new module has its header; public functions have blocks, methods the one line |
| VI. The tail | Three reserved tasks: check run, documentation, changelog. Each case gets a script and a notebook under `examples/` |
| API only through actions | The existing actions grow fields; no new route |

Passed before research and after design. No violations.

## Project Structure

### Documentation (this feature)

```text
specs/051-version-track-graph-changes/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/history-routes.md
└── tasks.md
```

### Source Code (repository root)

```text
packages/maxitor/web/maxitor/web/model/core/
├── history_address.py                 # version_link=, version_key=
├── history_entry.py                   # version_file, version_problem, the two parameters
├── history_reading.py                 # the description into the entry
├── resources/repo_graph_port_gateway.py
└── actions/{open_history,check_history,history_versions,check_version_access}_action.py

packages/maxitor/web/client/src/
├── api/history.ts
├── lib/{versionNames,versionRange,historyAddress}.ts
├── lib/smallPointsShown.ts            # new: the viewer's checkbox
├── app/{App.tsx,useOpenHistory.ts}
└── components/history/{VersionTrack,VersionPicker,VersionButton,VersionsBetween}/
```

**Structure Decision**: the existing server and client. One new client module, following `lib/hoverCardsOn.ts`.

## Complexity Tracking

No violations to justify.
