# Implementation Plan: a dictionary card draws its fields, and the graph keeps its values

**Branch**: `feature/issue-265-erd-without-dictionary-values` | **Date**: 2026-10-25 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/022-erd-without-dictionary-values/spec.md`

## Summary

A closed dictionary is drawn in the entity diagram as a card whose declared values are rows. On a real model that is 93 rows for a region dictionary and a drawing 1698 × 6800 px tall for one domain — a green column that pushes every other entity out of the view. The fix is a rendering decision, not a data one: the card stops drawing value rows, while the graph export and the ERD payload keep carrying every value, its code, its label and its properties.

The change is deliberately small and has one shape:

1. **The renderer stops drawing the rows.** `buildDotSource` loses the block that turns `values` into table rows and the interpolation that appends them to the card. The payload type keeps `values` — it is the consumer contract, and the renderer is the only layer that ignores it.
2. **Nothing replaces them.** No badge, no count, no tint, no marker (clarification of 2026-10-25). The card is its header, its own fields and the arrows that reach it.
3. **The check is inverted rather than deleted.** The dictionary check keeps its fixtures — including a four-value dictionary whose payload still carries the values — and asserts the new contract: no value text and no code tooltip anywhere in the DOT or the SVG, the dictionary's own field rows intact, non-dictionary cards untouched, and a graph saved before the change still rendering. One new assertion pins the real rule: a dictionary rendered with its values and the same dictionary rendered with `values: []` produce the same DOT.
4. **The graph-side proof stays.** `test_dictionary_reference_json.py` already asserts that the graph document publishes `properties.values` with `code`, `display_name` and `properties`; it runs unchanged, and the adversarial break that removes values from the export must fail it.
5. **The documents that promised rows are reconciled.** The card contract, the tutorial chapter (keeping its ERD introduction and its payload-boundary explanation), the package README, and an amendment note on the two earlier requirements that mandated the row.

## Technical Context

**Language/Version**: TypeScript 5.7 for the renderer and the checks (Node 22+ runs the `.ts` scripts directly, as the existing checks already do); no Python changes. The Python backend, the payload action, its SQL and its schemas are untouched.

**Primary Dependencies**: none new. `@hpcc-js/wasm-graphviz` already renders the SVG inside the check, and Vite 6 already builds the client.

**Storage**: none. The graph format, the interchange schema and the ERD payload schema do not change, so a saved graph renders without a rebuild.

**Testing**: the three client check scripts (`check-erd-card-containment.ts` unchanged, `check-erd-dictionary-values.ts` inverted, `check-erd-group-label.ts` unchanged); `npm run build`; the package test suites unchanged (`test_list_entities_payload_dictionary.py` keeps proving the payload shape); the closing `bash scripts/run_checks_with_log.sh`.

**Target Platform**: the Maxitor React SPA in a browser; the checks run in Node.

**Project Type**: library monorepo with a viewer package; this is a viewer-rendering change plus documentation.

**Performance Goals**: the drawing shrinks by one table row per declared value — 93 rows for the measured region dictionary, taking the players domain from 6800 px to 2075 px, and the other three domains to 1423, 1242 and 1667 px. No new computation is introduced; the renderer does strictly less work.

**Constraints**: the payload and the graph must keep every value (FR-003, FR-004); nothing may be added in place of the rows (FR-002); no threshold, name or kind may enter the renderer (FR-006); no compatibility flag or migration (FR-012); English throughout (Principle II); nothing committed without instruction (Principle I).

**Scale/Scope**: 1 renderer function (one block and one interpolation), 1 check script (~60 lines rewritten), 1 contract page, 1 tutorial section, 1 package README paragraph, 2 earlier specification pages amended in place, 2 changelogs. No Python source file in the delivered diff; two are edited and reverted during the adversarial passes (T009, T011), which is why the constitution-check rows for Principles III–V read "no change" rather than "no file touched".

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | How this plan satisfies it |
| --- | --- | --- |
| I. The maintainer decides | No commit, push, PR or merge unless instructed in the current conversation | The branch exists on the maintainer's word. Phase 1 becomes a commit only on instruction; the tail is prepared, shown and left uncommitted. Nothing is pushed. |
| II. English in commits and code | Every message, comment, page and changelog in English | The renderer comment, the check's assertions and messages, the contract, the tutorial edit, the README and both changelogs are English. |
| III. Module headers | Path on line 1, title docstring, `═`-ruled sections | No Python module is touched, so no header is edited. The TypeScript files keep the header comment form their neighbours use (`// src/lib/...`). |
| IV. AI-CORE blocks | `ROLE`/`CONTRACT`/`INVARIANTS` on public Python types | No public Python type changes. `ListEntitiesAction` keeps its block, and its contract text is checked against the payload it still returns — the action is not modified because the payload does not lose anything. |
| V. Short docstrings | One line with a period on every class, function, method | No new Python symbol. The check's helpers keep their one-line comments; `buildDotSource` keeps its docstring form. |
| VI. The last three steps | Check run to zero, then documentation, then changelog — exactly three reserved tasks | The tail is exactly three tasks, in that order: the closing check run, the documentation, the changelog. No implementation task absorbs them. |
| VI.4–VI.6 each case shown, twice, and executed | Every case as a script under `examples/` and as a notebook, and the examples run | This change introduces no declaration, no runtime API and no refusal — it removes a drawing. Its cases are rendering outcomes, and the repository's own form for them is the client check scripts, not an `examples/` script: a Python example cannot draw an SVG. The dictionary example that exists (`examples/step_20_dictionaries/09_erd.py` + notebook) still prints the payload unchanged and keeps working, and the documentation says so. Recorded in Complexity Tracking as a deliberate, bounded exception rather than an omission. |

