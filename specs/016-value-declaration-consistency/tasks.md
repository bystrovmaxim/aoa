# Tasks: an explicit `value(...)`, a protected value, one reference form, one label

**Input**: Design documents from `specs/016-value-declaration-consistency/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: included. Every requirement of this feature is either a refusal, a count or a wire shape, so each one is asserted by a test or a check script; a requirement without one is not done.

**Organization**: tasks are grouped by user story, in the priority order of the spec. US1 is the MVP. A phase ends with a commit **only on the maintainer's instruction** (constitution I); the task list names no commit.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel — a different file, no dependency on an incomplete task
- **[Story]**: the user story the task belongs to (US1–US6)
- Every task names the exact file it touches

## Path Conventions

Repository root holds `packages/`, `examples/`, `docs/`, `specs/`. The framework is `packages/aoa-action-machine`, the viewer `packages/aoa-maxitor` (Python action + TypeScript client), the demo `packages/aoa-demo`.

---

## Phase 1: Setup (shared infrastructure)

**Purpose**: the baseline every later phase is measured against, and the tool that performs the migration.

- [x] T001 Confirm the branch `feature/issue-244-simplify-value-declarations` is based on `e791ad28`, the tree is otherwise clean, and `uv sync` succeeds; record the commit and the Pydantic version in `specs/016-value-declaration-consistency/evidence/baseline.before.txt`
- [x] T002 [P] Run `uv run python specs/016-value-declaration-consistency/evidence/scan_value_declarations.py` and append its table to `specs/016-value-declaration-consistency/evidence/baseline.before.txt`; it must print `373` class-name declarations in `116` files and `332` suppressed lines in `117` files
- [x] T003 [P] Add `specs/016-value-declaration-consistency/evidence/reproduce_defects.py` printing the four baseline defects — nested mutation of `to_reference()`, an ignored `@field_serializer`, `json.dumps(to_reference())` raising, and the input schema rejecting a code-only reference — and store its output beside the scan
- [x] T004 Write `specs/016-value-declaration-consistency/evidence/migrate_value_declarations.py`: rewrite `NAME = <Owner>Entity(` to `NAME = value(` only for uppercase targets inside a declaring class body, add `value` to the module's `aoa.action_machine.domain` import, strip `# noqa: F821` / `# type: ignore[name-defined]` from the migrated lines, and refuse a file whose migrated count differs from the count it found

**Checkpoint**: the baseline is recorded and the migration tool exists and refuses a partial rewrite.

---

## Phase 2: User Story 1 — declare a value with `value(...)` (Priority: P1) 🎯 MVP

**Goal**: `value(...)` is the one public declaration form for both kinds; the namespace, the metaclass and the Pydantic-internal import are gone; every declaration in the repository is on the new form.

**Independent Test**: declare a dictionary and a state type with `value(...)` only, check attribute identity, `members`, `codes()`, `by_code()`, `entity_type` and order; then confirm the replaced form fails, and that `scan_value_declarations.py` reports 0 and 0.

### Tests for User Story 1

- [x] T005 [P] [US1] Rewrite `packages/aoa-action-machine/tests/action_machine/domain/test_declared_values.py` — the factory returns a placeholder with its kwargs, the placeholder becomes an instance and never a field, the catalogue keeps order, both per-kind switches behave, the mixin is not a kind base; delete the alias test and add `test_a_class_body_naming_its_own_class_fails` (FR-001, FR-002, FR-004)
- [x] T006 [P] [US1] Add `packages/aoa-action-machine/tests/action_machine/domain/test_value_export.py` — `from aoa.action_machine.domain import value` works, `"value"` is in `__all__`, `DeclaredValuesMeta` / `_DeclaredValuesNamespace` no longer exist in `declared_values`, and a grep over `packages/` and `examples/` finds neither name anywhere (FR-001, FR-003; SC-002)
- [x] T007 [P] [US1] Run `packages/aoa-action-machine/tests/action_machine/domain/test_dictionary_scope.py`, `test_dictionary_core_schema.py` and `test_state_entity.py` now — this is the before-snapshot — and again after T011; only declaration lines may differ, every assertion stays byte-identical (FR-005, FR-006)

### Implementation for User Story 1

> The tree is red from T008 until T011 completes: the alias leaves before the corpus follows. That is the within-phase state, not the phase's end — only the checkpoint after T017 must be green, and the whole phase is one commit (plan phase 1).

- [x] T008 [US1] Delete `_DeclaredValuesNamespace`, `DeclaredValuesMeta`, the `ModelMetaclass` import and the namespace section of the module docstring from `packages/aoa-action-machine/src/aoa/action_machine/domain/declared_values.py`; annotate `value(**kwargs) -> Any` and give it its AI-CORE block and one-line docstring (FR-002, FR-003; research D2)
- [x] T009 [US1] Remove `metaclass=DeclaredValuesMeta` and the `DeclaredValuesMeta` import from `packages/aoa-action-machine/src/aoa/action_machine/domain/enum_entity.py` and `packages/aoa-action-machine/src/aoa/action_machine/domain/state_entity.py`, keeping `ignored_types=(ValueSpec,)` and the conversion hook (FR-003)
- [x] T010 [US1] Export `value` from `packages/aoa-action-machine/src/aoa/action_machine/domain/__init__.py` — the import, the `__all__` entry, and the usage example in the module docstring rewritten to `value(...)` (FR-001)
- [x] T011 [US1] Run `migrate_value_declarations.py` over `packages/aoa-action-machine` (sources and tests) and confirm the framework suite and `mypy --strict` pass on that area alone (FR-007)
- [x] T012 [US1] Run `migrate_value_declarations.py` over `packages/aoa-demo` — 103 declarations in 25 files, mechanically only — and run `pytest packages/aoa-demo/tests -q` (FR-007)
- [x] T013 [US1] Run `migrate_value_declarations.py` over `examples/` — 194 declarations in the scripts, including `examples/step_22_lifecycle/19_non_json_field.py` — and run every migrated script once (FR-007)
- [x] T014 [US1] Rewrite the code cells of `examples/step_20_dictionaries/*.ipynb` (25 notebooks) and every other affected notebook file with the same rules, editing only cell sources and re-serialising with the same indentation; abort on a failed JSON load (FR-007; research D10)
- [x] T015 [US1] Remove the 13 file-level `# ruff: noqa: F821` lines and the now-unused `value as state` import in `packages/aoa-action-machine/tests/action_machine/domain/test_state_entity.py`; re-run ruff on the touched areas (FR-007)
- [x] T016 [US1] Rewrite the declaration examples in the docstrings of `declared_values.py`, `enum_entity.py`, `state_entity.py` and `entity_graph_node.py` to `value(...)`, so no module header shows the removed form (FR-007)
- [x] T017 [US1] Re-run `scan_value_declarations.py` and confirm `0` class-name declarations and `0` suppressed lines, appending the table to `specs/016-value-declaration-consistency/evidence/baseline.after.txt` (FR-007; SC-001, SC-002, SC-003)

**Checkpoint**: one declaration form in the repository, everything imports, the catalogue behaves as before. This is the MVP.

---

## Phase 3: User Story 2 — a shared value cannot be changed by a consumer (Priority: P1)

**Goal**: a dictionary value carries no mutable data, so neither the exported reference form nor the attribute offers a mutation path.

**Independent Test**: declare a dictionary value with `labels: list[str]` and see it refused with the class, the field and the type named; declare one with a `tuple[str, ...]` and a `date` and confirm the exported form holds nothing mutable; declare the same `list[str]` on a state type and see it accepted.

### Tests for User Story 2

- [x] T018 [P] [US2] Add `packages/aoa-action-machine/tests/action_machine/domain/test_dictionary_property_types.py` — one accepted case per leaf type (`str`, `int`, `float`, `bool`, `Decimal`, `date`, `datetime`, `time`, `UUID`, an `Enum`, a `Literal`), accepted `tuple[...]`, accepted `Optional[...]`; refusals for `list`, `dict`, `set`, `frozenset`, a nested model, `Any`; a refused type nested inside a tuple; and a state type declaring `list[str]` accepted (FR-009 to FR-012)

### Implementation for User Story 2

- [x] T019 [US2] Add the per-kind switch `__declared_values_immutable__` to the mixin in `packages/aoa-action-machine/src/aoa/action_machine/domain/declared_values.py`, off by default (research D3)
- [x] T020 [US2] Add the recursive annotation walk and its refusal to `packages/aoa-action-machine/src/aoa/action_machine/domain/declared_values.py`, run from `__pydantic_init_subclass__` when the switch is on, with the message of `specs/016-value-declaration-consistency/contracts/declared-value.md` §6 (FR-010, FR-011)
- [x] T021 [US2] Turn the switch on for `BaseEnumEntity` in `packages/aoa-action-machine/src/aoa/action_machine/domain/enum_entity.py` and update its AI-CORE `INVARIANTS` line with the supported types (FR-010)
- [x] T022 [US2] Prove the state kind is untouched: run `pytest packages/aoa-action-machine/tests/action_machine/domain/test_lifecycle_current_status.py packages/aoa-action-machine/tests/action_machine/graph_host/test_lifecycle_graph_node.py -q` unedited, and run `uv run python examples/step_22_lifecycle/19_non_json_field.py` (FR-012, FR-031)

**Checkpoint**: the reproduced mutation defect is impossible, and the lifecycle suite is unchanged.

---

## Phase 4: User Story 3 — a reference serializes through its own field serializers (Priority: P2)

**Goal**: `to_reference()` is the value's JSON export, so a serializer runs and every leaf is JSON-compatible, including in the graph document.

**Independent Test**: declare a dated value with a `%d/%m/%Y` serializer and one without; `json.dumps` both references; export a graph document and parse it.

### Tests for User Story 3

- [x] T023 [P] [US3] Extend `packages/aoa-action-machine/tests/action_machine/domain/test_dictionary_core_schema.py` — a custom serializer's text in the reference, a `date` as its ISO string without one, `json.dumps` not raising, the Python-mode dump documented as possibly different, and a value with two extra fields where only one has a serializer: the other keeps its own emitted form (FR-013 to FR-015)
- [x] T024 [P] [US3] Add `packages/aoa-action-machine/tests/action_machine/graph/test_dictionary_reference_json.py` — the actual node's `properties["values"]` survives `json.dumps` and carries the serializer's text (FR-016)

### Implementation for User Story 3

- [x] T025 [US3] Replace the `getattr` loop in `to_reference()` with the split of `model_dump(mode="json")` in `packages/aoa-action-machine/src/aoa/action_machine/domain/enum_entity.py`, and state the JSON-only contract in its docstring (FR-013, FR-014; research D5)
- [x] T026 [US3] Re-check the plain-serializer lambda and the validation path in `packages/aoa-action-machine/src/aoa/action_machine/domain/enum_entity.py` for recursion — the reference must be produced once per serialization (FR-013)
- [x] T027 [US3] Re-run the corpus checks that compare the reference with a dump — `packages/aoa-action-machine/tests/action_machine/domain/test_dictionary_scope.py` and `uv run python examples/step_20_dictionaries/03_serialization.py` — and reword the assertion to name the mode where it compares with `model_dump()` (FR-014, SC-004)

**Checkpoint**: no entry point can return a non-serializable leaf.

---

## Phase 5: User Story 4 — input and output schemas describe their own contracts (Priority: P2)

**Goal**: the validation schema accepts a code-only reference, the serialization schema describes the emitted reference including each property's serialized type.

**Independent Test**: validate `{"code": "eur"}` against the input schema; validate an emitted reference against the output schema; compare a property whose field has a serializer.

### Tests for User Story 4

- [ ] T028 [P] [US4] Add `packages/aoa-action-machine/tests/action_machine/domain/test_dictionary_json_schema.py` — code-only, code+label and full reference validate on the input side; a blank code and an extra member are refused; the output side requires `code`, `display_name`, `properties` and types each property; a serializer's field is a plain `string`; no `$defs`; the hook is entered once per mode (FR-017 to FR-020)
- [ ] T029 [P] [US4] Keep `packages/aoa-action-machine/tests/action_machine/domain/test_dictionary_core_schema.py`'s runtime refusals green — missing, blank and unknown codes; a stale label and stale properties ignored (FR-019)

### Implementation for User Story 4

- [ ] T030 [US4] Rewrite `__get_pydantic_json_schema__` in `packages/aoa-action-machine/src/aoa/action_machine/domain/enum_entity.py` to branch on `handler.mode`: the validation branch accepts a code-only reference with an open `properties`; the serialization branch requires all three members (FR-017, FR-018)
- [ ] T031 [US4] Add the helper, with its one-line docstring (constitution V), that lifts the emitted `properties` from `GenerateJsonSchema().generate(copy, mode="serialization")` over a metadata-stripped core schema, stripping `title` and `description` from each property schema, in `packages/aoa-action-machine/src/aoa/action_machine/domain/enum_entity.py` (research D6)
- [ ] T032 [US4] Document the asymmetry as intentional in the hook's docstring and in `packages/aoa-action-machine/src/aoa/action_machine/domain/enum_entity.py`'s AI-CORE `CONTRACT` (FR-018)
- [ ] T033 [US4] Run `pytest packages/aoa-action-machine/tests/action_machine/graph/ -q` and `pytest packages/aoa-maxitor/tests/ -q` to prove the graph schema and the ERD payload schema — which describe other documents — are unaffected (FR-021)

**Checkpoint**: each schema describes one side of the contract, and no runtime refusal changed.

---

## Phase 6: User Story 5 — a dictionary's properties reach the ERD card (Priority: P3, verification)

**Goal**: every property present in the graph reaches the rendered card, for every supported shape, and a drop between layers fails a test.

**Independent Test**: run a dictionary with a two-property value, a `<`/`>`/`&` value, an empty property list and an array property through the action and the renderer; compare the visible rows with the declared values.

### Tests and checks for User Story 5

- [ ] T034 [P] [US5] Extend `packages/aoa-maxitor/tests/test_list_entities_payload_dictionary.py` — a value with two properties, one with `<`, `>` and `&`, one with none (an empty list, not a missing member), one whose property is an array, one whose property is `None`, one whose property is an empty string, and a model with no dictionaries; assert every item is `{name, value}` with both strings, `additionalProperties: false`, and the deterministic text of each (`null`, `""`, `["a", "b"]`) (FR-021, FR-023, FR-025)
- [ ] T035 [P] [US5] Make the drop-between-layers case a countable invariant in `packages/aoa-maxitor/tests/test_list_entities_payload_dictionary.py`: assert `len(properties) == len(graph_mapping)` for every value, and feed the same payload through a deliberately lossy local conversion that skips one member, asserting the assertion above fails (FR-022, FR-030)
- [ ] T036 [P] [US5] Extend `packages/aoa-maxitor/client/scripts/check-erd-dictionary-values.ts` — an array-valued property rendered as deterministic JSON text, a value with no properties rendering no empty row, the DOT carrying `&lt;safe&gt; &amp; readable` for a property with `<`/`>`/`&`, and the same text found in the rendered SVG in the XML-escaped form Graphviz emits (the existing check asserts the decoded `€`, so the new assertion is written against the actual output rather than assumed) (FR-023, FR-024)
- [ ] T037 [US5] Run the payload test, the client check and the SVG assertions, and confirm the payload validates against `list_entities_action_schema.py` with no schema edit (FR-021, SC-005)

**Checkpoint**: the carrier #243 merged is proven complete for every supported value shape, with no production change beyond the serialization fixes of US3 and US4.

---

## Phase 7: User Story 6 — a specialization group label is composed once (Priority: P3)

**Goal**: the dictionary name appears once in a group label, composed by the server, rendered by the client.

**Independent Test**: produce the server payload for a group and feed it to `buildDotSource`; the DOT label names the dictionary once.

### Tests for User Story 6

- [ ] T038 [P] [US6] Update `packages/aoa-maxitor/tests/test_list_entities_specialization_contract.py` — the group's key set loses `dictionary_label`, and the label is `field (by Dictionary)`; the same key set in `packages/aoa-maxitor/tests/test_entity_specialization_erd.py` (FR-027)
- [ ] T039 [P] [US6] Add `packages/aoa-maxitor/client/scripts/check-erd-group-label.ts` — take the payload the server test produces, render it through `buildDotSource`, and assert the dictionary name appears exactly once and escaping happens once (FR-028, FR-029)

### Implementation for User Story 6

- [ ] T040 [US6] Remove `dictionary_label` from the group `SELECT` and the group dict in `packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/list_entities_action.py`, keeping the composed `label` and `classifier_field` (FR-027)
- [ ] T041 [US6] Remove the property from the group item in `packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/list_entities_action_schema.py` and from `ErdGroup` in `packages/aoa-maxitor/client/src/lib/buildDotSource.ts` (FR-027)
- [ ] T042 [US6] Delete the second append in `packages/aoa-maxitor/client/src/lib/buildDotSource.ts` — the label is rendered as received, escaped once (FR-028)
- [ ] T043 [US6] Run `packages/aoa-maxitor/tests/test_list_entities_specialization_contract.py`, `packages/aoa-maxitor/tests/test_entity_specialization_erd.py`, `packages/aoa-maxitor/client/scripts/check-erd-group-label.ts` and the Maxitor client build (FR-027 to FR-029, SC-006)

**Checkpoint**: one owner for the label, and two layer-local tests can no longer hide the duplication.

---

## Phase 8: Polish & cross-cutting concerns

**Purpose**: the three closing tasks of constitution VI, in their order, plus the quickstart proof. No earlier phase absorbs them.

> This phase is **three commits**, not one: T044 is the check run, T045 with T047 is the documentation, T046 is the changelog — the order VI.1, VI.2, VI.3 refuses any other arrangement.

- [ ] T044 Run `bash scripts/run_checks_with_log.sh` and take it to zero, with the two accepted remarks (the Vite chunk-size advisory and the pending-deprecation warning) left alone; then perform the adversarial check for each corrected defect in isolation — an accepted mutable property, a bypassed serializer, a non-serializable export, an input schema rejecting a code-only reference, a property dropped between graph and card, a twice-composed label — confirming the targeted test fails and unrelated tests in the selected run pass, restoring each time; record every command, output and restoration in `specs/016-value-declaration-consistency/evidence/closing-check-run.md` (FR-030, FR-032, FR-033, SC-004)
- [ ] T045 Write the documentation — `docs/tutorials/step-20-dictionaries.md` (the declaration, the supported types, the reference form, both schemas), `docs/tutorials/step-21-relations.md` and `docs/tutorials/step-22-lifecycle.md` (their declaration examples), `docs/how-to/specialization-declaration-fails.md` (the refusal messages), `docs/explanation/architectural-constitution.md` (its example), `docs/tutorials/step-26-maxitor.md` and `packages/aoa-maxitor/client/src/components/diagrams/ErdViewer/parts/ErdGraphvizCanvas/README.md` (the single-owner label and the property rows); reconcile `specs/015-closed-dictionary-variants/contracts/dictionary-declaration.md` and the stale ERD risk in `specs/015-closed-dictionary-variants/plan.md` as resolved; add the four new cases — a refused mutable property, a serializer's text, the two schema modes, the single label — as scripts under `examples/step_20_dictionaries/` each with its notebook; execute every one of the 25 dictionary scripts and their notebooks, plus `examples/step_22_lifecycle/19_non_json_field.py`; state the one-line declaration migration and the `value` import as the whole migration (FR-008); create no Russian draft (FR-026; SC-007; constitution VI.2, VI.4–VI.6)
- [ ] T046 Write the changelog last: one article in `docs/CHANGELOG.md` about what this work created — the one-line declaration migration, the value that can no longer be changed, the reference that now carries a serializer's text, the two schemas, the properties on the card — in plain words, with no per-file account; `[Unreleased]` entries in `packages/aoa-action-machine/CHANGELOG.md`, `packages/aoa-maxitor/CHANGELOG.md` and `packages/aoa-demo/CHANGELOG.md` (FR-026; constitution VI.3)
- [ ] T047 Run every scenario of `specs/016-value-declaration-consistency/quickstart.md` and correct the page where an output differs; the scan scenario must print `0` and `0` (SC-001 to SC-007)

---

## Dependencies & execution order

### Phase dependencies

- **Setup (Phase 1)**: no dependency.
- **US1 (Phase 2)**: depends on Setup (T004's tool, T001–T002's baseline). It blocks US2–US5, because each adds declarations in tests and examples that must be written in the surviving form.
- **US2 (Phase 3)**: depends on US1. It touches the same mixin the alias removal edits.
- **US3 (Phase 4)**: depends on US1; independent of US2.
- **US4 (Phase 5)**: depends on US3 — the output schema describes what the new reference form emits.
- **US5 (Phase 6)**: depends on US3 and US4 — the card proof is the reason those two exist.
- **US6 (Phase 7)**: independent of US1–US5 in code; it is sequenced last because it touches the same Maxitor files as US5 and the plan orders it there.
- **Polish (Phase 8)**: depends on every story.

### Within a story

Tests first (they must fail before the implementation), then the implementation, then the run that proves the story independently. Files shared by two tasks of the same story are ordered, not parallel.

### Parallel opportunities

- T002 and T003 (different evidence files) in Setup.
- T005, T006, T007 (three different test modules) in US1.
- The documentation examples of T045 are separate files and can be written in parallel once the code is settled; the check run of T044 precedes all of them.

### Parallel example — User Story 1 tests

```bash
# Three independent test modules, written before T008 touches the machinery:
Task: "Rewrite test_declared_values.py without the alias"
Task: "Add test_value_export.py for the public factory"
Task: "Confirm the refusal suites pass unedited"
```

---

## Implementation strategy

### MVP first

1. Phase 1 — baseline and the migration tool.
2. Phase 2 — one declaration form, the whole corpus migrated.
3. **Stop and validate**: `scan_value_declarations.py` prints 0/0, three package suites and `mypy --strict` pass. That alone delivers the explicit declaration the issue asks for, and it is the only phase whose absence blocks every other.

### Incremental delivery after the MVP

US2 (a value that cannot be changed) → US3 (a reference a consumer can serialize) → US4 (schemas that tell the truth) → US5 (the property that reaches the card) → US6 (one label) → the three closing tasks. Each story is independently testable at its checkpoint, and none reopens an earlier one.

### What is deliberately not a task

- No commit, push, pull request or merge: those happen on instruction only (constitution I).
- No Russian draft for the documentation pages: #244 forbids it (research D11). The task list keeps `tasks.ru_draft.md` beside it for the maintainer, and `.gitignore` keeps that file out of a commit.
- No compatibility shim for the removed alias, no separate `Enum`, no new generic parameter, no demo behaviour change, no storage migration, no graph rebuild.
