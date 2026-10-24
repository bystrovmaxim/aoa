# Tasks: Endpoint Role Compatibility

**Input**: Design documents from `/specs/021-endpoint-role-compatibility/`

**Prerequisites**: [plan.md](plan.md) (required), [spec.md](spec.md) (required for user stories),
[research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/),
[quickstart.md](quickstart.md)

**Tests**: Included — the specification explicitly requires them (FR-024…FR-027, adversarial verification).

**Organization**: Tasks are grouped by user story so each story can be implemented and tested independently. The three closing tasks (C1 check run, C2 documentation, C3 changelog) are reserved for the tail per FR-028 and constitution VI and are not absorbed by any story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1…US7)

## Path Conventions

Source lives under `packages/aoa-action-machine/src/aoa/action_machine/`; package tests under
`packages/aoa-action-machine/tests/`; teaching examples under `examples/step_21_relations/`;
documentation under `docs/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the workspace is ready; no new project scaffold is needed (existing library).

- [x] T001 Verify the branch environment is green before work: `uv run --extra dev pytest packages/aoa-action-machine/tests -q` passes, and confirm no new dependency is required by this feature.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The role-pair matrix, the public exception, and the role-mapping helper — every role-compatibility story (US1, US3, US4) depends on them.

**⚠️ CRITICAL**: No role-compatibility work can begin until this phase is complete.

- [x] T002 [P] Define the symmetric 8×8 role-pair matrix as a module-level constant in `packages/aoa-action-machine/src/aoa/action_machine/graph/validators/entity_role_compatibility_validator.py` — the eight roles (`AssociationOne`, `AssociationMany`, `AggregateOne`, `AggregateMany`, `CompositeOne`, `CompositeMany`, `Specialization`, `Generalization`), exactly 12 permitted and 24 prohibited unordered combinations (22 permitted / 42 prohibited directed cells), encoded as a family lookup so One/Many never changes a verdict (FR-007, `contracts/role-pair-matrix.md`).
- [x] T003 [P] Add the public exception `RoleCompatibilityError` to `packages/aoa-action-machine/src/aoa/action_machine/domain/exceptions.py` with an AI-CORE block (`ROLE`/`CONTRACT`/`INVARIANTS`), a constructor that carries both owner classes and field names, both resolved roles, the violated rule and the permitted correction, and export it from the package public surface (`__all__`). Keep `EntityFieldDeclarationError` and `SpecializationDeclarationError` unchanged for their existing checks.
- [x] T004 Map a `ResolvedEntityField.container` to one of the eight roles in the same validator module: `AssociationOne`/`AssociationMany`/`AggregateOne`/`AggregateMany`/`CompositeOne`/`CompositeMany` from the six container classes, and `Specialization`/`Generalization` from the specialization containers, using `relation_kind`/`cardinality` where the container identity alone is not enough.

**Checkpoint**: Matrix, exception and role mapping ready — user story implementation can now begin.

---

## Phase 3: User Story 1 - Assemble a model and enforce the role-pair matrix before publication (Priority: P1) 🎯 MVP

**Goal**: For every explicitly paired relationship, the two resolved roles are validated against the matrix before graph publication; permitted pairs publish, prohibited pairs block publication.

**Independent Test**: Assemble a model for each of the 12 permitted and 24 prohibited unordered combinations and confirm publication/refusal; reverse each pair and confirm the verdict is unchanged.

### Implementation for User Story 1

- [x] T005 [US1] Implement `validate_entity_role_compatibility(entities=None)` in `packages/aoa-action-machine/src/aoa/action_machine/graph/validators/entity_role_compatibility_validator.py`: walk every declared `@entity` class (the same walk the inverse validator uses), and for each field with `has_inverse` and `is_relation`/`is_specialization`/`is_generalization`, resolve the reverse field on the target (by `(declaring_owner, field_name)` identity), map both endpoints to roles, consult the matrix, and raise `RoleCompatibilityError` on a refused cell. Module header follows constitution III (`Name — purpose.`, `PURPOSE`, `ARCHITECTURE / DATA FLOW`, closing `"""`).
- [x] T006 [US1] Wire the check into `packages/aoa-action-machine/src/aoa/action_machine/graph/core/node_graph_coordinator.py`: call `validate_entity_role_compatibility()` in `NodeGraphCoordinator.build()` after `validate_entity_inverses()` and before `_gather_all_nodes(...)`, and extend the `Raises` docstring.
- [x] T007 [US1] Wire the check into `packages/aoa-action-machine/src/aoa/action_machine/graph/nodes/entity_graph_node.py` beside the existing `validate_entity_inverses` call, so the per-node build path enforces the matrix too.

### Tests for User Story 1

- [x] T008 [P] [US1] Write the matrix test in `packages/aoa-action-machine/tests/action_machine/graph/validators/test_role_compatibility_matrix.py`: all 64 directed combinations produce exactly 22 acceptances and 42 refusals, and reversing each record keeps the verdict while retaining the endpoint roles and One/Many values (FR-024).
- [x] T009 [US1] Write the assembly test in `packages/aoa-action-machine/tests/action_machine/graph/validators/test_role_compatibility_assembly.py`: actual reciprocal declarations through `NodeGraphCoordinator.build()` for every permitted family and every prohibited family, using valid fixtures that reach the role-pair check rather than failing on a missing marker, unresolved type or absent reverse endpoint (FR-025). Include the adversarial mutations: admit an ownership/ownership pair, and reject a permitted Many pair, each failing while a valid neighbouring control passes (FR-027).
- [x] T010 [P] [US1] Write the cross-module test in `packages/aoa-action-machine/tests/action_machine/graph/validators/test_role_compatibility_cross_module.py`: two related classes in separate modules, imported in both orders, with forward annotations resolved in a composition root; field-only `Inverse(field_name=...)` and concrete `Inverse(Target, "...")` receive equivalent checks, a supplied concrete target that differs from the resolved target fails, and the pair assembles without circular imports (FR-009, FR-026).
- [x] T011 [P] [US1] Write the no-bypass test in `packages/aoa-action-machine/tests/action_machine/graph/validators/test_role_compatibility_bypass.py`: graph exclusion, `NoGraphEdge`, hidden edges, inherited fields, overrides and delayed type resolution must not bypass the compatibility check, and inherited endpoints are compared by resolved endpoint identity, never by matching short class names (FR-009, FR-026).

**Checkpoint**: US1 is independently testable — the matrix blocks invalid models before publication and cannot be bypassed.

---

## Phase 4: User Story 2 - Declare every relationship completely, reciprocal or intentionally one-way (Priority: P1)

**Goal**: The reciprocal-versus-unpaired contract is exact: `NoInverse` is permitted on the six ordinary containers and refused on `Specialization`/`Generalization`; two `NoInverse` fields are independent, and an `Inverse` cannot target a `NoInverse` field.

**Independent Test**: Assemble the four declaration shapes of the NoInverse table and confirm each required result.

### Implementation for User Story 2

- [x] T012 [US2] Verify and, where missing, add coverage that `NoInverse` is accepted on each of the six ordinary containers (`AssociationOne`, `AssociationMany`, `AggregateOne`, `AggregateMany`, `CompositeOne`, `CompositeMany`) in `packages/aoa-action-machine/src/aoa/action_machine/graph/validators/entity_field_validator.py` — the field still requires the complete `Annotated` declaration, a description, a resolved target and a valid value.
- [x] T013 [US2] Refuse `NoInverse` on `Specialization` and on `Generalization` (extend `entity_specialization_validator.py` if it does not already refuse it): these roles require a reciprocal `Specialization`/`Generalization` pair with `Inverse` on both endpoints.

### Tests for User Story 2

- [x] T014 [US2] Write the NoInverse table test in `packages/aoa-action-machine/tests/action_machine/graph/validators/test_role_compatibility_noinverse.py`: one unpaired `NoInverse` field accepted; two mutually resolving `Inverse` markers accepted; an `Inverse` targeting a `NoInverse` field refused in both inspection orders; two `NoInverse` fields (even referring to each other's entity types) accepted as two independent relationships with no inverse metadata; `NoInverse` on `Specialization` and on `Generalization` refused with a valid reciprocal control (FR-026).

**Checkpoint**: US2 is independently testable — the one-way/reciprocal contract is exact.

---

## Phase 5: User Story 3 - Pair specialization and generalization exclusively (Priority: P1)

**Goal**: A paired inheritance relationship has exactly one `Specialization` and one `Generalization`; neither pairs with an ordinary role, and same-role pairs are refused — while classifier/alternative semantics stay intact.

**Independent Test**: Assemble a valid classified axis, then `Specialization`/`Specialization`, `Generalization`/`Generalization`, and each spec/gen endpoint paired with an ordinary role, with otherwise valid declarations.

### Implementation for User Story 3

- [x] T015 [US3] In `entity_role_compatibility_validator.py`, apply the matrix to spec/gen endpoints: `Specialization ↔ Generalization` is allowed; `Specialization`/`Specialization`, `Generalization`/`Generalization`, and either endpoint paired with any of the six ordinary roles is refused (FR-004). Do not duplicate the classifier/alternative/closure/cycle checks that `entity_specialization_validator.py` already performs.

### Tests for User Story 3

- [x] T016 [US3] Write the specialization test in `packages/aoa-action-machine/tests/action_machine/graph/validators/test_role_compatibility_specialization.py`: a complete valid classified axis passes (classifier/alternative intact); `Specialization`/`Specialization` and `Generalization`/`Generalization` refuse; each spec/gen endpoint paired with an ordinary role refuses with the "pair exclusively" message. Include the adversarial mutation: admit an invalid specialized pair, failing while a valid control passes (FR-027).

**Checkpoint**: US3 is independently testable — the inheritance axis pairs exclusively.

---

## Phase 6: User Story 4 - Read a refusal that names both endpoints and the fix (Priority: P2)

**Goal**: One consistent public exception, exact text, and an accurate failure boundary; newly refused ownership/ownership pairs are shown as a migration, never silently rewritten.

**Independent Test**: Trigger each refusal family and read the message; confirm it names both owners and fields, both roles, the rule and the correction.

### Implementation for User Story 4

- [x] T017 [US4] Finalize the `RoleCompatibilityError` message per rule in `packages/.../domain/exceptions.py`: an ownership/ownership refusal says both endpoints carry ownership roles and the reverse of an ownership endpoint must be `AssociationOne`/`AssociationMany` (never "all Many relationships are prohibited"); a specialization/ordinary-role refusal says `Specialization` and `Generalization` pair exclusively with each other; the ownership/ownership refusal names which endpoint to change to `AssociationOne`/`AssociationMany` according to the intended domain meaning (FR-013, FR-014, FR-015).

### Tests for User Story 4

- [x] T018 [US4] Write the diagnostics test in `packages/aoa-action-machine/tests/action_machine/graph/validators/test_role_compatibility_diagnostics.py`: pin the exact exception type, text and failure boundary for each refusal family, and confirm an earlier declaration check (missing marker, unresolved type, absent reverse endpoint) fires first and is reported accurately.
- [x] T019 [US4] Write the adversarial regression suite in `packages/aoa-action-machine/tests/action_machine/graph/test_role_compatibility_adversarial.py` covering the three matrix mutations of FR-027 (admit an ownership/ownership pair, admit an invalid specialized pair, reject a permitted Many pair); the two dictionary mutations (restore `AssociationOne`-only dictionary acceptance, bypass member validation) are covered by T025. Each mutation is caught by its targeted check while its valid neighbouring control passes.

**Checkpoint**: US4 is independently testable — every refusal is actionable and its boundary is pinned.

---

## Phase 7: User Story 5 - Use all six ordinary containers for dictionary targets (Priority: P2)

**Goal**: Dictionary targets accept every ordinary container under the general rules; to-one and to-many values resolve, invalid values are refused, and transport/graph export preserve the declaration.

**Independent Test**: For each of the six ordinary containers with a dictionary target, exercise to-one/to-many values, empty/nullable cases, input/export in both schema modes, and graph projection.

### Implementation for User Story 5

- [x] T020 [US5] Remove the dictionary `AssociationOne`-only rule in `packages/aoa-action-machine/src/aoa/action_machine/graph/validators/entity_field_validator.py`: rewrite `_dictionary_container_refusal`, `_dictionary_inverse_refusal` and the `if resolved.container is not AssociationOne` branch so any of the six ordinary containers is a legal dictionary relationship under the general full-declaration and endpoint-pair rules (FR-016); update the module header and the refusal text that names `AssociationOne[...] | None, NoInverse()`.
- [x] T021 [US5] Ensure to-one dictionary resolution works for all six containers: an identifier resolves to the canonical declared member; unknown, blank or incorrectly typed codes and foreign, fabricated or mismatched supplied members are refused with item paths (FR-017), in `packages/aoa-action-machine/src/aoa/action_machine/domain/relation_containers.py`.
- [x] T022 [US5] Implement to-many dictionary value resolution in `packages/aoa-action-machine/src/aoa/action_machine/domain/relation_containers.py`: resolve every identifier in input order, retain the declared container class, normalize into an immutable container without mutating the caller's input, and specify empty selection, explicit absence, omission and loaded/unloaded states distinctly (FR-017, FR-018).
- [x] T023 [US5] Implement the dictionary transport and export contract: preserve the to-one transport contract and add the equivalent to-many input/export form and both schema modes; retain custom property serializers and typed exported-property schemas; add no unsupported uniqueness or cardinality restriction (FR-018, `contracts/dictionary-transport.md`).
- [x] T024 [US5] Preserve graph projection in `packages/aoa-action-machine/src/aoa/action_machine/graph/` (nodes/edges for dictionary references): keep the declared role family, cardinality, endpoint direction, description and dictionary hint; do not force a dictionary relationship into association/one and do not emit duplicate relationship arrows; preserve historical graph import support independently of the source declaration rule (FR-019).

### Tests for User Story 5

- [x] T025 [US5] Write the dictionary test in `packages/aoa-action-machine/tests/action_machine/graph/validators/test_role_compatibility_dictionary.py`: all six ordinary dictionary containers across runtime values, empty/nullable cases, input/export in both schema modes, graph projection, canonical identity and invalid-code refusals (FR-026). Include the adversarial mutations: restore `AssociationOne`-only dictionary acceptance, and bypass member validation, each failing while a valid control passes (FR-027).

**Checkpoint**: US5 is independently testable — dictionaries use the full six-container surface.

---

## Phase 8: User Story 7 - Run the teaching scenarios and their notebooks (Priority: P3)

**Goal**: Five coherent topics teach the matrix through numbered scripts with matching notebooks, executed in fresh processes.

**Independent Test**: Execute each script and notebook in a fresh process; confirm they complete with real output and that script/notebook results agree.

> **Note**: US6 (reference documentation) is delivered by the C2 tail task T033, not here — the constitution VI reserves the documentation for the tail, after the code settles (FR-028).

### Implementation for User Story 7

- [x] T026 [P] [US7] Write scenario 1 — plain associations (`AssociationOne`/`AssociationOne`, `AssociationOne`/`AssociationMany`, `AssociationMany`/`AssociationMany`, with each field's cardinality explained) as `examples/step_21_relations/68_role_plain_associations.py` + matching `.ipynb`, with a `main`, clear assertions and real output.
- [x] T027 [P] [US7] Write scenario 2 — aggregation (`AggregateOne`/`AssociationMany`, `AggregateMany`/`AssociationOne`, a refused aggregate/aggregate pair and its corrected reverse association) as `examples/step_21_relations/69_role_aggregation.py` + `.ipynb`.
- [x] T028 [P] [US7] Write scenario 3 — composition (`CompositeMany`/`AssociationOne`, `CompositeOne`/`AssociationMany`, refused composite/composite and composite/aggregate pairs and corrected alternatives) as `examples/step_21_relations/70_role_composition.py` + `.ipynb`.
- [x] T029 [P] [US7] Write scenario 4 — specialization/generalization (a complete valid classified axis and representative same-role and ordinary-role mismatch refusals with otherwise valid declarations) as `examples/step_21_relations/71_role_specialization.py` + `.ipynb`.
- [x] T030 [P] [US7] Write scenario 5 — dictionary endpoints (complete to-one and to-many selections across the ordinary relation families, canonical identity, invalid values, transport, graph kind/cardinality, permitted reciprocal roles) as `examples/step_21_relations/72_role_dictionary.py` + `.ipynb`.
- [x] T031 [US7] Execute each scenario in a fresh process (FR-022), confirm script and notebook results agree and notebooks retain actual outputs and execution counts, copy documentation code into clean files and execute it, and check local links and section anchors (FR-023).

**Checkpoint**: US7 is independently testable — every teaching topic runs and agrees with its notebook.

---

## Phase 9: Polish & Cross-Cutting Concerns (the reserved tail)

**Purpose**: The three closing steps of constitution VI, in order, and no story may absorb them (FR-028).

- [x] T032 **C1 — The check run, taken to zero.** Run `bash scripts/run_checks_with_log.sh`, fix every remark it reports (including the demo package, Ruff/mypy/pylint/vulture/Radon and the packaging smoke), and leave the run green with only the two accepted third-party remarks the constitution names.
- [x] T033 **C2 — The documentation.** After the code settles, update the public relationship reference with the eight role definitions, the symmetric 8×8 matrix and the 12 permitted combinations, the three rules, the NoInverse table, the failure boundary and migration, and the dictionary rules (FR-020); update affected how-to pages and tutorials, removing the former dictionary single-selection-only rule and the former claim that all ownership/ownership pairs are permitted (FR-021); keep historical changelog entries identifiable as historical. Every case appears as a script and a notebook, every example is executed with its output recorded, local links and anchors are checked, and a Russian draft sits beside each page written (drafts stay outside the commit).
- [x] T034 **C3 — The changelog, one article.** Write `docs/CHANGELOG.md` as a single readable piece about what the work created — the matrix, the refused families, the dictionary change — in plain words with the nuances a user has to know, and no per-file account.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup; BLOCKS US1, US3 and US4 (they all consume the matrix/exception).
- **User Stories (Phases 3–8)**: Depend on Foundational. US1 is the MVP. US2, US3, US4, US5 and US7 are independent of each other once Foundational is done (US5 also depends on the field-validator refactor only, not on the other stories).
- **Polish (Phase 9)**: Depends on all desired stories being complete.

### User Story Dependencies

- **US1 (P1)**: after Foundational; no other story dependency. 🎯 MVP.
- **US2 (P1)**: after Foundational; independent.
- **US3 (P1)**: after Foundational; independent (shares the validator with US1).
- **US4 (P2)**: after Foundational and US1/US3 (it pins the refusal messages those stories raise).
- **US5 (P2)**: after Foundational; independent (dictionary refactor + values + transport).
- **US6 (P2)**: delivered by C2 (T033) in the tail — see the note in Phase 8.
- **US7 (P3)**: after US1/US3/US5 settle (the scenarios must reflect the finished rules), but the scripts are separate files and parallel among themselves.

### Within Each User Story

- Tests (included per FR-024…FR-027) are written to fail before the corresponding implementation lands where practical.
- Implementation before wiring; wiring before assembly tests; story complete before the next priority.

### Parallel Opportunities

- Foundational T002 and T003 are different files and can run in parallel.
- US1 tests T008/T010/T011 are separate files and can run in parallel once T005–T007 exist; T009 follows T005–T007.
- US7 scenarios T026–T030 are separate files and can all run in parallel; T031 follows them.
- US2, US3, US5 are independent of each other after Foundational and can run in parallel (US4 after them).

---

## Parallel Example: User Story 7

```bash
# Launch the five teaching scenarios together (separate files):
Task: "Write scenario 1 ... examples/step_21_relations/68_role_plain_associations.py + .ipynb"
Task: "Write scenario 2 ... examples/step_21_relations/69_role_aggregation.py + .ipynb"
Task: "Write scenario 3 ... examples/step_21_relations/70_role_composition.py + .ipynb"
Task: "Write scenario 4 ... examples/step_21_relations/71_role_specialization.py + .ipynb"
Task: "Write scenario 5 ... examples/step_21_relations/72_role_dictionary.py + .ipynb"
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Complete Phase 1 (Setup) and Phase 2 (Foundational).
2. Complete Phase 3 (US1): the matrix validator, the two wirings, and the 64-combination + assembly tests.
3. **STOP and VALIDATE**: run `uv run --extra dev pytest packages/aoa-action-machine/tests/action_machine/graph/validators -q` and confirm the matrix blocks invalid models before publication.

### Incremental Delivery

1. Setup + Foundational → matrix, exception and role mapping ready.
2. Add US1 → the matrix is enforced before publication (MVP).
3. Add US2, US3, US4 → the NoInverse contract, specialization exclusivity and actionable diagnostics.
4. Add US5 → dictionaries use the full six-container surface.
5. Add US7 → the five teaching scenarios and notebooks.
6. Polish → C1 check run, C2 documentation (incl. US6), C3 changelog.

### Parallel Team Strategy

- Developer A: US1 (matrix enforcement) + US3 (specialization) — same validator file, sequential within.
- Developer B: US5 (dictionary targets) — independent files.
- Developer C: US2 (NoInverse) then US4 (diagnostics) — US4 depends on US1/US3.
- Developer D: US7 scenarios after the rules settle.

---

## Notes

- [P] tasks are different files with no dependency on each other.
- The exception type is `RoleCompatibilityError` — one new public type, the maintainer's confirmed answer to the clarification question. No existing exception type is removed; only the removed dictionary `AssociationOne`-only refusal helpers are deleted with their rule (verified by the vulture dead-code check in C1).
- Every task names its exact file path; descriptions quote the FR constraints they implement.
- Commit after each task or logical group only on the maintainer's explicit instruction (constitution I).
