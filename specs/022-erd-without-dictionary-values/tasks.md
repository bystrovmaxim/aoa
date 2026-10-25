---
description: "Task list for feature 022 — the dictionary card draws no values, while the graph keeps them"
---

# Tasks: the ERD card draws no dictionary values, while the graph keeps carrying them

**Input**: Design documents from `specs/022-erd-without-dictionary-values/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/erd-card.md](./contracts/erd-card.md), [quickstart.md](./quickstart.md)

**Tests**: the repository's tests are the three Node checks and the package suites; the specification makes them the acceptance proof (US1–US3), so they are tasks here. No new test framework, no new file beyond the existing check script.

**Organization**: tasks are grouped by the user stories of the specification. US1 is the change; US2 and US3 prove that the two data layers did not lose anything; US4 is delivered by the documentation task of the tail, because the constitution reserves exactly three tasks for the tail and no other task may absorb them.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependencies)
- **[Story]**: which user story the task belongs to (US1, US2, US3)
- Every task carries at least one concrete file path

## Path Conventions

This is a library monorepo, so paths are package-relative: `packages/aoa-maxitor/client/…` for the renderer and its checks, `packages/aoa-maxitor/…` for the payload, `packages/aoa-action-machine/…` for the graph, `docs/…` and `specs/…` for prose.

## Phase order

| Phase | Story | Priority | What it delivers |
| --- | --- | --- | --- |
| 1 | — | — | the baseline the spec quotes, recorded |
| 2 | US1 | P1 | the card stops drawing values 🎯 MVP |
| 3 | US2 | P1 | the graph export still carries every value |
| 4 | US3 | P2 | the ERD payload still carries every value |
| 5 | — | — | the three tail tasks, in the constitution's order |

---

## Phase 1: Setup

- [x] T001 [P] Create `specs/022-erd-without-dictionary-values/evidence/baseline.md` and record the state the specification quotes: the three client checks green, the two Python tests green, the players-domain `viewBox` height (`1698 × 6800`), the 98 painted property rows, and the seven dictionaries with their value counts — reproducing each number with the command that produced it. Also record, as a golden, the DOT that `buildDotSource` produces for the check's non-dictionary entity (`shop.PriceTagCoreEntity` with its `amount` row) before any edit, so "a non-dictionary card is unchanged" is a comparison rather than an impression (SC-001, SC-002, SC-005)

**Checkpoint**: the numbers in the spec are traceable to a record, and the tree is green before anything is touched.

---

## Phase 2: User Story 1 — read a domain's ERD without a dictionary wall (Priority: P1) 🎯 MVP

**Goal**: a dictionary is a card of its own fields; no value row, no code tooltip, nothing in their place — and the card's drawing does not depend on how many values the dictionary declares.

**Independent Test**: render the measured model's players domain, read the drawing's `viewBox`, and run the dictionary check — the height falls to 2075 px from 6800, no value text or tooltip exists in the DOT or the SVG, and the two control checks stay green.

### Tests and checks for User Story 1

- [x] T002 [US1] In `packages/aoa-maxitor/client/scripts/check-erd-dictionary-values.ts`, invert the assertions against the rendered card: no `>Euro<`, no `symbol: €`, no escaped note, no array-property text, no `TOOLTIP="code: …"` in the DOT and no `xlink:title="code: …"` in the SVG; keep the non-dictionary row, the reference arrow, the single printed name and the legacy-graph assertions. Run it before the renderer changes and confirm it FAILS — a check that passes here proves nothing (FR-001, FR-007, FR-009)
- [x] T003 [US1] Add to `packages/aoa-maxitor/client/scripts/check-erd-dictionary-values.ts` two assertions. First, count-independence over the counts the specification names: for the same dictionary rendered with 0, 1, 3, 26 and 93 values, every DOT equals the DOT for `values: []`. Second, the golden from T001: the DOT of the non-dictionary entity (`shop.PriceTagCoreEntity`) still equals the recorded string, so an ordinary card is provably unchanged rather than merely still containing its row (FR-005, FR-008, SC-005, SC-006)

### Implementation for User Story 1

- [x] T004 [US1] In `packages/aoa-maxitor/client/src/lib/buildDotSource.ts`, delete the `valueRows` block and the `${valueRows}` interpolation from the card label; keep `ErdValue` and `ErdEntity.values` in the payload type with a comment that the payload carries them and the card does not draw them (FR-001, FR-002, FR-006)
- [x] T005 [US1] Run `cd packages/aoa-maxitor/client && npm run build`, then `node scripts/check-erd-dictionary-values.ts`, `node scripts/check-erd-card-containment.ts` and `node scripts/check-erd-group-label.ts`; all four are green, and the containment and group-label checks are unchanged files (FR-007, FR-012)
- [x] T006 [US1] Adversarial: restore one value row in `packages/aoa-maxitor/client/src/lib/buildDotSource.ts`, confirm `packages/aoa-maxitor/client/scripts/check-erd-dictionary-values.ts` fails while the two control checks still pass, then revert the edit — and record the failure text in `specs/022-erd-without-dictionary-values/evidence/baseline.md` (FR-001; spec Verification)
- [x] T007 [US1] Walk the measured model in the built client and record the results in `specs/022-erd-without-dictionary-values/evidence/baseline.md`: (a) render each of the four domains and the all-domains view and confirm zero value rows across all seven dictionaries — no label, no property text, no `is_obsolete` line; (b) read the players-domain `viewBox` and confirm the height is 2075 px — under a third of the former 6800 — and record events, offers, showcases and the all-domains view for scale; (c) screenshot one small dictionary card and the players domain as the visual record. This is the only task that exercises SC-002's "seven of seven" and SC-005's "every non-dictionary card", because the client check runs on fixtures, not on the model (SC-001, SC-002, SC-005, SC-006)

**Checkpoint**: US1 is complete and independently testable — the card is readable, the check proves it, and the height is measured.

---

## Phase 3: User Story 2 — keep every value in the graph export (Priority: P1)

**Goal**: the interchange document still publishes every declared value with its code, label and properties; the display decision did not become data loss.

**Independent Test**: run the graph test unchanged, then break the export in isolation and watch the same test fail while the card check still passes.

- [x] T008 [US2] Run `.venv/bin/pytest packages/aoa-action-machine/tests/action_machine/graph/test_dictionary_reference_json.py -q` without editing it; confirm it passes and record the run in the evidence file as the graph-side proof. Note in the evidence that the markup case of US2's third scenario (`<`, `>`, `&` carried verbatim) is asserted at the payload layer by `test_list_entities_payload_dictionary.py`'s `"<safe> & readable"` fixture and holds at the graph layer by construction — the same test's `json.dumps` round-trip is what a markup string would travel through (FR-003; SC-003)
- [x] T009 [US2] Adversarial: comment out the `properties["values"] = [member.to_reference() for member in declared]` assignment at `packages/aoa-action-machine/src/aoa/action_machine/graph/nodes/entity_graph_node.py:93`, so `to_dict` skips the key entirely (line 122 only re-carries what line 93 wrote); confirm `.venv/bin/pytest …test_dictionary_reference_json.py` fails while `node scripts/check-erd-dictionary-values.ts` still passes, then restore the file and re-run both (FR-003)

**Checkpoint**: US2 holds — the export is proven complete, and the proof fails when the values are removed.

---

## Phase 4: User Story 3 — read the same ERD data as before (Priority: P2)

**Goal**: the entity endpoint returns the same document it returned before the change, `values` included, typed and ordered; no consumer loses data to a drawing decision.

**Independent Test**: run the payload test unchanged, then break the payload in isolation and watch it fail while the card check still passes.

- [ ] T010 [US3] Run `.venv/bin/pytest packages/aoa-maxitor/tests/test_list_entities_payload_dictionary.py -q` without editing it; confirm the item shape, the text forms, the empty-property case and the schema still pass, and record the run (FR-004; SC-004)
- [ ] T011 [US3] Adversarial: replace the `entity["values"] = [...]` comprehension at `packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/list_entities_action.py:370` with `entity["values"] = []` (the line the payload test reads), confirm `.venv/bin/pytest …test_list_entities_payload_dictionary.py` fails while the card check still passes, then restore the file and re-run both (FR-004)

**Checkpoint**: US3 holds — the payload is untouched by the change and the proof is a test that was never edited.

---

## Phase 5: Polish & cross-cutting concerns

Exactly three tasks — the constitution's tail, in this order, and no other task absorbs them.

- [ ] T012 Run `bash scripts/run_checks_with_log.sh` and take it to zero, including the client build, the three Node checks, mypy, pylint, radon, vulture, packaging and every package's suite; confirm only the chunk-size advisory and the LangGraph pending-deprecation warning remain, and paste the tail into `specs/022-erd-without-dictionary-values/evidence/check-run.md` (constitution VI.1)
- [ ] T013 Write the documentation in English: amend `specs/016-value-declaration-consistency/contracts/dictionary-card.md` §3 (Placement and Printed text) and `specs/017-explicit-entity-relations/spec.md` FR-038 in place; rewrite the row promises in `docs/tutorials/step-26-maxitor.md` while keeping its ERD introduction and its payload-boundary explanation; correct the sentence in `packages/aoa-maxitor/README.md`; confirm the client README never mentioned values instead of assuming it. State explicitly that no `examples/` script/notebook pair is added, and why — the change has no runnable Python surface, and `examples/step_20_dictionaries/09_erd.py` still prints the unchanged payload (FR-010, FR-011; SC-007)
- [ ] T014 Write the changelog: one article in `docs/CHANGELOG.md` — what a reader can now do (a dictionary card that is readable at a glance, values that stay in the graph for every consumer) — and one entry under `[Unreleased] → Changed` in `packages/aoa-maxitor/CHANGELOG.md` naming the graph and payload guarantee; plain words, no per-file account (constitution VI.3)

---

## Dependencies & execution order

### Phase dependencies

- **Phase 1 (Setup)**: no dependency; it records the baseline every later number is compared against.
- **Phase 2 (US1)**: depends on Phase 1. T002 and T003 are written before T004, and both must be red before it: a check that passes against the unfixed renderer proves nothing.
- **Phase 3 (US2)** and **Phase 4 (US3)**: depend on Phase 2 only for the final re-run — their tests are unchanged files and can be run at any time, but the "still passes" claim is only meaningful after the renderer changed.
- **Phase 5 (Polish)**: after US1–US3. The three tail tasks keep their order: check run, documentation, changelog.

### Within Phase 2

T002 → T003 → T004 → T005 → T006 → T007. T002 and T003 edit the same check file, so they are sequential; T004 edits the renderer; T006 restores exactly what T004 removed.

### Parallel opportunities

- **T008 and T010** are different packages, different test files, and neither depends on the other — they can run in parallel with each other and with T002.
- **T001** stands alone.
- Nothing inside Phase 2 parallelizes: two tasks touch the check, the rest depend on the renderer edit.

### Parallel example — the two proofs that the data survived

```text
Task: T008 — the graph export still publishes properties.values (action-machine)
Task: T010 — the payload still carries values with its typed property list (maxitor)
```

---

## Implementation strategy

### MVP first

US1 alone is the whole user-visible change: T001 → T002 → T003 → T004 → T005. Validate it with T007's measurement — a domain that was 6800 px tall now fits one screen — and stop there for review before the adversarial passes.

### Incremental delivery

US2 and US3 add no code: they are the two "nothing was lost" proofs, and they can be shown in one sitting. The tail follows only once the code is what it will be: check run, then documentation, then changelog.

### What is deliberately not a task

- **Adding a badge, a count or a marker** in place of the rows — refused by the clarification of 2026-10-25.
- **Removing the value rows server-side** — the payload and the graph must keep them; a temptation that would delete the FR-003/FR-004 guarantee.
- **Touching the specialization field's tooltip** — out of scope; it belongs to the field, not the card.
- **Renaming `check-erd-dictionary-values.ts`** — churn in the check-run script and in every page that cites it, for no behavioural gain (D7).
- **A new `examples/` script and notebook** — recorded in the plan's Complexity Tracking with its reason; the tail states it rather than hides it.
- **Acting on the two accepted remarks of the check run.**
- **A commit, a push, a pull request or a merge** — phase boundaries are commit boundaries only on the maintainer's instruction (Principle I).

---

## Traceability

| Story | Tasks | Requirement |
| --- | --- | --- |
| US1 | T002–T007 | FR-001, FR-002, FR-005, FR-006, FR-007, FR-008, FR-009, FR-012 |
| US2 | T008, T009 | FR-003 |
| US3 | T010, T011 | FR-004 |
| US4 (documentation) | T013 | FR-010, FR-011 |
| — | T012, T014 | constitution VI |

| Success criterion | Task | How it is shown |
| --- | --- | --- |
| SC-001 the drawing is laid out by its entities | T001, T007 | `viewBox` before 6800, after 2075 for players and 1242–1667 for the others |
| SC-002 seven of seven dictionaries, zero rows | T007 | the four domains and the all-domains view, walked |
| SC-003 every value stays in the graph export | T008 | the graph test, unchanged |
| SC-004 every dictionary keeps `values` in the payload | T010 | the payload test, unchanged |
| SC-005 non-dictionary cards identical | T001, T003 | the golden DOT recorded before the change |
| SC-006 one, three, twenty-six and ninety-three values alike | T003 | the count-independence loop over 0/1/3/26/93 |
| SC-007 a reader attributes the change to the dictionary | T013 | the documentation and changelog article carry that reading |

## Format validation

Every task above carries a checkbox, a sequential ID, an optional `[P]`, a story label inside a story phase, and at least one concrete file path; the Phase 1 and Phase 5 tasks carry no story label; the tail is exactly three tasks and none of them was absorbed by an earlier phase.