**Violations requiring justification**: one, above — the documentation tail adds no new `examples/` script/notebook pair because the change has no runnable Python surface. It is justified by the rule's purpose (a reader must see what actually happens) being served by the executed client check plus the reproduced drawing, and it is bounded to this feature.

**Re-checked after Phase 1 design**: unchanged. The design removes more than it adds: one block and one interpolation leave the renderer, the payload keeps its shape, and the check gains one assertion while losing the ones that pinned the old contract.

## Project Structure

### Documentation (this feature)

```text
specs/022-erd-without-dictionary-values/
├── plan.md              # this file
├── spec.md              # the specification
├── research.md          # Phase 0: D1–D6, the two measurements, the rejected alternatives
├── data-model.md        # Phase 1: the payload's value, the card, the renderer's input
├── quickstart.md        # Phase 1: runnable proofs
├── contracts/
│   └── erd-card.md      # graph → payload → card, and what each layer must keep
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
packages/aoa-maxitor/
├── client/
│   ├── src/lib/buildDotSource.ts                    # the value-row block and its interpolation REMOVED
│   ├── scripts/check-erd-dictionary-values.ts        # inverted: no value rows, payload-driven invariant
│   ├── scripts/check-erd-card-containment.ts         # unchanged, runs as the control
│   └── scripts/check-erd-group-label.ts              # unchanged, runs as the control
├── tests/test_list_entities_payload_dictionary.py    # unchanged: the payload still carries the values
├── src/aoa/maxitor/model/diagrams/actions/list_entities_action.py  # unchanged
├── README.md                                         # the sentence that promises rows
└── CHANGELOG.md                                      # the article (tail)

packages/aoa-action-machine/
└── tests/action_machine/graph/test_dictionary_reference_json.py   # unchanged: the graph keeps the values

docs/
├── tutorials/step-26-maxitor.md                      # the chapter loses its row promise, keeps ERD + payload
└── CHANGELOG.md                                      # the article (tail)

specs/
├── 016-value-declaration-consistency/contracts/dictionary-card.md   # §3 amended in place
└── 017-explicit-entity-relations/spec.md                            # FR-038 amended in place
```

**Structure Decision**: one package owns the change (`packages/aoa-maxitor`, client only), one package owns the graph-side proof (`aoa-action-machine`, unchanged test), and the documentation spans the package README, the tutorial and the two specifications that stated the old contract. No new module, no new package and no new dependency.

## Phases

Each phase is a commit only when the maintainer says so (Principle I); the numbers are the order of the work, not a claim to ship.

### Phase 1 — the card stops drawing value rows

