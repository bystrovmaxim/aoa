# Implementation Plan: Maxitor Rooms Polish — One Picture, Faithful Following, the Finer Look

**Branch**: `feature/issue-282-maxitor-rooms-polish` | **Date**: 2026-10-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/029-maxitor-rooms-polish/spec.md` (issue #282)

## Summary

Fifteen remarks from using Maxitor rooms on the live stand. A room becomes one picture: the opener's settings seed the room and nobody's own values show inside it. Following mirrors the followed person's hover, tooltip, selection and panels (relayed to followers only, never logged), glides by interpolation, and works in Firefox. Pointers stay while their person is in the room. The room controls take Maxitor's sizes and their circles never touch. The ERD card is drawn by the post-pass to the mockup's geometry, its icon sits on the name's axis, field types read as clean names, line ends show true cardinality (with a new `optional` flag on relations) and reference lines point the right way, hover lights every joined table, role labels appear on hover, and the *Kinds* filter lists only the diagram's kinds. Maxitor serves its own `graph-json` through an action, with the adapter's `ETag`; the demo moves to the adapter that sends one. Every phase is accepted by the maintainer on a local stand before its commit (research R17).

## Technical Context

**Language/Version**: Python 3.12 (packages), TypeScript 5 / React 18 (Maxitor client)

**Primary Dependencies**: AOA ActionMachine, `aoa-fastapi-adapter` (WebSocket routes, `ConditionalGetMiddleware`), FastAPI/Starlette, MUI, Graphviz (wasm) for ERD and use-case layouts, AntV G6 for the full graph, Playwright (cross-engine check)

**Storage**: in-process only — `RoomRegistry`, `GraphStore`, DuckDB per held graph; nothing persistent

**Testing**: pytest (packages), vitest (client), Playwright scripts under `client/scripts/` run by `scripts/run_checks_with_log.sh`

**Target Platform**: Linux containers behind nginx (stand and `maxitor.aoa.run`); Chrome, Safari, Firefox; phones

**Project Type**: monorepo of Python packages plus a web client

**Performance Goals**: follower updates within 0.5 s and smooth on every frame (SC-002, SC-003); at most 50 relayed messages/s per connection

**Constraints**: 4 KB per room message; rooms route limit 80 messages/s; hover/pointer/viewport never logged; identical layouts across engines (spec 028) must survive the ERD card change

**Scale/Scope**: up to 20 people per room, 100 rooms per process (spec 028); 39 distinct field types in the demo model

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How this plan meets it |
|---|---|
| I. Maintainer decides | No commit, push, PR, merge, tag or deploy without an instruction in the conversation. Each phase ends with acceptance on the local stand; its commit waits for the instruction. Releases (`aoa-action-machine`, `aoa-maxitor`, `aoa-demo`) and redeploying `maxitor.aoa.run` / `demo.aoa.run` are separate steps on command. |
| II. English | Code, docstrings, commits, the issue, specs in English; Russian only in chat and in `tasks.ru_draft.md` (not committed). |
| III. Module headers | Every new module (`seed_page_settings_action.py`, `get_own_graph_json_action.py`, `own_model_graph_resource.py`, the field-type label module) opens with the path line, title and `PURPOSE` / `ARCHITECTURE / DATA FLOW`. |
| IV. AI-CORE blocks | New public classes carry ROLE/CONTRACT(/INVARIANTS). The known violation on `EntityFieldGraphNode.pretty_annotation` is fixed as that file is touched (the block moves to the new module-level function). |
| V. Short docstrings | Every new class, function and method gets its one line. |
| VI. Tail | Three reserved tasks at the end, in order: the check run to zero, the documentation (every case as a script and a notebook, executed), the changelog as one article. |
| Final check run | `bash scripts/run_checks_with_log.sh` taken to zero, with the new follow case and ERD measurements inside it. |
| Project rule: API only through actions | Maxitor's `graph-json` is an action over a resource; seeding is an action; `focus` is relayed like `pointer` (spec 028's documented exception for high-frequency, unlogged traffic). |

Result: **pass**, no violations to justify.

## Project Structure

### Documentation (this feature)

```text
specs/029-maxitor-rooms-polish/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── room-protocol.md
│   └── graph-interchange.md
├── checklists/requirements.md
└── tasks.md              # /speckit-tasks
```

### Source Code (repository root)

```text
packages/aoa-action-machine/src/aoa/action_machine/
├── graph/nodes/entity_field_graph_node.py      # field_type clean label + field_annotation
├── graph/field_type_label.py                   # NEW: the FR-030 rule (pure function)
├── graph/edges/entity_graph_edge.py            # relation edge: optional
└── intents/entity/                             # where a relation's optionality is read

packages/aoa-fastapi-adapter/                   # unchanged (route limit is a route argument)

packages/aoa-maxitor/src/aoa/maxitor/
├── api/app.py                                  # /examples/model/graph-json, rooms limit 80
├── model/core/actions/get_own_graph_json_action.py      # NEW
├── model/core/resources/own_model_graph_resource.py     # NEW
├── model/rooms/actions/seed_page_settings_action.py     # NEW
├── model/rooms/resources/room_registry.py      # focus relay to followers, pointers without window
├── model/diagrams/actions/list_entities_action.py       # four end values, reference direction, annotation
└── model/diagrams/resources/duckdb_graph_resource.py    # field_annotation, relation optional

packages/aoa-maxitor/client/
├── src/lib/pageSettings.ts                     # room value or default; seeding
├── src/rooms/                                  # follow playback, focus surface, pointers, circles, bar
├── src/lib/buildDotSource.ts, erdPostPass.ts   # card, icon axis, line ends, hover
├── src/lib/fieldTypeLabel.ts                   # NEW: cleanFieldType for older services
├── src/components/diagrams/…                   # focus surfaces per viewer, role labels, kinds list
└── scripts/check-layout-determinism.ts, check-erd-table-style.ts   # follow case; card/axis/ends

packages/aoa-demo/pyproject.toml                # aoa-fastapi-adapter>=1.3.0, version bump
```

**Structure Decision**: existing monorepo layout; changes stay inside the packages named above, new code next to its neighbours (actions under `model/*/actions`, resources under `model/*/resources`, client code under `src/rooms` and `src/lib`).

## Phases and commits

One phase = one commit; each ends with acceptance on the local stand (quickstart.md). Commit 1 holds the design documents, so phase *n* below is commit *n + 1* in tasks.md.

1. Room picture on open (US1; R1)
2. Pointers stay (FR-020…022; R5)
3. Follow mirrors focus (US2; R2)
4. Smooth follow (FR-014, FR-016; R3)
5. Following in Firefox and the follow case (FR-015; R4)
6. Room controls in Maxitor's style, clean switch (US5; R6, R7)
7. ERD card as in the mockup (FR-032; R8)
8. Kind icon on the name's axis (FR-033; R9)
9. Clean field types (FR-030, FR-031; R10)
10. ERD line ends and direction (FR-043; R11)
11. ERD hover lights joined tables (FR-040, FR-041; R12)
12. Role labels on hover (FR-042; R13)
13. *Kinds* lists the diagram's kinds (FR-044; R14)
14. Maxitor serves its own `graph-json` (FR-060, FR-061; R15)
15. The demo on the fresh adapter (FR-062; R16) — dependency and version only
16. The check run to zero
17. Documentation
18. Changelog

Publishing packages to PyPI and updating the servers are not part of this work (maintainer, 2026-10-27).

## Complexity Tracking

No constitution violations.
