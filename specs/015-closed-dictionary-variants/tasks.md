# Tasks: A closed dictionary declares its variants, and specialization takes its codes from it

**Input**: Design documents from `specs/015-closed-dictionary-variants/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

**Tests**: included, because every requirement is a refusal or a count that a test must assert (constitution III–VI and the repository's practice).

**Organization**: tasks are grouped by user story, so each story is independently implementable, testable and demonstrable. US1 is the MVP.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: the user story the task belongs to (US1–US4)
- Every task names the exact file it touches

## Path Conventions

Repository root is `packages/` + `examples/` + `docs/`; the framework package is `packages/aoa-action-machine`, the demo is `packages/aoa-demo`, the viewer is `packages/aoa-maxitor`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: the baseline that every later phase is compared with.

- [x] T001 Confirm the branch `feature/issue-241-closed-dictionary-variants` is based on `70980156`, the tree is clean, and `uv sync` succeeds; record the commit and tool versions in `specs/015-closed-dictionary-variants/evidence/baseline.before.json`
- [x] T002 Write the scan script in `specs/015-closed-dictionary-variants/evidence/scan_dictionary_variants.py` — counts of decorated dictionaries, values, duplicate codes, `currency_iso: str`, other `*_iso` fields, `Classifier(…, Literal[…])` per area, axes per area, classifier fields per axis
- [x] T003 Run the scan and store the demo facts — `enum` nodes (expected 0), the 25 currency fields, the axes, their classifier fields and their codes — in `specs/015-closed-dictionary-variants/evidence/baseline.before.json`
- [x] T004 Write `specs/015-closed-dictionary-variants/evidence/compare_baselines.py`, reporting identity or a named difference between two graph dumps
- [x] T005 Re-measure the numbers quoted in `specs/015-closed-dictionary-variants/spec.md` and correct that file if anything moved since `70980156`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the one declaration mechanism both kinds use. Nothing in US1 or US2 can start before it exists, and the state kind must come out of it unchanged.

**⚠️ CRITICAL**: no story work begins until this phase is green.

- [x] T006 Create `packages/aoa-action-machine/src/aoa/action_machine/domain/declared_values.py` with the full principle-III header: the `_DeclaredValues` mixin (no `BaseEntity` in its bases), `DeclaredValuesMeta(ModelMetaclass)`, the namespace that answers the class's own name, `ValueSpec`, and `value(**kwargs)`
- [x] T007 Move the conversion hook, the catalogue (`members`, `codes()`, `by_code()`, `entity_type`) and the duplicate refusal into the mixin, add the two configuration flags the kinds need — own-class catalogue and empty-catalogue refusal for the dictionary, inherited catalogue and no refusal for a state type — and make `packages/aoa-action-machine/src/aoa/action_machine/domain/state_entity.py` inherit it; delete `packages/aoa-action-machine/src/aoa/action_machine/domain/state_spec.py`
- [x] T008 [P] Add `packages/aoa-action-machine/tests/action_machine/domain/test_declared_values.py` — the mixin is not a kind base (`BaseEntity.__bases__` check and `_is_kind_base`), the placeholder is excluded from model fields, unknown names still raise `NameError`
- [x] T009 Run the `014` state suite unchanged (`pytest packages/aoa-action-machine/tests -q`) and prove no assertion had to move
- [x] T010 Keep the package surface coherent in `packages/aoa-action-machine/src/aoa/action_machine/domain/__init__.py` (`StateSpec`/`state` are not exported; nothing new leaks)

**Checkpoint**: the mechanism is shared and the state kind behaves exactly as before.

---

## Phase 3: User Story 1 — Declare a closed dictionary with its values (Priority: P1) 🎯 MVP

**Goal**: `BaseEnumEntity` becomes a closed dictionary: `code` and `display_name` from the kind, values declared in the body, a catalogue, duplicate and empty refusals, no inheritance of values.

**Independent Test**: declare a three-value dictionary and check `codes()`, `by_code()`, `members`, `entity_type`; then declare a duplicate, an empty decorated dictionary and a subclass with its own values and check each outcome.

### Tests for User Story 1

- [x] T011 [P] [US1] Add `packages/aoa-action-machine/tests/action_machine/domain/test_dictionary_scope.py` — non-inheritance, the empty decorated dictionary, duplicate codes, blank `code`/`display_name`
- [x] T012 [P] [US1] Extend `packages/aoa-action-machine/tests/action_machine/domain/test_entity_kind.py` — the dictionary kind's word, suffix and declaration surface, and that its structural rules still hold: the marker is abstract and unconstructible, the class keeps the kind's suffix, and it stays in the entity graph (FR-013)

### Implementation for User Story 1

- [x] T013 [US1] Add `code`/`display_name` with the non-blank validator to `packages/aoa-action-machine/src/aoa/action_machine/domain/enum_entity.py`
- [x] T014 [US1] Wire the declaration factory and the catalogue for the dictionary kind in `packages/aoa-action-machine/src/aoa/action_machine/domain/enum_entity.py` (`metaclass=DeclaredValuesMeta`, `ignored_types=(ValueSpec,)`, own-class catalogue)
- [x] T015 [US1] Refuse a decorated dictionary with no values and a duplicate code in `packages/aoa-action-machine/src/aoa/action_machine/domain/enum_entity.py`, with the messages of `specs/015-closed-dictionary-variants/contracts/dictionary-declaration.md` §4
- [x] T016 [US1] Publish the dictionary's values on its node in `packages/aoa-action-machine/src/aoa/action_machine/graph/nodes/entity_graph_node.py` (`properties.values`)
- [x] T017 [US1] Require `values` when `entity_kind` is `enum` with an `if/then` branch in `packages/aoa-action-machine/src/aoa/action_machine/graph/graph_json_schema.py`
- [x] T018 [P] [US1] Add `packages/aoa-action-machine/tests/action_machine/graph/test_graph_json_schema_values.py` — an `enum` node with values validates and one without fails; a value produces no node of its own and no domain edge (FR-015)
- [x] T019 [US1] Rewrite `examples/step_20_entity/07_enumeration.py` and `examples/step_20_entity/07_enumeration.ipynb` as a closed dictionary with three values, printing the catalogue
- [x] T020 [US1] Rewrite the marker's docstring and `AI-CORE` block in `packages/aoa-action-machine/src/aoa/action_machine/domain/enum_entity.py` for the closed-dictionary contract, and run `pytest packages/aoa-action-machine/tests -q`

**Checkpoint**: a dictionary declares its values and refuses the two declaration mistakes; the graph carries them.

---

## Phase 4: User Story 2 — Reference a value from a field (Priority: P1)

**Goal**: a field typed by the dictionary accepts a declared instance or its reference object, refuses a bare code, an undeclared code and a copy, serializes the value whole, and reads by the code; the graph marks the field as a reference.

**Independent Test**: build one entity with a dictionary-typed field, assign the input shapes of `contracts/dictionary-declaration.md` §2, then serialize and re-read a payload with a stale label.

### Tests for User Story 2

- [x] T021 [P] [US2] Add `packages/aoa-action-machine/tests/action_machine/domain/test_dictionary_core_schema.py` — declared value, reference object, bare code refused, unknown code, constructed copy, absent on an optional field, serialization, code-authoritative read
- [x] T022 [P] [US2] Add the reference assertions to `packages/aoa-action-machine/tests/action_machine/graph/test_entity_field_graph.py` — `reference_qualname` set for a dictionary-typed field, absent for `str`

### Implementation for User Story 2

- [x] T023 [US2] Implement `__get_pydantic_core_schema__`, `__get_pydantic_json_schema__` and `to_reference()` on `packages/aoa-action-machine/src/aoa/action_machine/domain/enum_entity.py`, accepting a declared instance or its reference object, resolving by `code`, refusing a bare code and a copy by identity
- [x] T024 [US2] Refuse a field typed by an intermediate dictionary with no values in `packages/aoa-action-machine/src/aoa/action_machine/graph/edges/entity_field_graph_edge.py`
- [x] T025 [US2] Set `reference_qualname` for a dictionary-typed field in `packages/aoa-action-machine/src/aoa/action_machine/graph/edges/entity_field_graph_edge.py` and declare the property in `packages/aoa-action-machine/src/aoa/action_machine/graph/graph_json_schema.py`
- [x] T026 [US2] Add one referencing field to `examples/step_20_entity/07_enumeration.py` and its notebook, showing the accepted reference object, the refused bare code and the serialized value
- [x] T027 [US2] Run `pytest packages/aoa-action-machine/tests -q` and `mypy packages/aoa-action-machine/src`

**Checkpoint**: a dictionary is a usable type; the graph can draw a reference.

---

## Phase 5: User Story 3 — Move a specialization axis onto a dictionary (Priority: P1)

> **Delivered in two commits.** T028–T032 (the container, the marker and
> `declared_variant`) are in the tree with a one-argument bridge that keeps every
> existing axis on `variant: str`. T030 and T033–T038 are **not done**: until they
> land, an axis written in the declared form is not refused — the validator
> gathers axes only where the head carries a `Classifier` marker, so such an axis
> has no coverage check, no specialization edges and no generalization edges, and
> its container is drawn as a scalar column. Do not declare the new form before
> T033.

**Goal**: the head's specialization field names the dictionary as its second type argument and carries no classifier field; each extension names its field and the declared value it is; the container refuses a bare code and a value that disagrees with the hydrated row; the build refuses a `Literal`, a copy, a foreign value, a field that does not point back and an uncovered value; the edge publishes the dictionary.

**Independent Test**: one complete axis builds; the five broken ones raise their named errors; a container with a mismatched pair is refused; the same dictionary on two axes builds when both cover it.

### Tests for User Story 3

- [x] T028 [P] [US3] Add `packages/aoa-action-machine/tests/action_machine/domain/test_specialization_container.py` — a declared value and a reference object accepted, a bare code refused, a foreign value refused, a copy refused, `None` for an absent variant, serialization, and the pairing check naming both values
- [x] T029 [P] [US3] Add `packages/aoa-action-machine/tests/action_machine/domain/test_spec_entity.py` — `declared_variant` derived on an extension, and the refusal when the marker does not name a declared value
- [x] T030 [P] [US3] Add `packages/aoa-action-machine/tests/action_machine/graph/test_entity_specialization_vocabulary.py` — the five build refusals, the shared dictionary, the edge carrying `field_name`, `classifier_value`, `dictionary_qualname`, `dictionary_label` and no `classifier_field`, and that a `Literal` outside specialization still works (FR-025)

### Implementation for User Story 3

- [x] T031 [US3] Make the container generic and typed in `packages/aoa-action-machine/src/aoa/action_machine/domain/specialization_containers.py`: `Specialization[T, D]` with `variant: D` and the pairing validator
- [x] T032 [US3] Change the extension marker to `Classifier(field=…, variant=…)` and derive `declared_variant` on `packages/aoa-action-machine/src/aoa/action_machine/domain/spec_entity.py`
- [x] T033 [US3] Read the dictionary from the head field's second type argument in `packages/aoa-action-machine/src/aoa/action_machine/intents/entity/entity_specialization_intent_resolver.py`, and rewrite the rules in `packages/aoa-action-machine/src/aoa/action_machine/graph/validators/entity_specialization_validator.py`: `_validate_axis_vocabulary` first, the classifier-field rules deleted
- [x] T034 [US3] Drop `classifier_field` from `packages/aoa-action-machine/src/aoa/action_machine/graph/edges/entity_specialization_graph_edge.py` and from `packages/aoa-action-machine/src/aoa/action_machine/graph/graph_json_schema.py`, keeping `field_name`, `classifier_value` and the dictionary properties
- [x] T035 [US3] Rewrite the codemod in `specs/015-closed-dictionary-variants/evidence/migrate_axes_to_dictionaries.py` — generate one `<Head>KindEnumEntity` per axis from its `Literal`s, delete the head's classifier field, add the dictionary argument, drop the head's `Classifier`, rewrite the extension markers and every construction or payload that set the deleted field, editing `.py` files and `.ipynb` code cells only
- [x] T036 [US3] Run the codemod on `examples/step_20_entity/06_specialization.py` with its notebook and on the 37 scripts with their 37 notebooks in `examples/step_21_relations/` — 38 scripts and 38 notebooks in all — then review each diff
- [x] T037 [US3] Run the codemod on the 7 framework test modules under `packages/aoa-action-machine/tests/action_machine/graph/` (105 `Classifier` declarations, including `test_entity_specialization_sweep.py`), keeping the existing rules' tests unchanged: alternatives are declared entities, one class in one head, no cycles (FR-026)
- [x] T038 [US3] Remove the one-argument bridge from `Specialization.__class_getitem__` and the interim `, str` it forced in `packages/aoa-demo/src/aoa/demo/model/generalization_shapes/entities/generalization_entities.py`, so a container must name its dictionary; then rewrite by hand the examples that assert the replaced rules — `examples/step_21_relations/41_error_codes_not_literal.py` and any other negative case the codemod cannot express — keeping their scenario and their printed message; then run every migrated example script, the whole `aoa-action-machine` suite and the scan, which must report 0 `Classifier(…, Literal[…])` and 0 classifier fields on axes in `packages/` and `examples/`

**Checkpoint**: the whole corpus is on the container form and the refusals have tests.

---

## Phase 6: User Story 4 — Adapt the demo, the examples and Maxitor (Priority: P2)

**Goal**: the demo's currency references become dictionary references, the graph carries the dictionary, its values, the references and the axis label, and Maxitor draws them from the graph alone.

**Independent Test**: load the migrated demo in Maxitor, toggle the `enum` kind, and check the card with its rows, the reference from a field, and the axis label; the scan reports zeros.

### Tests for User Story 4

- [x] T039 [P] [US4] Add the demo graph assertions in `packages/aoa-demo/tests/` — the `enum` node with three values, 25 `reference_qualname` fields, the axis edge with the dictionary and without `classifier_field`
- [x] T040 [P] [US4] Add the payload test in `packages/aoa-maxitor/tests/` for `values` and `reference_qualname` reaching the ERD slice

### Implementation for User Story 4

- [x] T041 [US4] Create `packages/aoa-demo/src/aoa/demo/model/dictionaries/__init__.py`, `dictionaries_domain.py` and `entities/currency_enum.py` with `USD`, `EUR`, `RUB`
- [x] T042 [US4] Retype the 25 currency fields in the 22 demo files `packages/aoa-demo/src/aoa/demo/model/**/entities/*.py` (`currency_iso`, `settlement_currency_iso`, `quote_currency_iso`) to `CurrencyEnumEntity`
- [x] T043 [US4] Point the default at the declared value in `packages/aoa-demo/src/aoa/demo/model/store/entities/sales_core.py`
- [x] T044 [US4] Move the demo's axis onto the dictionary in `packages/aoa-demo/src/aoa/demo/model/generalization_shapes/entities/generalization_entities.py`, dropping the interim `, str` second argument
- [x] T045 [US4] Add `values_json` to the `entity` table and `reference_qualname` to the `entity_field` table, and fill them, in `packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/resources/duckdb_graph_resource.py`
- [x] T046 [US4] Select the two new values into the ERD payload in `packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/list_entities_action.py` and its schema
- [x] T047 [US4] Add `values` and `reference_qualname` to `packages/aoa-maxitor/client/src/lib/buildDotSource.ts`, render the value rows in the ERD card, draw the reference and label the axis container in `packages/aoa-maxitor/client/src/components/diagrams/ErdViewer/parts/ErdGraphvizCanvas/ErdGraphvizCanvas.tsx`, and write the component README
- [x] T048 [US4] Run the scan and `compare_baselines.py`, record `specs/015-closed-dictionary-variants/evidence/baseline.after.json`, and confirm only the intended differences
- [x] T049 [US4] Run `npm run build` in `packages/aoa-maxitor/client` and `pytest packages/aoa-maxitor/tests -q`
- [x] T050 [US4] Search `packages/aoa-maxitor` for any dictionary, kind or value name of AOA's and remove it from the rendering path

**Checkpoint**: the feature is visible end-to-end and nothing in the viewer knows AOA's vocabulary.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: the adversarial sweep before the tail.

- [x] T051 [P] Break each rule of `contracts/dictionary-declaration.md` §4 and `contracts/specialization-codes.md` §5 in turn — the empty dictionary, the duplicate, the bare code, the copy, the `Literal`, the head-side `Classifier`, the uncovered value, the foreign value, the mismatched pair — confirm the dedicated test fails and no other, then restore each break and record the results in `specs/015-closed-dictionary-variants/evidence/breaks.md`
- [x] T052 [P] Run `python specs/015-closed-dictionary-variants/evidence/scan_dictionary_variants.py` and confirm every count of the spec's Success Criteria is at zero, appending the output to `specs/015-closed-dictionary-variants/evidence/scan.after.txt`

---

## Phase 8: The tail (constitution VI — exactly three tasks, in this order)

**Purpose**: the closing steps. No other task may absorb them.

- [x] T053 Run `bash scripts/run_checks_with_log.sh` and fix every remark it reports, to zero; only the two named remarks stay — record the run in `specs/015-closed-dictionary-variants/evidence/check-run.txt`
- [x] T054 Write the documentation in `docs/tutorials/step-20-entity.md`, `docs/tutorials/step-26-maxitor.md`, `docs/reference/glossary.md`, `docs/reference/intents-and-invariants.md`, `docs/how-to/specialization-declaration-fails.md` and `packages/aoa-maxitor/README.md` — every case and every refusal, each shown twice as a script and a notebook under `examples/`, with every touched example and notebook executed; write `<page>.ru_draft.md` beside each page
- [x] T055 Write the changelog as one article in `docs/CHANGELOG.md` with an `[Unreleased]` entry for `packages/aoa-action-machine/CHANGELOG.md`, `packages/aoa-demo/CHANGELOG.md` and `packages/aoa-maxitor/CHANGELOG.md` — what this work created, in plain words, without technical detail

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies; can start immediately
- **Foundational (Phase 2)**: depends on Setup; blocks US1 and US2
- **US1 (Phase 3)**: depends on Foundational
- **US2 (Phase 4)**: depends on US1 (the dictionary type must exist)
- **US3 (Phase 5)**: depends on US1 and US2 (the container's `variant` is a dictionary-typed field)
- **US4 (Phase 6)**: depends on US1, US2 and US3
- **Polish (Phase 7)**: depends on all four stories
- **Tail (Phase 8)**: depends on Polish; the three tasks are strictly ordered

### User Story Dependencies

- **US1 (P1)** — no story dependency; the MVP.
- **US2 (P1)** — needs US1's catalogue and refusals.
- **US3 (P1)** — needs US2's core schema: `variant` is a dictionary-typed field.
- **US4 (P2)** — needs all three: the demo needs US2's references and US3's axis, Maxitor needs both payloads.

### Within Each User Story

- Tests first, and they must fail before the implementation that answers them.
- Declaration before catalogue, catalogue before the field type, field type before the container.
- The codemod (T035) lands before the rule it serves is applied to the corpus (T036–T038) in the same phase.

### Parallel Opportunities

- T008 (mixin test) runs beside T007 (the move).
- T011, T012 (US1 tests) run in parallel; T018 (schema test) beside T016–T017.
- T021, T022 (US2 tests) run in parallel.
- T028, T029, T030 (US3 tests) run in parallel before the implementation.
- T039, T040 (US4 tests) run in parallel, and T041–T043 (demo) beside T045–T047 (Maxitor) once T041 lands.
- T051 and T052 (Polish) run in parallel.

---

## Parallel Example: User Story 3

```bash
# the three test modules, in parallel, written against the contract first
pytest packages/aoa-action-machine/tests/action_machine/domain/test_specialization_container.py &
pytest packages/aoa-action-machine/tests/action_machine/domain/test_spec_entity.py &
pytest packages/aoa-action-machine/tests/action_machine/graph/test_entity_specialization_vocabulary.py &
```

## Parallel Example: User Story 4

```bash
# the demo and the viewer, once the dictionary exists
# demo: packages/aoa-demo/src/aoa/demo/model/dictionaries/…
# viewer: packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/…
```

---

## Implementation Strategy

**MVP first**: Phase 1 + Phase 2 + Phase 3 (US1). A closed dictionary with its catalogue and its two declaration refusals is a complete, demonstrable increment: the example prints its codes, the graph carries its values, and no other kind changes.

**Then incrementally**: US2 makes the dictionary usable from a field; US3 moves the corpus onto the container; US4 makes it visible.

**Stop points**: after US1 the tree is green with the old corpus untouched; after US3 the corpus is on the container form; after US4 the feature is visible. Each stop point is a commit candidate, on instruction only.