- `client/src/lib/buildDotSource.ts`: delete the `valueRows` block and the `${valueRows}` interpolation; keep `ErdValue` and `ErdEntity.values` in the type with a comment that the payload carries them and the card does not draw them.
- `client/scripts/check-erd-dictionary-values.ts`: invert the assertions — no `>Euro<` or property text in the DOT, no `xlink:title="code: …"` in the SVG; the dictionary's own fields and the non-dictionary card unchanged; the reference arrow and its single printed name preserved; the legacy graph still rendered. Add two invariants: the DOT is identical for 0, 1, 3, 26 and 93 declared values, and the non-dictionary card's DOT still equals the golden recorded before the change.
- `npm run build` and the three check scripts are green in the same phase; a red check is not a later task.

**Proves**: FR-001, FR-002, FR-005, FR-006, FR-007, FR-008, FR-009, FR-012.

### Tail task 1 — the closing check run

`bash scripts/run_checks_with_log.sh` from the repository root, taken to zero. The two accepted remarks — the Vite chunk-size advisory and the LangGraph pending-deprecation warning — stay and are not acted on. Any edit the run makes (ruff `--fix`) is reviewed as part of the change.

### Tail task 2 — the documentation

- `specs/016-value-declaration-consistency/contracts/dictionary-card.md` §3: the Placement and Printed-text rows now state that no row is drawn, and that the graph and the payload keep the values.
- `specs/017-explicit-entity-relations/spec.md` FR-038: amended in place with a dated note that the value row retires, while FR-037 stands.
- `docs/tutorials/step-26-maxitor.md`: the chapter loses the sentences that promise value rows and a code tooltip; it keeps its introduction to the ERD and its explanation of how a value's properties reach the payload. The printed example output stays as it is, because the payload did not change.
- `packages/aoa-maxitor/README.md`: the sentence "The ERD card draws those values as rows under the fields" becomes a statement of what the card shows and where the values live.
- The client README gains nothing — it never mentioned the values; checked, not assumed.

### Tail task 3 — the changelog

One article in `docs/CHANGELOG.md` about what the work created: a dictionary card that is readable at a glance, and values that are still in the graph for every consumer. One entry in `packages/aoa-maxitor/CHANGELOG.md` under `[Unreleased] → Changed`, in the compact form that file uses, naming the graph and payload guarantee so a consumer is not surprised.

## Requirement coverage

| Requirement | Where it is satisfied | Proof |
| --- | --- | --- |
| FR-001 no value row | Phase 1, renderer | inverted DOT/SVG assertions |
| FR-002 nothing in their place | Phase 1, renderer | the equality assertion (no row, no substitute) |
| FR-003 graph keeps every value | untouched | `test_dictionary_reference_json.py` |
| FR-004 payload keeps every value | untouched | `test_list_entities_payload_dictionary.py` |
| FR-005 independent of the count | Phase 1, renderer | `with values` ≡ `values: []` |
| FR-006 no vocabulary, no threshold | Phase 1, renderer | review of the diff; the check names no field |
| FR-007 non-dictionary cards unchanged | Phase 1 | `>amount<` and the reference assertions |
| FR-008 a dictionary with no values renders | Phase 1 | the `values: []` half of the equality assertion |
| FR-009 the code tooltip retires | Phase 1 | no `TOOLTIP`/`xlink:title` in DOT or SVG |
| FR-010 the contract superseded in place | tail task 2 | contract §3 and FR-038 amendment |
| FR-011 the documents reconciled | tail task 2 | tutorial, README, contract |
| FR-012 no rebuild, no flag | Phase 1 | the legacy-graph assertion; no schema edit |

## Complexity Tracking

| Exception | Why needed | Simpler alternative rejected because |
| --- | --- | --- |
| No new `examples/` script + notebook pair for the documentation tail (Principle VI.4–VI.6) | The change has no runnable Python surface: it removes a drawing, and the cases are rendering outcomes. An `examples/` script cannot render an SVG. | A Python example that prints a payload would prove nothing about the card, and a new notebook would restate `09_erd.py`, which already prints the unchanged payload. The executed client check plus the reproduced drawing is the honest proof, and it runs in the closing check run. |

No other violations. The change adds no dependency, no module, no flag and no migration.
