# Implementation Plan: Entity Kinds Travel with the Graph, and the ERD Shows Every Line It Should

**Branch**: `feature/issue-239-entity-kinds-travel-with-graph` | **Date**: 2026-10-26 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/027-erd-kinds-and-lines/spec.md`; issue #239.

## Summary

The kind of an entity becomes data the graph carries in full — its word and, new, its display name, declared on each AOA kind base and checked at class creation — and the wire stops enumerating the words. Maxitor loads any kinds a graph states (including none), lists them, and turns the ERD into a viewer that uses them: one 148 px filter panel with Domains and Kinds as a strict accordion, a kind icon before every table name, a grey Kinds disk with no grey left among domain colours. In the same work the ERD stops losing lines (relations, references and generalizations are chosen by "both ends on screen", per slice and across slices, and a specialization head is joined to the dictionary of its axis), draws one line per association with crow's-foot ends and roles, cleans the type column, gives every table a minimum width, and makes lines hoverable (thicker, raised, fields marked by text) and names copyable.

The technical approach (research R1–R16): a `KIND_LABEL` class attribute checked in `BaseEntity.__init_subclass__`; an open JSON-schema property with an optional label; tolerant DuckDB loading with a nullable label column; a new `ListEntityKindsAction`; relation SQL rewritten around `selected_entity` plus a request-wide relation list; association pairing in SQL on `inverse_field`; Graphviz `dir=both` with `crow`/`tee` and `headlabel`/`taillabel`; addressable cells through `ID` + `TOOLTIP`; one SVG post-pass for icons, hit strokes, hover and copy targets; a new `ErdFilterPanel` component; and plain-Node checks on the client's own WASM Graphviz, as `check-erd-*.ts` already do.

## Technical Context

**Language/Version**: Python ≥ 3.12 (`aoa-action-machine`, `aoa-maxitor`); TypeScript + React 18 (Maxitor client, Vite).

**Primary Dependencies**: Pydantic (entity base), `jsonschema` (graph schema tests), DuckDB (Maxitor store), FastAPI (routes), MUI (legend chrome), `@hpcc-js/wasm-graphviz` 1.21.x (ERD layout). No new dependency.

**Storage**: DuckDB in-memory per loaded graph (`entity` table gains a nullable `entity_kind_label`). Browser module-level maps for per-diagram toggles, as today.

**Testing**: pytest per package (`packages/aoa-action-machine/tests/action_machine/...`, `packages/aoa-maxitor/tests/`); vitest under jsdom for client logic (`npm test`); plain-Node ERD checks in `packages/aoa-maxitor/client/scripts/check-erd-*.ts` rendering through the real WASM Graphviz and wired into `scripts/run_checks_with_log.sh`.

**Target Platform**: Maxitor server (Linux, behind nginx on production) and evergreen browsers; mobile at 375 px width.

**Project Type**: Monorepo of Python libraries plus a FastAPI service with a React SPA.

**Performance Goals**: No new round trip per entity; the ERD of the admingameoffer graph renders as fast as today (one extra SQL for kinds, one request-wide relation query). The post-pass is linear in cards and edges.

**Constraints**: The visual baseline is production (FR-038): fonts, sizes, spacing, Graphviz look, MUI chrome stay; only named changes happen. The header stays one coloured cell so `containNodeFills.ts` keeps rounding it. Payload shapes only grow (new fields), except the FK row's `type` text losing its `FK -> ` prefix.

**Scale/Scope**: Reference graph: admingameoffer, 440 nodes, 26 entities, 46 relation edges, 4 domains (frozen as `specs/025-graph-index-memory/data/ref-graph-2026-10-26.json.gz`). Six AOA kinds; any number of producer kinds.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How this plan complies |
|---|---|
| I. The maintainer decides | Planning only: nothing is committed, pushed or opened as a PR. Each phase in `tasks.md` ends with a commit that waits for the maintainer's instruction. |
| II. English in code and git | All code, comments, docstrings, examples and commit messages in English. Russian exists only in `*.ru_draft.md` beside each document, which `.gitignore` excludes. |
| III. Module headers | New Python modules (`list_entity_kinds_action.py`, its schema) open with the path line, a `Name — purpose.` title and `PURPOSE` / `ARCHITECTURE / DATA FLOW` sections. |
| IV. AI-CORE blocks | `ListEntityKindsAction` and `entity_kind_label_of` carry blocks; the six kind bases keep theirs, with one `CONTRACT` sentence naming `KIND_LABEL`. |
| V. Short docstrings | Every new class, function and method has a one-line docstring ending with a period. |
| VI. Tail of three steps | `tasks.md` reserves exactly three final tasks, in order: the check run to zero, the documentation (every case as a script and a notebook, executed), one changelog article. |
| Final step: check run | New ERD checks are added to `scripts/run_checks_with_log.sh` like the existing `check-erd-*.ts`; the two accepted remarks stay untouched. |

**Gate result**: PASS — no violation, nothing in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/027-erd-kinds-and-lines/
├── plan.md              # This file
├── research.md          # R1–R16a: decisions and rejected alternatives
├── data-model.md        # Kind, kind base, association, line, filter state
├── quickstart.md        # Runnable validation scenarios
├── contracts/
│   ├── graph-json-entity-kind.md      # wire: entity_kind (open) + entity_kind_label
│   ├── list-entity-kinds.md           # GET /api/v1/list-entity-kinds
│   ├── list-entities-relations.md     # relation rows: association pairing, request-wide list
│   └── erd-svg-postpass.md            # ids, classes and events the ERD post-pass relies on
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks output
```

