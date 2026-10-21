# Tasks: Entity type markers — one base per kind, and the kind in the name

**Input**: Design documents from `specs/013-entity-type-markers/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), `contracts/`, [quickstart.md](./quickstart.md)

**Tests**: requested — the specification requires every refusal to be measured by a test (SC-004), and `AGENTS.md` requires adversarial proof (break the code, watch the one test fail, restore).

**Organization**: tasks are grouped by the user story they deliver. One story's enforcement is scheduled after another story's migration — the reason is stated in Dependencies, and the branch order is the plan's phase table.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: the user story the task delivers (US1–US4)
- Every task names the file it writes

## Path Conventions

Repository root is `/Users/bystrovmaxim/PythonDev/aoa`. Framework code lives in `packages/aoa-action-machine/src/aoa/action_machine/`, its tests in `packages/aoa-action-machine/tests/action_machine/`, the store in `packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/resources/`, the corpus in `packages/aoa-demo/src/aoa/demo/model/`, `examples/` and the packages' `tests/`, and the evidence for this feature in `specs/013-entity-type-markers/evidence/`.

---

## Phase 1: Setup

**Purpose**: the working environment and the scan every count in the specification rests on.

- [ ] T001 Confirm the branch and the environment: `git status` shows `feature/issue-210-entity-type-markers` from `origin/main`, then `uv sync --extra dev` completes and `uv run pytest packages/aoa-action-machine/tests -q --co` collects (the tree is green before anything changes)
- [ ] T002 Create `specs/013-entity-type-markers/evidence/` and write `specs/013-entity-type-markers/evidence/scan_entity_classes.py` — counts classes directly on `BaseEntity`, classes on a marker, kind-suffixed names, undecorated entities, old-name occurrences; prints the numbers quickstart §4 expects
- [ ] T003 [P] Run `scan_entity_classes.py` on the branch base and record the output as the before-numbers (476 directly on the base, 0 with a kind suffix, 470 decorated, 6 not, 63 on `BaseStateEntity`) in `specs/013-entity-type-markers/evidence/scan.before.txt`

---

## Phase 2: Foundational (blocking for every story)

**Purpose**: the vocabulary and the registration mechanism every later task reads.

**⚠️ CRITICAL**: no user story can start before this phase is complete.

- [ ] T004 Write `packages/aoa-action-machine/src/aoa/action_machine/domain/entity_kind.py` — module header per principle III; `class EntityKind(StrEnum)` with `CORE`, `ASSOC`, `DETAIL`, `SPEC`, `ENUM`, `STATE`; each member carries `suffix` (`"CoreEntity"` … `"StateEntity"`) and `word` (`"core"` … `"state"`) as properties; `register_marker(kind, cls)` refusing a second registration of one class, `kind_of(cls) -> EntityKind | None` walking the MRO nearest-first, `markers() -> tuple[type, ...]` in declaration order; one-line docstrings and an AI-CORE block on the module-level API
- [ ] T005 Write `packages/aoa-action-machine/src/aoa/action_machine/domain/entity_markers.py` — module header; `abstract_marker(kind)` decorator that registers the kind, applies `exclude_graph_model`, and installs a `__new__` on the marker that raises `TypeError("<Name> is an abstract marker and cannot be instantiated.")` when `cls` is the registered marker (the probe in `research.md` D1 proves the mechanism); AI-CORE block on `abstract_marker`
- [ ] T006 [P] Write `packages/aoa-action-machine/tests/action_machine/domain/test_entity_kind.py` — the six members' `suffix`/`word` pairs; `kind_of` on a registered marker, on its descendant and on an unrelated class; a duplicate registration refused; `markers()` order; every assertion one line with a docstring
- [ ] T007 [P] Register the existing marker: decorate `BaseStateEntity` in `packages/aoa-action-machine/src/aoa/action_machine/domain/state_entity.py` with `@abstract_marker(EntityKind.STATE)` (replacing `@exclude_graph_model`, whose effect the decorator now provides), keeping `code`, `display_name`, `_reject_blank` and the `__init_subclass__` exclusion unchanged

**Checkpoint**: `EntityKind` and the registration mechanism exist; every later story builds on them.

---

## Phase 3: User Story 1 — a declaration says what kind of thing it is (P1) 🎯 MVP

**Goal**: six markers exist with their roles, are abstract, are kept out of the model graph, and every entity row of the interchange graph carries its kind.

**Independent Test**: declare one entity per kind, build the graph, and confirm six entity rows appear with `properties.entity_kind` equal to their kind, no marker appears as an entity, and no marker can be instantiated (quickstart §1 and §3).

### Implementation for User Story 1

- [ ] T008 [P] [US1] Declare the five markers in `packages/aoa-action-machine/src/aoa/action_machine/domain/entity_markers.py` — `BaseCoreEntity`, `BaseAssocEntity`, `BaseDetailEntity`, `BaseSpecEntity`, `BaseEnumEntity`, each `class BaseXxxEntity(BaseEntity, ABC)` decorated with `@abstract_marker(EntityKind.XXX)`, each with the AI-CORE block (ROLE / CONTRACT / INVARIANTS) carrying the role, the identity and the forbidden shapes stated in the issue §2 (`FR-001`, `FR-002`)
- [ ] T009 [US1] Export the six markers and `EntityKind` from `packages/aoa-action-machine/src/aoa/action_machine/domain/__init__.py` (`from … import`, `__all__`, the module docstring's entity section) and extend the names the lazy-export test expects in `packages/aoa-action-machine/tests/action_machine/smoke/test_lazy_exports_coverage.py`
- [ ] T010 [P] [US1] Write `packages/aoa-action-machine/tests/action_machine/domain/test_entity_markers.py` — for each marker: `issubclass(marker, BaseEntity)` is true, `marker()` raises `TypeError`, `excluded_from_graph_model(marker)` is true, and a graph built from a probe model emits no marker as an `Entity` row (`FR-002`). The refusal of a marker as an `@entity` target belongs to T032, because the check it exercises does not exist until T029
- [ ] T011 [US1] Emit the kind in the row (`FR-016`): `packages/aoa-action-machine/src/aoa/action_machine/graph/nodes/entity_graph_node.py` sets `properties={"description": description, "entity_kind": kind_of(entity_cls).word}`, and its AI-CORE `CONTRACT` line names the property
- [ ] T012 [US1] Tighten the schema (`FR-016`) in `packages/aoa-action-machine/src/aoa/action_machine/graph/graph_json_schema.py`: the `Entity` row's `properties` requires `["description", "entity_kind"]`, admits `entity_kind` as `{"type": "string", "enum": ["core", "assoc", "detail", "spec", "enum", "state"]}`, keeps `additionalProperties: false`
- [ ] T013 [US1] Test the row in `packages/aoa-action-machine/tests/action_machine/graph/test_entity_field_graph.py` — the row's `properties` equals `{"description": …, "entity_kind": "core"}`, and `jsonschema` rejects a copy of that row with `entity_kind` deleted (proves the schema is not merely tolerant)
- [ ] T014 [US1] Extend the Maxitor store in `packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/resources/duckdb_graph_resource.py`: `entity` table gains `entity_kind VARCHAR NOT NULL`, `_fill_table_entity` inserts `p["entity_kind"]`, and the entity node payload builder adds `'entity_kind', entity_kind`
- [ ] T015 [P] [US1] Update the hand-built entity rows in `packages/aoa-maxitor/tests/` (12 `{"type": "Entity", …}` literals in 6 modules plus 2 `type="Entity"` kwargs) so every row carries `"entity_kind"`, and add one assertion that a row without it fails validation
- [ ] T016 [US1] Prove the round trip (`FR-016`, `SC-007`): in `packages/aoa-maxitor/tests/` assert that the kind the graph emits is the kind the store returns in the node payload (one test, named after the guarantee)

**Checkpoint**: US1 is deliverable and testable on its own — the six kinds exist, the marker cannot be instantiated, the graph and the store carry the kind.

---

## Phase 4: User Story 3 — the corpus says what it means (P3)

**Goal**: all 476 classes carry one marker chosen by meaning, are renamed with their kind, and nothing else about them changed.

**Independent Test**: `scan_entity_classes.py` reports 0 classes directly on the base except the six markers and 0 names without a kind suffix; `compare_baselines.py` reports 476 compared and 0 with a changed field set (quickstart §4 and §5).

**⚠️ This phase precedes US2 on purpose** — the refusal fails at class definition, so the corpus must move before the rule is switched on (plan phase table; `research.md` D9).

- [ ] T017 [US3] Write the decision table as data in `specs/013-entity-type-markers/evidence/entity_kind_map.py` — for each of the 476 classes: module, old name, kind, new name, one-line reason ("represents …"); apply the default rule from `research.md` D7 (`Generalization[` → spec, `Composite*` target → detail, only participant/service fields → assoc, code-like dictionary → enum, else core) and record every override with its reason
- [ ] T018 [US3] Render the table for review as `specs/013-entity-type-markers/entity-kind-map.md`, grouped by module, with counts per kind; **stop here and show it** — no rename may be written before the maintainer has read the 476 rows (spec FR-010)
- [ ] T019 [US3] Write `specs/013-entity-type-markers/evidence/migrate_entity_markers.py` — the AST codemod: build the symbol table from `entity_kind_map.py`, rename local class definitions, resolve imported names per module, rename annotations and `Inverse(...)`/`Composite*[...]`/`Specialization[...]` references, rewrite the base class to the marker, refuse on a same-module collision (three `DummyEntity`, two `ChildEntity`), and print a per-file count of changes
- [ ] T020 [US3] Write `specs/013-entity-type-markers/evidence/compare_baselines.py` and take `baseline.before.json` (`FR-011`) — per class: module, name, model field names, relation field names with relation type, lifecycle field names, `@entity` description, domain name; the comparison reports changed/missing/added classes and classes whose field set moved
- [ ] T021 [P] [US3] Migrate the framework's fixtures (`FR-012`): run the codemod over `packages/aoa-action-machine/tests/` (114 classes, including `packages/aoa-action-machine/tests/support/domain_model/entities.py`), keeping the three deliberately undeclared fixtures undecorated
- [ ] T022 [P] [US3] Migrate the demo (`FR-012`): run the codemod over `packages/aoa-demo/src/aoa/demo/model/` (209 classes in 17 bounded contexts)
- [ ] T023 [P] [US3] Migrate the examples (`FR-012`): run the codemod over `examples/` (145 classes in 43 scripts), then re-execute the 43 notebooks beside their scripts and regenerate `examples/step_21_relations/02_specialization_erd.{dot,json,svg}` by running its script
- [ ] T024 [P] [US3] Migrate the remaining packages (`FR-012`): `packages/aoa-ocel` (2 in `src`, 3 in `tests`), `packages/aoa-maxitor` (1 in `src`), `packages/aoa-fastapi-adapter` (1 test), `packages/aoa-mcp-adapter` (1 test)
- [ ] T025 [US3] Update the string references the codemod cannot resolve (`FR-013`): 25 quoted class names and 2 dotted entity ids in `packages/*/tests/`; the 21 current-state markdown pages (including `README.md` and its `README.ru_draft.md`) and the one TypeScript check script `packages/aoa-maxitor/client/scripts/check-erd-card-containment.ts` (`FR-013`). The 25 **historical** files — `docs/CHANGELOG.md`, the package changelogs, the earlier `specs/` — are not touched: they record the name that was true when they were written
- [ ] T026 [US3] Take `specs/013-entity-type-markers/evidence/baseline.after.json` (`FR-011`, `SC-005`) and run `compare_baselines.py` — the result must be "476 compared, 0 with a changed field/relation/lifecycle set"; break one class on purpose in a scratch copy to see the comparison fail, then restore
- [ ] T027 [US3] Run `scan_entity_classes.py` again and record `specs/013-entity-type-markers/evidence/scan.after.txt` — 0 old names in `packages/` and `examples/`, 539 classes on a marker, 539 with a kind suffix, 0 without
- [ ] T028 [US3] Run the full suite of every package and all 43 example scripts (quickstart §6) — no failure (`SC-009`); the demo's graph keeps its entity, field, relation and lifecycle counts

**Checkpoint**: the corpus speaks the six kinds; the rule is still off, so the branch is green.

---

## Phase 5: User Story 2 — a misdeclaration is refused where it is written (P2)

**Goal**: the three rules refuse at class definition, naming the class, what was found and the suffix expected.

**Independent Test**: `pytest packages/aoa-action-machine/tests/action_machine/domain/test_entity_markers.py -v` — every refusal row of the declaration contract passes, every accepted shape imports, and each refusal test fails alone when its check is removed (quickstart §2).

**⚠️ Scheduled after US3** — this is the phase that switches the rule on.

- [ ] T029 [US2] Add the structural refusals (`FR-003`, `FR-004`, `FR-008`) to `packages/aoa-action-machine/src/aoa/action_machine/intents/entity/entity_decorator.py`: after the target check, compute `kinds = [m for m in markers() if issubclass(cls, m)]`; raise `DeclarationStructureError` when `len(kinds) == 0` (naming the class, that no marker was found, and the six markers), when `len(kinds) > 1` (naming both), and when the target is itself a registered marker
- [ ] T030 [US2] Add the naming refusal to the same decorator (`FR-005`, `FR-008`): `cls.__name__.endswith(kind.suffix)` must hold, and a name ending with another kind's suffix is refused as the wrong kind — `NamingSuffixError`, message naming the class, the suffix found and the suffix the kind requires
- [ ] T031 [US2] Add the status suffix check (`FR-007`) to `BaseStateEntity.__init_subclass__` in `packages/aoa-action-machine/src/aoa/action_machine/domain/state_entity.py` — a descendant whose name does not end with `StateEntity` raises `NamingSuffixError`; the marker itself is exempt
- [ ] T032 [US2] Extend `packages/aoa-action-machine/tests/action_machine/domain/test_entity_markers.py` with one test per refused declaration (no marker, two markers, marker as `@entity` target, missing suffix, foreign suffix, status suffix) and one per accepted shape (intermediate abstract descendant, marker plus ordinary mixin, class on `BaseEntity` without `@entity`, a name that keeps the generic `…Entity` suffix); each test asserts the error type and the names the message carries (`FR-003`–`FR-008`, `FR-006`, `FR-009`, `SC-004`)
- [ ] T033 [US2] Invert the markerless case (`FR-009`) in `packages/aoa-action-machine/tests/action_machine/domain/test_entity.py` — replace `test_plain_class_without_base_entity_allowed` with a test that `@entity` on a plain class raises `DeclarationStructureError`, and delete the now-false claim from the module's docstring
- [ ] T034 [US2] Adversarial proof for every refusal: comment out one check at a time, confirm exactly its test fails and no other, restore; list the six observed failures, each with the test that failed, in the phase report (`SC-004`)
- [ ] T035 [US2] Run every package suite and all 43 example scripts again — the migrated corpus is accepted, nothing lawful is refused

**Checkpoint**: the rules are on and the tree is green; US1, US2 and US3 are all deliverable.

---

## Phase 6: The check run (constitution VI.1)

- [ ] T036 Take the closing check run to zero (`FR-017`, `SC-010`): walk [quickstart.md](./quickstart.md) sections 1–6 by hand, then run `bash scripts/run_checks_with_log.sh` from the repository root and fix every remark it reports until it exits without errors. Only the two accepted remarks stay in the log (the Vite chunk-size advisory and LangGraph's `LangChainPendingDeprecationWarning`); whatever `ruff check --fix` changes is reviewed and kept or reverted, never left unreviewed. Three whole-tree proofs belong here: (a) `specs/013-entity-type-markers/evidence/scan_entity_classes.py` reports 0 classes directly on the base except the six markers, 539 classes on a marker, 539 kind-suffixed names, 0 without, and 0 old names in `packages/` and `examples/` (`SC-001`, `SC-002`, `SC-003`, `SC-008`); (b) `compare_baselines.py` reports 476 compared and 0 with a changed field/relation/lifecycle set (`SC-005`); (c) the demo's built graph keeps its entity, field, relation and lifecycle counts and every entity row carries `entity_kind` (`SC-006`, `SC-007`).

---

## Phase 7: User Story 4 — the reader sees the kind, and the documentation says how (P4)

**Goal**: the reference and the tutorials teach the six kinds and the three rules, each case runs as a script and as a notebook, and every page written here has its Russian draft beside it.

**Independent Test**: read the reference page and the tutorial as someone who has not seen the change; run the new example and confirm its printed output matches the notebook (quickstart §7 and §9).

**⚠️ This phase follows T036** — the constitution's tail is the check run, then the documentation, then the changelog.

- [ ] T037 [US4] Write the documentation of the change (`FR-014`), every case shown twice and every example executed while it is written. Its deliverables, in one pass:
  - `docs/reference/intents-and-invariants.md` — the six kinds with what each represents, its identity, its suffix and its wire word; the three rules each with its refusal and error type; the declaration-invariants table row replaced; the `BaseStateEntity` section updated.
  - `docs/tutorials/step-20-entity.md` — the entity it teaches derives from a marker and is named with its kind; `docs/tutorials/step-21-relations.md` and `docs/how-to/specialization-declaration-fails.md` — the renamed classes.
  - `examples/step_28_entity_kinds/01_entity_kinds.py` — one named case per kind (what the instance represents, the class, the suffix, the wire word), one per refusal (the error type and the message it printed), the intermediate abstract descendant and the marker-plus-mixin accepted shapes; run it and keep the real output.
  - `examples/step_28_entity_kinds/01_entity_kinds.ipynb` — the same case cell by cell, with the output the script actually printed between the steps.
  - `docs/tutorials/step-28-entity-kinds.md` — prose around the new example: what a case is, why the framework answers as it does, and what changes if the author chooses a different kind.
  - The Russian drafts beside every page written or rewritten here — `docs/tutorials/step-28-entity-kinds.ru_draft.md`, `docs/reference/intents-and-invariants.ru_draft.md`, `docs/tutorials/step-20-entity.ru_draft.md` — reported as links and kept out of the commit (`*_draft.md` is ignored).

---

## Phase 8: The changelog (constitution VI.3)

- [ ] T038 Write the changelog last (`FR-015`): one article at the top of `docs/CHANGELOG.md`, dated `2026-10-22`, in the form the existing dated entries use — what a reader can now rely on (an entity states what kind of thing it is; six kinds; the declaration is refused where it is written; the kind is in the graph row), with the nuances a user needs and no per-file account: a technical association may be omitted from the diagram as a separate node while the participants' connection stays; a relationship that has acquired its own process is no longer an association; an existing entity's old name is gone rather than aliased. Add the `[Unreleased]` entries beside it: `packages/aoa-action-machine/CHANGELOG.md` (the six markers, the three refusals, `properties.entity_kind`) and `packages/aoa-demo/CHANGELOG.md` (209 entities renamed, old names removed), both under *Breaking changes*. Then run [quickstart.md](./quickstart.md) sections 7–9 and the final diff pass: no module without its principle-III header, no new public symbol without a docstring and an AI-CORE block, no Russian in code or commit-facing text, no codemod scratch file outside `specs/013-entity-type-markers/evidence/`.

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)** — no dependency.
- **Foundational (Phase 2)** — after Setup; blocks every story.
- **US1 (Phase 3)** — after Foundational. Independent of the corpus.
- **US3 (Phase 4)** — after US1: the migration needs the markers to inherit from. Blocks US2.
- **US2 (Phase 5)** — after US3: the refusal fails at class definition, so switching it on before the migration would break every import (`research.md` D9, plan Complexity Tracking).
- **Check run (Phase 6)** — after US2, and it is the first of the three tail steps.
- **US4 (Phase 7)** — after the check run: documentation follows the code, as constitution VI.2 requires.
- **Changelog (Phase 8)** — after the documentation: the last step of the change.

### Story dependencies

- **US1 (P1)**: no dependency beyond Foundational.
- **US2 (P2)**: depends on US3's migration. Its tests are written in its own phase and are the only proof the rules exist.
- **US3 (P3)**: depends on US1 for the markers and on the approved mapping table (T018) for the names.
- **US4 (P4)**: depends on US1, US2 and US3 — it documents what they deliver, with the names they produced.

### Within the migration

- T017 → T018 (decision table, then its review) → T019 (codemod) → T020 (baseline before)
- T020 → T021–T024 (the four areas can run in parallel: different files) → T025 (strings the codemod cannot resolve) → T026 (baseline after and comparison) → T027 (scan) → T028 (suites and examples)

### Parallel opportunities

- T002 and T003 run with the environment check.
- T006 and T007 in Foundational.
- T008 and T010 in US1; T013 and T015 with the schema and the store work; T015 is independent of T014.
- T021, T022, T023, T024 — the four migration areas, different trees.

---

## Parallel Example: the four migration areas

```bash
# After T019 and T020, the codemod runs over four disjoint trees:
uv run python specs/013-entity-type-markers/evidence/migrate_entity_markers.py --root packages/aoa-action-machine/tests
uv run python specs/013-entity-type-markers/evidence/migrate_entity_markers.py --root packages/aoa-demo/src
uv run python specs/013-entity-type-markers/evidence/migrate_entity_markers.py --root examples
uv run python specs/013-entity-type-markers/evidence/migrate_entity_markers.py --root packages/aoa-ocel
```

## Independent test criteria per story

| Story | Proven on its own by |
| --- | --- |
| US1 | quickstart §1 (six markers, none constructs, all excluded) and §3 (`entity_kind` in the row and through the store) |
| US2 | quickstart §2 — every refusal row of the declaration contract, plus the six adversarial breaks of T034 |
| US3 | quickstart §4 and §5 — the scan after the migration and the baseline comparison |
| US4 | quickstart §7 and §9 — the new example prints what the notebook shows, and every kind and refusal appears in the reference page |

## Implementation Strategy

### MVP first

Foundational + US1 (T001–T016) is a deliverable, testable increment on its own: six kinds exist, the marker cannot be instantiated, the graph and the store carry the kind, and the corpus has not moved. Everything else builds on it.

### Incremental delivery, in the only order that keeps the tree green

1. Foundational → US1: the vocabulary and the kind on the wire.
2. Mapping table, then the corpus (US3): 476 classes, reviewed before renamed.
3. US2: switch the rule on; the corpus already speaks the kinds.
4. The tail: check run → documentation → changelog, three steps and no other.

### Stop points

- **After T018**: the maintainer reads the 476-row mapping. No rename is written before that.
- **After T028**: the corpus is done and the rule is still off — the last moment the rule can be reconsidered without breaking imports.
- **After T036**: the check run is zero, and the documentation has not been written yet (constitution VI.2 follows VI.1).

---

## Notes

- Every refusal task carries its error type from `contracts/entity-kind-declaration-contract.md`: `DeclarationStructureError` for structure, `NamingSuffixError` for the name, `TypeError` from the marker guard.
- The `entity_kind` constraint is quoted from `data-model.md`: required, one of `core`, `assoc`, `detail`, `spec`, `enum`, `state`, `additionalProperties: false`, `entity_kind VARCHAR NOT NULL` in the store.
- Verification is adversarial throughout: each refusal, the schema, and the baseline comparison are broken on purpose once, observed to fail alone, and restored.
- The tail is exactly three tasks — T036, T037, T038 — in the constitution's order, and no other task absorbs them.
- Plan → tasks: plan phase 1 (markers, registry) = Foundational + US1; plan phase 2 (the kind on the wire) = US1 T011–T016; plan phase 3 (mapping) = US3 T017–T020; plan phases 4–7 (migration) = US3 T021–T028; plan phase 8 (the rule on) = US2; plan phases 9–11 (check run, documentation, changelog) = T036, T037, T038.
- Commit after each phase, only on the maintainer's instruction (constitution I); one phase is one commit.
