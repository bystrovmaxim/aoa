# Tasks: explicit entity relations, a protected dictionary member, resolvable schemas, and a card that shows labels

**Feature**: `specs/017-explicit-entity-relations` | **Branch**: `feature/issue-249-explicit-relations-and-dictionary-safety` | **Plan**: [plan.md](./plan.md) | **Spec**: [spec.md](./spec.md)

**Input**: Design documents from `specs/017-explicit-entity-relations/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel — different files, no dependency on an incomplete task
- **[Story]**: which user story the task serves (`US1`–`US6`, mapped to spec.md)
- Every task names the file it touches; a task that does not name one is not a task

## Path Conventions

Repository root is the working directory. Python packages live under `packages/*/src/aoa/*`,
their tests under `packages/*/tests/`, the viewer under `packages/aoa-maxitor` (Python action)
and `packages/aoa-maxitor/client` (TypeScript), examples under `examples/`, pages under `docs/`.

## Phase order

The phase order below is the plan's commit order, not the spec's priority order: the spec
orders the stories P1–P3, while a commit has to carry its whole migration, so the display
work (US6) lands before the large relation migration (US4). No story blocks another except
US4, which extends the validator US1 creates.

| Tasks phase | Plan phase | Story | Priority |
| --- | --- | --- | --- |
| 1. Setup | — | — | — |
| 2. US1 | 1 | entity field is explicit | P1 |
| 3. US5 | 2 | `Classifier` states only the variant | P3 |
| 4. US6 | 3 | the card shows labels | P3 |
| 5. US2 | 4 | the member is checked after validation | P1 |
| 6. US3 | 5 | the schema keeps its definitions | P2 |
| 7. US4 | 6 | a relation's description is metadata | P2 |
| 8. Polish | 7–9 | check run, documentation, changelog | — |

---

## Phase 1: Setup

- [x] T001 Re-run the four baseline reproductions (bare field, mutable member, shape mismatch, `Rel` default, `Enum` schema) and paste each exact output into the "Measured baseline" table of `specs/017-explicit-entity-relations/research.md` (FR-009, FR-015, FR-031; SC-003)
- [x] T002 Refresh both migration counts — `Classifier(field=…)` over `packages/`, `examples/`, `docs/` including `--include=*.ipynb`, and `= Rel(description=…)` — and update the Scale/Scope of `specs/017-explicit-entity-relations/plan.md` and the opening count of each migration task below (FR-031, FR-036; SC-004, SC-006)

---

## Phase 2: User Story 1 — a field whose type is an entity is declared explicitly (Priority: P1) 🎯 MVP

**Goal**: a bare structural-entity field, a collection of one, a bare `X | None` and a state-typed field are refused at the graph-build boundary with a message naming the two legal forms (or the `Lifecycle[...]` form for a state); the embedded-value marker `NoRelation("reason")` is the second legal form.

**Independent test**: declare one isolated model per form, run the build, and read the four answers; a model with a refused form fails while a model with either legal form builds, draws an edge only for the relation form, and leaves the payload unchanged for the embedded one.

### Tests for User Story 1

- [x] T003 [P] [US1] Write `packages/aoa-action-machine/tests/action_machine/graph/test_entity_field_validator.py`: a bare entity field is refused and the message names the owner, the field, the resolved type and both forms (FR-001, FR-002; SC-002)
- [x] T004 [P] [US1] Add to `packages/aoa-action-machine/tests/action_machine/graph/test_entity_field_validator.py`: a relation container is accepted, the graph gains the edge, and the field is a foreign-key row (FR-003)
- [x] T005 [P] [US1] Add to `packages/aoa-action-machine/tests/action_machine/graph/test_entity_field_validator.py`: `NoRelation("reason")` is accepted, adds no edge, and a blank reason is refused at construction (FR-004; SC-002)
- [x] T006 [P] [US1] Add to `packages/aoa-action-machine/tests/action_machine/graph/test_entity_field_validator.py`: a state-typed field is refused bare, inside a container and with the marker, each naming `Lifecycle[...]` (FR-003; SC-002)
- [x] T007 [P] [US1] Add to `packages/aoa-action-machine/tests/action_machine/graph/test_entity_field_validator.py`: `list[X]`, `dict[str, X]`, `set[X]`, `tuple[X, …]` and a bare `X | None` are refused; a forward-referenced field is judged after resolution; an `exclude_graph_model` class is skipped (FR-003, FR-005; SC-002)
- [x] T008 [P] [US1] Add to `packages/aoa-action-machine/tests/action_machine/graph/test_entity_field_validator.py`: ordinary scalars, a dictionary reference, a `Lifecycle[...]` field and a `BaseSchema` subclass are accepted unchanged (FR-006)

### Implementation for User Story 1

- [x] T009 [US1] Add `NoRelation(reason)` to `packages/aoa-action-machine/src/aoa/action_machine/domain/relation_markers.py` — frozen slots, nonblank reason, `__eq__`/`__hash__`/`__repr__`, AI-CORE block, one-line docstrings — and export it from `packages/aoa-action-machine/src/aoa/action_machine/domain/__init__.py` (FR-004)
- [x] T010 [US1] Create `packages/aoa-action-machine/src/aoa/action_machine/graph/validators/entity_field_validator.py` with module header, one public `validate_entity_fields()`, the resolved-annotation walker, the kind test and the four refusals, reusing `declared_entity_classes()` and skipping excluded classes (FR-001, FR-002, FR-005)
- [x] T011 [US1] Call `validate_entity_fields()` from `packages/aoa-action-machine/src/aoa/action_machine/graph/core/node_graph_coordinator.py` beside the specialization pass (FR-001, FR-005)
- [x] T012 [US1] Adversarially reintroduce the silent acceptance (skip the bare-field refusal), confirm T003 fails while an unrelated test in the same run passes, then restore (file: `packages/aoa-action-machine/src/aoa/action_machine/graph/validators/entity_field_validator.py`) (FR-001, FR-042)

**Checkpoint**: the four answers exist and the corpus still builds.

---

## Phase 3: User Story 5 — a classifier names its variant and nothing else (Priority: P3)

**Goal**: `Classifier(variant=…)` carries no field name; the head's inverse check still compares against the attribute name; every other specialization check survives.

**Independent test**: migrate one specialization, pass a stale `field=`, and break each remaining check in turn; each answer is a refusal naming what failed.

### Tests for User Story 5

- [x] T013 [P] [US5] Add to `packages/aoa-action-machine/tests/action_machine/intents/entity/test_entity_specialization_resolver.py`: `Classifier(field=…)` raises `TypeError`, and head/alternative, inverse, dictionary-membership and variant/data checks each still refuse their case (FR-033, FR-034, FR-035)

### Implementation for User Story 5

- [x] T014 [US5] Remove `field` from `Classifier` in `packages/aoa-action-machine/src/aoa/action_machine/domain/specialization_containers.py` — slot, constructor argument and validation, AI-CORE block, docstring — and refuse `variant=None` as today (FR-033)
- [x] T015 [US5] Delete the `marker.field != field_name` comparison in `packages/aoa-action-machine/src/aoa/action_machine/graph/validators/entity_specialization_validator.py` and keep every other check, including the head's comparison against the attribute name (FR-034)
- [x] T016 [US5] Migrate every `Classifier(field=…, variant=…)` to `Classifier(variant=…)` across `packages/`, `examples/` and `docs/` scripts, and the notebook matches, in one pass; report the refreshed count from T002 (FR-036; SC-006)
- [x] T017 [US5] Adversarially restore the deleted comparison, confirm T013's matching case fails while an unrelated check passes, then restore (file: `packages/aoa-action-machine/src/aoa/action_machine/graph/validators/entity_specialization_validator.py`) (FR-034, FR-042)

**Checkpoint**: 0 `field=` arguments remain and the five checks still refuse.

---

## Phase 4: User Story 6 — a dictionary card shows labels, not storage codes (Priority: P3)

**Goal**: the enum kind's payload field list loses `code` and `display_name`, the value row loses its code cell, the code becomes a tooltip, and the graph and payload keep both members.

**Independent test**: drive a dictionary through the payload action, validate the payload, render DOT and SVG, and check the printed text, the tooltip and the payload separately.

### Tests and checks for User Story 6

- [x] T018 [P] [US6] Extend `packages/aoa-maxitor/client/scripts/check-erd-dictionary-values.ts`: the printed text carries no code, the DOT carries `TOOLTIP="code: …"`, a code needing escaping is escaped in the tooltip too, a non-dictionary entity's rows are unchanged, and a graph saved before the change renders without a rebuild (FR-038, FR-039, FR-040; SC-007)
- [x] T019 [P] [US6] Extend `packages/aoa-maxitor/tests/test_list_entities_payload_dictionary.py`: the enum kind's field list has no `code`/`display_name`, each value still carries its code in `properties.values`, and the payload satisfies its declared schema (FR-037, FR-041)

### Implementation for User Story 6

- [x] T020 [US6] Omit `code` and `display_name` from the payload field list for the enum kind in `packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/list_entities_action.py`, leaving the graph SQL and `graph_json_schema.py` untouched (FR-037)
- [x] T021 [US6] Drop the code cell and add the row tooltip in `packages/aoa-maxitor/client/src/lib/buildDotSource.ts`, following the tooltip the specialization axis row already uses (FR-038, FR-039)
- [x] T022 [US6] Reconcile §3 of `specs/016-value-declaration-consistency/contracts/dictionary-card.md` to the final behaviour instead of adding a second contract (FR-041)
- [x] T023 [US6] Adversarially restore the printed code cell, confirm T018 fails while the payload test passes, then restore (file: `packages/aoa-maxitor/client/src/lib/buildDotSource.ts`) (FR-042; SC-007)

**Checkpoint**: three client checks green, payload schema green, an old graph renders.

---

## Phase 5: User Story 2 — a shared dictionary member cannot be changed after custom validation (Priority: P1)

**Goal**: the completed member is verified against its declared annotation and the immutable set before it is published; a mutable or mismatched value is refused with the dictionary, the member, the property path and the actual type.

**Independent test**: the two reproducers (list-returning validator, joined-string validator) refuse at declaration, a valid tuple still publishes, and editing an export changes nothing.

### Tests for User Story 2

- [ ] T024 [P] [US2] Add to `packages/aoa-action-machine/tests/action_machine/domain/test_dictionary_property_types.py`: a validator returning `list(...)` is refused, and neither `members` nor `by_code()` exposes the member (FR-008, FR-009, FR-012, FR-014)
- [ ] T025 [P] [US2] Add to `packages/aoa-action-machine/tests/action_machine/domain/test_dictionary_property_types.py`: a model-level after-validator mutating a tuple's contents is refused; an `Enum` whose value is a list is refused naming the enum class and the value type (FR-010, FR-011)
- [ ] T026 [P] [US2] Add to `packages/aoa-action-machine/tests/action_machine/domain/test_dictionary_property_types.py`: a validator returning a different immutable type is refused with the declared and the actual type; a validator returning an equal tuple is accepted; a state type whose status holds a list is still published; editing an exported array never reaches the declared tuple (FR-011, FR-012, FR-013)

### Implementation for User Story 2

- [ ] T027 [US2] Add the runtime member check to `packages/aoa-action-machine/src/aoa/action_machine/domain/declared_values.py`, between member construction and the assignment of `members`/`_by_code`: annotation agreement plus the recursive immutable set, refusing — never freezing — with the four-part message (FR-008, FR-009, FR-010)
- [ ] T028 [US2] Update the `BaseEnumEntity` AI-CORE block and docstring in `packages/aoa-action-machine/src/aoa/action_machine/domain/enum_entity.py` to state the runtime member contract (FR-008)
- [ ] T029 [US2] Adversarially remove the runtime check (keep the annotation check), confirm T024 fails while the valid-tuple case passes, then restore (file: `packages/aoa-action-machine/src/aoa/action_machine/domain/declared_values.py`) (FR-014, FR-042; SC-003)

**Checkpoint**: no member with a mutable value or a mismatched type is reachable.

---

## Phase 6: User Story 3 — a dictionary's serialization schema is self-contained (Priority: P2)

**Goal**: the serialization schema keeps the definitions its references name, and its nested `required` list describes what is actually emitted.

**Independent test**: generate the schema for an `Enum`-valued property, validate the real export against it, fail a disallowed enum value, and resolve every local reference.

### Tests for User Story 3

- [ ] T030 [P] [US3] Add to `packages/aoa-action-machine/tests/action_machine/domain/test_dictionary_json_schema.py`: the reproducer returns a schema, every local `$ref` resolves, the real export validates, and a disallowed enum value is refused (FR-015, FR-018, FR-021; SC-003)
- [ ] T031 [P] [US3] Add to `packages/aoa-action-machine/tests/action_machine/domain/test_dictionary_json_schema.py`: a direct, an optional and a tuple-contained `Enum`; a dictionary field inside a containing model; two definitions with the same short class name; a custom serializer whose output type differs from its enum value (FR-015, FR-016, FR-020)
- [ ] T032 [P] [US3] Add to `packages/aoa-action-machine/tests/action_machine/domain/test_dictionary_json_schema.py`: `properties.required` lists a null-emitted key as required, omits an excluded field, and the input schema still accepts a code-only reference (FR-017, FR-019)

### Implementation for User Story 3

- [ ] T033 [US3] Rework `_emitted_reference_schema()` in `packages/aoa-action-machine/src/aoa/action_machine/domain/enum_entity.py`: keep the generated `$defs` reachable from the emitted property fragments, derive the nested `required` from the generated document, and leave the input schema and the field serializers' output shapes untouched (FR-015, FR-016, FR-017)
- [ ] T034 [US3] Adversarially drop the definitions again, confirm T030 fails while the input-schema test passes, then restore (file: `packages/aoa-action-machine/src/aoa/action_machine/domain/enum_entity.py`) (FR-021, FR-042)

**Checkpoint**: the `KeyError` is gone and the export validates against its own schema.

---

## Phase 7: User Story 4 — a relation's description is metadata, never a runtime value (Priority: P2)

**Goal**: the default contract from `contracts/relation-field-metadata.md` holds for all eight containers, both `Field` syntaxes feed one `FieldInfo.description`, `Rel` is gone, and 262 declarations plus the hydration callers migrate.

**Independent test**: all four rows of the default table, the factory refusal without invocation, the description refusals, and a `Rel` import failing.

### Tests for User Story 4

- [ ] T035 [P] [US4] Add to `packages/aoa-action-machine/tests/action_machine/domain/test_hydration.py` and the graph tests: the four rows of the default table independently, including hydration through `build()`, and the default and description checks repeated for an inherited relation field and for one named through a forward reference (FR-023, FR-026; SC-003)
- [ ] T036 [P] [US4] Add to the same tests: a prebuilt relation default and every `default_factory` are refused, and the factory is never executed; a `Rel` import fails (file: `packages/aoa-action-machine/tests/action_machine/domain/test_hydration.py`) (FR-024, FR-031)
- [ ] T037 [P] [US4] Add to the same tests: missing, empty and whitespace-only descriptions are refused including a hidden edge; a description supplied through either `Field` syntax reaches both the relation edge and the specialization edge (file: `packages/aoa-action-machine/tests/action_machine/domain/test_hydration.py`) (FR-025, FR-026, FR-028)

### Implementation for User Story 4

- [ ] T038 [US4] Extend `packages/aoa-action-machine/src/aoa/action_machine/graph/validators/entity_field_validator.py` with the relation-default and description rules for the eight containers, inherited fields and resolved forward references (FR-022, FR-023, FR-024, FR-026)
- [ ] T039 [US4] Give `packages/aoa-action-machine/src/aoa/action_machine/intents/entity/entity_relation_intent_resolver.py` and `entity_specialization_intent_resolver.py` one description rule reading `FieldInfo.description` only, and delete both `Rel`-default fallback branches (FR-027)
- [ ] T040 [US4] Delete `Rel` from `packages/aoa-action-machine/src/aoa/action_machine/domain/relation_markers.py` and its export; correct the marker and container docstrings, the coordinator's claim that both ends carry `Rel`, and the `hydration.py` paragraph advertising a relation default (FR-031)
- [ ] T041 [US4] Migrate every `= Rel(description=…)` to `Field(description=…)` across `packages/`, `examples/` and `docs/`, deciding each of the seven nullable relations by its full-construction call sites, and update the assertion the old default leaked — `assert isinstance(entity.children, Rel)` in `packages/aoa-action-machine/tests/action_machine/domain/test_hydration.py` (FR-029, FR-030; SC-004)
- [ ] T042 [US4] Adversarially accept a non-`None` default and reinstate one description fallback, confirm each targeted test fails while a valid nullable relation still passes, and confirm description text, relation targets, inverse matching, classifier mappings and edge semantics are unchanged, then restore (file: `packages/aoa-action-machine/src/aoa/action_machine/graph/validators/entity_field_validator.py`) (FR-030, FR-032, FR-042; SC-003)

**Checkpoint**: no relation slot can hold a description object, and no module imports `Rel`.

---

## Phase 8: Polish & cross-cutting concerns

Exactly three tasks — the constitution's tail, in this order, and no other task absorbs them.

- [ ] T043 Run `bash scripts/run_checks_with_log.sh` and take it to zero, including the client build, the three Node checks, mypy, pylint, radon, vulture, packaging and every package's suite; confirm only the chunk-size advisory and the pending-deprecation warning remain, and record the tail (FR-044; SC-008)
- [ ] T044 Write the documentation in English — `docs/tutorials/step-21-relations.md`, the dictionary chapter, `docs/reference/intents-and-invariants.md`, `docs/reference/glossary.md`, `docs/how-to/specialization-declaration-fails.md` — with a case for every new refusal, each case as a script under `examples/step_20_dictionaries/` and `examples/step_21_relations/` and as a notebook, executed while written; no Russian draft (FR-045; SC-008)
- [ ] T045 Write the changelog article in `docs/CHANGELOG.md` for `aoa-action-machine` and `aoa-maxitor`: what a reader can now do — the two legal forms, the member guarantee, the resolvable schema, the card without codes — in plain words, without a per-file account (FR-045; SC-008)

---

## Dependencies & execution order

### Story dependencies

- **US1 (phase 2)** has no dependency; it creates `entity_field_validator.py`.
- **US5 (phase 3)** and **US6 (phase 4)** are independent of every other story.
- **US2 (phase 5)** and **US3 (phase 6)** are independent of each other and of the rest.
- **US4 (phase 7)** extends the module US1 creates, so it follows phase 2; it shares no declaration with US2, US3, US5 or US6.
- **Phase 8** follows every story, and T043 precedes T044, which precedes T045.

### Within a story

Tests first (T003–T008, T013, T018–T019, T024–T026, T030–T032, T035–T037), then the implementation, then the adversarial reintroduction. A test that passes before its implementation is a test that proves nothing.

### Parallel opportunities

- T001 and T002 in Setup.
- Every test task marked `[P]`: T003–T008 (eight files' worth of cases across two modules), T013, T018/T019, T024–T026, T030–T032, T035–T037.
- The two payload tasks T019 and T018 run in parallel (Python test and TypeScript check).
- T039's two resolver edits are one task because they must stay identical.

### Parallel example — Phase 5 tests

```text
Task: T024 — list-returning validator refused, member unreachable
Task: T025 — nested tuple mutation refused; enum with a mutable value refused
Task: T026 — shape mismatch refused; equal tuple accepted; export independence
```

## Implementation strategy

### MVP first

US1 alone (phase 2) is the MVP: the silent scalar is refused, the two forms exist, and the rest of the corpus is untouched. Validate it with `quickstart.md` proofs 1–5, then commit on instruction.

### Incremental delivery

Add one phase at a time, each a commit on instruction, each leaving the tree green:
US5 → US6 → US2 → US3 → US4. US4 is last because its migration is the widest and because it
rewrites the description source every other story reads from the graph.

### What is deliberately not a task

- A compatibility window for `Rel`, a second description carrier, or a deprecated `Classifier.field` — the spec refuses all three.
- A storage migration or a graph rebuild — the graph keeps the code and the label.
- A Russian draft of any page — the spec's Out of scope says so.
- Acting on the two accepted remarks of the check run.
- A commit, a push, a pull request or a merge: phase boundaries are commit boundaries only on the maintainer's instruction.

## Format validation

Every task above carries a checkbox, an ID, an optional `[P]`, a story label inside a story phase, and at least one concrete file path; the three tail tasks carry no story label, and none of them was absorbed by an earlier phase.