### Source Code (repository root)

```text
packages/aoa-action-machine/src/aoa/action_machine/
├── domain/entity.py                     # KIND_LABEL check in BaseEntity.__init_subclass__
├── domain/{core,assoc,detail,spec,enum,state}_entity.py   # KIND_LABEL on each kind base
├── graph/nodes/entity_graph_node.py     # entity_kind_label_of; entity_kind_label in properties
└── graph/graph_json_schema.py           # open entity_kind, optional entity_kind_label

packages/aoa-action-machine/tests/action_machine/
├── domain/test_entity_kind.py           # label declared, refused when missing/empty/inherited
└── graph/test_graph_json_schema_entity_kind.py   # open word, optional label, rejections

packages/aoa-maxitor/src/aoa/maxitor/
├── model/diagrams/resources/duckdb_graph_resource.py   # tolerant _fill_table_entity, label column, nodes view
├── model/diagrams/actions/list_entity_kinds_action.py (+ _schema.py)   # new
├── model/diagrams/actions/list_entities_action.py      # selected_entity relations, pairing, request-wide list, FK type text
├── model/diagrams/actions/list_domains_action.py       # slate → orange
└── api/app.py                                          # /list-entity-kinds route

packages/aoa-maxitor/tests/
├── test_duckdb_entity_kind_tolerance.py
├── test_list_entity_kinds_action.py
├── test_list_entities_lines_on_screen.py
├── test_list_entities_associations.py
└── test_maxitor_names_no_kind_words.py

packages/aoa-maxitor/client/
├── src/api/erd.ts                                  # listEntityKinds(); relations list
├── src/lib/buildDotSource.ts                       # min width, header slot, rows, association edges
├── src/lib/enrichErdData.ts                        # slate → orange
├── src/lib/icons/entity_kind_glyphs.ts             # pictograms + monogram
├── src/lib/erdPostPass.ts                          # icons, hit strokes, line and row hover
├── src/lib/erdCopy.ts                              # click-to-copy and its fallback
├── src/lib/erdKindFilter.ts                        # kind filter composed with the domain filter
├── src/lib/mergeErdRelations.ts                    # request-wide relations pruned to the tables on screen
├── src/components/ui/ErdFilterPanel/ (+ README.md) # accordion panel
├── src/components/diagrams/ErdViewer/parts/ErdGraphvizCanvas/ErdGraphvizCanvas.tsx
├── src/**/*.test.ts(x)                             # vitest: panel, filters, pairing glue, copy
└── scripts/check-erd-kinds-and-lines.ts            # WASM Graphviz check, wired into the check run

docs/ and examples/                                 # tail: pages from spec Context, Maxitor README, step_20 / step_26 cases (.py + .ipynb)
```

**Structure Decision**: Existing monorepo layout; no new package. Engine changes stay in `aoa-action-machine`, store and API changes in `aoa-maxitor`, drawing and interaction in its client. The client's ERD-specific DOM work goes into new modules (`erdPostPass.ts`, `erdCopy.ts`) beside the existing `containNodeFills.ts` / `sanitizeGraphvizSvgOverlays.ts`, so the canvas component only wires it.

## Phases (each phase = one commit, on the maintainer's instruction)

The phases follow issue #239 §12 one to one, so each commit ticks one box; a commit 0 carries these design documents.

| # | Phase (issue #239 §12) | Spec |
|---|---|---|
| 0 | Specification artifacts | — |
| 1 | Engine: display names on kind bases, export, open schema | US3; FR-001–FR-004 |
| 2 | Maxitor backend: tolerant load, label column, `list-entity-kinds` | US3; FR-005–FR-007 |
| 3 | Every line between tables on screen (per slice and request-wide), including the specialization head → dictionary line | US1; FR-021, FR-022 |
| 4 | Filter panel and kind filter | US2; FR-008–FR-015 |
| 5 | Kind icons, palette, specialization container, table rows, minimum width | US4, US7; FR-016–FR-020, FR-031–FR-033 |
| 6 | Lines and interactions: association pairing, crow's-foot ends and roles, line hover with field marking, click to copy; before/after comparison with production | US5, US6, US8; FR-023–FR-030, FR-034–FR-038 |
| 7 | Closing check run taken to zero | FR-039 |
| 8 | Documentation | FR-039 |
| 9 | Changelog article | FR-039 |

Phases 3 and 6 both touch `relation_sql`; 6 builds on 3. Phases 4–6 touch `ErdGraphvizCanvas.tsx` in turn and run in order. Phase 5's header slot and phase 6's copy targets share the `ID` + `TOOLTIP` cell convention fixed in [contracts/erd-svg-postpass.md](contracts/erd-svg-postpass.md).

## Complexity Tracking

No constitution violation; nothing to justify.
