# Tasks: Entity kinds — one base class per kind, and the kind in the name

**Input**: Design documents from `specs/013-entity-type-markers/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), `contracts/`, [quickstart.md](./quickstart.md)

**Tests**: requested — the specification requires every refusal to be measured by a test (SC-004), and `AGENTS.md` requires adversarial proof (break the code, watch the one test fail, restore).

**Organization**: tasks are grouped by the user story they deliver. One story's second half is scheduled after another story's migration — the reason is stated in Dependencies, and the branch order is the plan's phase table.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: the user story the task delivers (US1–US4)
- Every task names the file it writes

## Path Conventions

Repository root is `/Users/bystrovmaxim/PythonDev/aoa`. Framework code lives in `packages/aoa-action-machine/src/aoa/action_machine/`, its tests in `packages/aoa-action-machine/tests/action_machine/`, the store in `packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/resources/`, the corpus in `packages/aoa-demo/src/aoa/demo/model/`, `examples/` and the packages' `tests/`, and the evidence for this feature in `specs/013-entity-type-markers/evidence/`.

---

## Phase 1: Setup

- [x] T001 Confirm the branch and the environment: `git status` shows `feature/issue-210-entity-type-markers`, then `uv sync --extra dev` completes and `uv run --extra dev pytest packages/aoa-action-machine/tests -q --co` collects (the tree is green before anything changes)
- [x] T002 Re-run `specs/013-entity-type-markers/evidence/scan_entity_classes.py` and confirm it still matches the committed `evidence/scan.before.txt` (476 / 470 / 6 / 63 / 539 / 63 / 476) — the evidence every count in the plan rests on is current

---

## Phase 2: Foundational — the base recognises a kind base class

**Purpose**: the rule that makes a kind base class abstract without any attribute or registry.

**⚠️ CRITICAL**: no user story can start before this phase is complete.

- [x] T003 Extend `packages/aoa-action-machine/src/aoa/action_machine/domain/entity.py`: a class that inherits `BaseEntity` directly **and** defines `__init_subclass__` in its own body is a kind base class — `cls.__new__ = staticmethod(_refuse_kind_base_instantiation)`, where the guard raises `TypeError("<Name> is the base class of a kind and cannot be instantiated.")` for such a class and lets its descendants construct. No enum, no registry and no class attribute are introduced; the exclusion is the ordinary `@exclude_graph_model` the six classes carry (`FR-002`, `FR-008`)
- [x] T004 Write `packages/aoa-action-machine/tests/action_machine/domain/test_entity_kind.py` — a kind base class is not constructible, is excluded from the model graph, and its descendant is neither (`SC-006`)

**Checkpoint**: the base can tell a kind base class from a real entity, using only the class's shape.

---

## Phase 3: User Story 1 — a declaration says what kind of thing it is (P1) 🎯 MVP

**Goal**: six kind base classes, one file each, each deriving its suffix from its own name and holding its descendants to it.

**Independent Test**: declare one entity per kind, import the module, and confirm all six exist with exactly one kind in the chain, a name carrying that kind, and a base class that cannot be constructed (quickstart §1 and §2).

- [x] T005 [P] [US1] Write `packages/aoa-action-machine/src/aoa/action_machine/domain/core_entity.py`, `assoc_entity.py`, `detail_entity.py`, `spec_entity.py`, `enum_entity.py` — one file per kind, each with the module header, `class BaseXxxEntity(BaseEntity, ABC)`, the AI-CORE block from the issue §2, and its own `__init_subclass__`, whose whole body is `super()._require_kind_suffix("XxxEntity")` — the check lives once on `BaseEntity`, the kind's suffix is passed as a literal, and a `NamingSuffixError` names the class and the suffix when a descendant's name does not end with it; the class carries `@exclude_graph_model` itself (`FR-001`, `FR-002`, `FR-003`, `FR-005`, `FR-006`)
- [x] T006 [P] [US1] Give the sixth kind the same shape in `packages/aoa-action-machine/src/aoa/action_machine/domain/state_entity.py` — the same `super()._require_kind_suffix("StateEntity")` call in its `__init_subclass__`, and the unchanged exclusion of every status type from the model graph (`FR-007`)
- [x] T007 [US1] Export the six kind base classes from `packages/aoa-action-machine/src/aoa/action_machine/domain/__init__.py` (`from … import`, `__all__`, the docstring's entity section) and extend the names the lazy-export test expects in `packages/aoa-action-machine/tests/action_machine/smoke/test_lazy_exports_coverage.py`
- [x] T008 [US1] Complete `packages/aoa-action-machine/tests/action_machine/domain/test_entity_kind.py` — parametrized over the six: `issubclass(base, BaseEntity)`, the derived word is the expected one, `base()` raises `TypeError`, `excluded_from_graph_model(base)` is true; for each kind a descendant with a missing suffix and one with a foreign suffix are refused with `NamingSuffixError`; a correctly named descendant constructs; an intermediate abstract descendant is accepted and held to the suffix; one kind base class beside an ordinary mixin is accepted; a class carrying a kind and no `@entity` is accepted (`FR-003`–`FR-009`, `SC-004`)
- [x] T009 [US1] Pin the declarations in the same module: scan `packages/` with `ast` and assert that exactly six classes inherit the entity base directly and override `__init_subclass__` (`SC-010`)
- [x] T010 [US1] Run every package suite and a demo graph build — no kind base class appears as an `Entity` row, and no behaviour of the existing corpus changes (`SC-006`, `SC-009`)

**Checkpoint**: US1 is deliverable on its own. The kind is not yet on the wire, and the hierarchy refusals are still off.

---

## Phase 4: User Story 3 — the corpus says what it means (P3)

**Goal**: all 476 classes carry one kind base class chosen by meaning, are renamed with their kind, and nothing else about them changed.

**Independent Test**: the scan reports 0 classes directly on the base except the six and 0 names without a kind suffix; `compare_baselines.py` reports 476 compared and 0 with a changed field set (quickstart §4 and §5).

**⚠️ This phase precedes the rest of US1 and all of US2 on purpose** — the hierarchy refusal fails at class creation, so the corpus must move first (plan phase table; `research.md` D4, D9).

- [x] T011 [US3] Write the decision table as data in `specs/013-entity-type-markers/evidence/entity_kind_map.py` — for each of the 476 classes: module, old name, kind, new name, one-line reason ("represents …"); apply the default rule from `research.md` D8 (`Generalization[` → spec, `Composite*` target → detail, only participant/service fields → assoc, code-like dictionary → enum, else core) and record every override with its reason
- [x] T012 [US3] Render the table for review as `specs/013-entity-type-markers/entity-kind-map.md`, grouped by module, with counts per kind; **stop here and show it** — no rename may be written before the maintainer has read the 476 rows (spec FR-010)
- [x] T013 [US3] Write `specs/013-entity-type-markers/evidence/migrate_entity_kinds.py` — the AST codemod: build the symbol table from `entity_kind_map.py`, rename local class definitions, resolve imported names per module, rename annotations and `Inverse(...)`/`Composite*[...]`/`Specialization[...]` references, rewrite the base class to the kind base class, refuse on a same-module collision (three `DummyEntity`, two `ChildEntity`), and print a per-file count of changes
- [x] T014 [US3] Write `specs/013-entity-type-markers/evidence/compare_baselines.py` and take `baseline.before.json` (`FR-011`) — per class: module, name, model field names, relation field names with relation type, lifecycle field names, `@entity` description, domain name; the comparison reports changed/missing/added classes and classes whose field set moved
- [x] T015 [P] [US3] Migrate the framework's fixtures (`FR-012`): run the codemod over `packages/aoa-action-machine/tests/` (114 classes, including `packages/aoa-action-machine/tests/support/domain_model/entities.py`), keeping the three deliberately undeclared fixtures undecorated
- [x] T016 [P] [US3] Migrate the demo (`FR-012`): run the codemod over `packages/aoa-demo/src/aoa/demo/model/` (209 classes in 17 bounded contexts)
- [x] T017 [P] [US3] Migrate the examples (`FR-012`): run the codemod over `examples/` (145 classes in 43 scripts), then re-execute the 43 notebooks beside their scripts and regenerate `examples/step_21_relations/02_specialization_erd.{dot,json,svg}` by running its script
- [x] T018 [P] [US3] Migrate the remaining packages (`FR-012`): `packages/aoa-ocel` (2 in `src`, 3 in `tests`), `packages/aoa-maxitor` (1 in `src`), `packages/aoa-fastapi-adapter` (1 test), `packages/aoa-mcp-adapter` (1 test)
- [x] T019 [US3] Update the string references the codemod cannot resolve (`FR-013`): 25 quoted class names and 2 dotted entity ids in `packages/*/tests/`; the 21 current-state markdown pages (including `README.md` and its `README.ru_draft.md`) and the one TypeScript check script `packages/aoa-maxitor/client/scripts/check-erd-card-containment.ts`. The 25 **historical** files — `docs/CHANGELOG.md`, the package changelogs, the earlier `specs/` — are not touched
- [x] T020 [US3] Take `specs/013-entity-type-markers/evidence/baseline.after.json` (`FR-011`, `SC-005`) and run `compare_baselines.py` — the result must be "476 compared, 0 with a changed field/relation/lifecycle set"; break one class on purpose in a scratch copy to see the comparison fail, then restore
- [x] T021 [US3] Run `scan_entity_classes.py` again and record `specs/013-entity-type-markers/evidence/scan.after.txt` — 0 old names in `packages/` and `examples/`, 0 classes on a kind base class without a kind suffix
- [x] T022 [US3] Run the full suite of every package and all 43 example scripts (quickstart §6) — no failure (`SC-009`); the demo's graph keeps its entity, field, relation and lifecycle counts

**Checkpoint**: the corpus speaks the six kinds; the refusals are still off, so the branch is green.

---

## Phase 5: The kind on the wire — User Story 1, second half (P1)

**Goal**: every entity row of the interchange graph states its kind, and the store keeps it.

**Independent Test**: build a graph over a probe entity and read `node.to_dict()["properties"]`; then round-trip the row through the Maxitor store (quickstart §3).

**⚠️ Scheduled after the migration** — a row cannot state a kind for a class whose base class does not exist, and the schema key is required.

- [x] T023 [US1] Emit the kind in the row (`FR-016`): `packages/aoa-action-machine/src/aoa/action_machine/graph/nodes/entity_graph_node.py` sets `properties={"description": description, "entity_kind": <word derived from the kind base class name>}`, refusing a class with no kind base class rather than emitting a row without a kind; its AI-CORE `CONTRACT` line names the property
- [x] T024 [US1] Tighten the schema (`FR-016`) in `packages/aoa-action-machine/src/aoa/action_machine/graph/graph_json_schema.py`: the `Entity` row's `properties` requires `["description", "entity_kind"]`, admits `entity_kind` as `{"type": "string", "enum": ["core", "assoc", "detail", "spec", "enum", "state"]}`, keeps `additionalProperties: false`
- [x] T025 [US1] Test the row in `packages/aoa-action-machine/tests/action_machine/graph/test_entity_field_graph.py` — the row's `properties` equals `{"description": …, "entity_kind": "core"}`, and `jsonschema` rejects a copy of that row with `entity_kind` deleted (`SC-007`)
- [x] T026 [US1] Extend the Maxitor store in `packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/resources/duckdb_graph_resource.py`: `entity` table gains `entity_kind VARCHAR NOT NULL`, `_fill_table_entity` inserts `p["entity_kind"]`, and the entity node payload builder adds `'entity_kind', entity_kind`
- [x] T027 [P] [US1] Update the hand-built entity rows in `packages/aoa-maxitor/tests/` (12 `{"type": "Entity", …}` literals in 6 modules plus 2 `type="Entity"` kwargs) so every row carries `"entity_kind"`, and add one assertion that a row without it fails validation
- [x] T028 [US1] Prove the round trip (`FR-016`, `SC-007`): in `packages/aoa-maxitor/tests/` assert that the kind the graph emits is the kind the store returns in the node payload

---

## Phase 6: User Story 2 — a misdeclaration is refused where it is written (P2)

**Goal**: the two hierarchy rules refuse at class creation, naming the class and what was found.

**Independent Test**: `pytest packages/aoa-action-machine/tests/action_machine/domain/test_entity_kind.py -v` — direct inheritance and two kind base classes are refused, every accepted shape imports, and each refusal test fails alone when its rule is removed (quickstart §2).

**⚠️ Scheduled after the migration** — this is the phase that switches the hierarchy rules on.

- [x] T029 [US2] Add the hierarchy rules to `BaseEntity.__init_subclass__` in `packages/aoa-action-machine/src/aoa/action_machine/domain/entity.py` — a class that inherits the base directly and is not a kind base class raises `DeclarationStructureError` telling the author to inherit one of the six; a class whose chain carries more than one kind base class raises `DeclarationStructureError` naming both (`FR-004`, `FR-008`)
- [x] T030 [US2] Extend `packages/aoa-action-machine/tests/action_machine/domain/test_entity_kind.py` with one test per refused shape (direct inheritance, two kind base classes) and one per accepted shape (intermediate abstract descendant, kind base class plus ordinary mixin, kind with no `@entity`, plain class with `@entity` and no entity base); each asserts the error type and the names the message carries (`FR-004`, `FR-009`, `SC-004`)
- [x] T031 [US2] Adversarial proof for both hierarchy rules: remove one rule at a time, confirm exactly its tests fail and no other, restore; list the observed failures in the phase report (`SC-004`)
- [x] T032 [US2] Run every package suite and all 43 example scripts again — the migrated corpus is accepted, nothing lawful is refused

**Checkpoint**: both rules are on and the tree is green; US1, US2 and US3 are all deliverable.

---

## Phase 7: The check run (constitution VI.1)

- [x] T033 Take the closing check run to zero (`FR-017`, `SC-011`): walk [quickstart.md](./quickstart.md) sections 1–6 by hand, then run `bash scripts/run_checks_with_log.sh` from the repository root and fix every remark it reports until it exits without errors. Only the two accepted remarks stay in the log (the Vite chunk-size advisory and LangGraph's `LangChainPendingDeprecationWarning`); whatever `ruff check --fix` changes is reviewed and kept or reverted. Three whole-tree proofs belong here: (a) the scan reports 0 classes directly on the base except the six, 0 classes on a kind base class without that kind's suffix, 0 old names (`SC-001`–`SC-003`, `SC-008`); (b) `compare_baselines.py` reports 476 compared and 0 with a changed field/relation/lifecycle set (`SC-005`); (c) the demo's built graph keeps its counts and every entity row carries `entity_kind` (`SC-006`, `SC-007`), and exactly six classes inherit the base directly and override the hook (`SC-010`)

---

## Phase 8: User Story 4 — the reader sees the kind, and the documentation says how (P4)

**Goal**: the reference and the tutorials teach the six kinds and both rules, each case runs as a script and as a notebook, and every page written here has its Russian draft beside it.

**Independent Test**: read the reference page and the tutorial as someone who has not seen the change; run the new example and confirm its printed output matches the notebook (quickstart §7 and §9).

**⚠️ This phase follows T033** — the constitution's tail is the check run, then the documentation, then the changelog.

- [ ] T034 [US4] Write the documentation of the change (`FR-014`), every case shown twice and every example executed while it is written. Its deliverables, in one pass:
  - `docs/reference/intents-and-invariants.md` — the six kinds with what each represents, its identity, its suffix and its wire word; both rules each with its refusal and error type; the declaration-invariants table updated; the `BaseStateEntity` section updated.
  - `docs/tutorials/step-20-entity.md` — the entity it teaches derives from a kind base class and is named with its kind; `docs/tutorials/step-21-relations.md` and `docs/how-to/specialization-declaration-fails.md` — the renamed classes.
  - `examples/step_28_entity_kinds/01_entity_kinds.py` — one named case per kind (what the instance represents, the class, the suffix, the wire word), one per refusal (the error type and the message it printed), the intermediate abstract descendant and the mixin accepted shapes; run it and keep the real output.
  - `examples/step_28_entity_kinds/01_entity_kinds.ipynb` — the same case cell by cell, with the output the script actually printed between the steps.
  - `docs/tutorials/step-28-entity-kinds.md` — prose around the new example: what a case is, why the framework answers as it does, and what changes if the author chooses a different kind.
  - The Russian drafts beside every page written or rewritten here — `docs/tutorials/step-28-entity-kinds.ru_draft.md`, `docs/reference/intents-and-invariants.ru_draft.md`, `docs/tutorials/step-20-entity.ru_draft.md` — reported as links and kept out of the commit.

---

## Phase 9: The changelog (constitution VI.3)

- [ ] T035 Write the changelog last (`FR-015`): one article at the top of `docs/CHANGELOG.md`, dated `2026-10-22`, in the form the existing dated entries use — what a reader can now rely on (an entity states what kind of thing it is; six kinds; the declaration is refused where it is written; the kind is in the graph row), with the nuances a user needs and no per-file account: a technical association may be omitted from the diagram as a separate node while the participants' connection stays; a relationship that has acquired its own process is no longer an association; an existing entity's old name is gone rather than aliased. Add the `[Unreleased]` entries beside it: `packages/aoa-action-machine/CHANGELOG.md` (six kind base classes, both rules, `properties.entity_kind`) and `packages/aoa-demo/CHANGELOG.md` (209 entities renamed, old names removed), both under *Breaking changes*. Then run [quickstart.md](./quickstart.md) sections 7–9 and the final diff pass: no module without its principle-III header, no new public symbol without a docstring and an AI-CORE block, no Russian in code or commit-facing text, no codemod scratch file outside `specs/013-entity-type-markers/evidence/`.

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)** — no dependency.
- **Foundational (Phase 2)** — after Setup; blocks every story.
- **US1 kind base classes (Phase 3)** — after Foundational. Independent of the corpus.
- **US3 (Phase 4)** — after US1: the migration needs the kind base classes to inherit from. Blocks the wire half and US2.
- **US1 wire (Phase 5)** — after US3: every class has a kind, so every row can state its kind and the schema can require it.
- **US2 (Phase 6)** — after US3 and the wire: the hierarchy refusals fail at class creation, so switching them on earlier would break every import.
- **Check run (Phase 7)** — after US2, and it is the first of the three tail steps.
- **US4 (Phase 8)** — after the check run: documentation follows the code.
- **Changelog (Phase 9)** — after the documentation: the last step of the change.

### Story dependencies

- **US1 (P1)**: no dependency beyond Foundational; its wire half waits for US3.
- **US2 (P2)**: depends on US3's migration. Its tests are written in its own phase and are the only proof the hierarchy rules exist.
- **US3 (P3)**: depends on US1 for the kind base classes and on the approved mapping table (T012) for the names.
- **US4 (P4)**: depends on US1, US2 and US3 — it documents what they deliver, with the names they produced.

### Within the migration

- T011 → T012 (decision table, then its review) → T013 (codemod) → T014 (baseline before)
- T014 → T015–T018 (the four areas can run in parallel: different trees) → T019 (strings the codemod cannot resolve) → T020 (baseline after and comparison) → T021 (scan) → T022 (suites and examples)

### Parallel opportunities

- T002 and T003 run with the environment check.
- T005 and T006 in US1: six different files.
- T007 is independent of the class bodies.
- T023 and T026 with the schema and the store work; T027 is independent of T026.
- T015, T016, T017, T018 — the four migration areas, different trees.

---

## Parallel Example: the four migration areas

```bash
# After T013 and T014, the codemod runs over four disjoint trees:
uv run python specs/013-entity-type-markers/evidence/migrate_entity_kinds.py --root packages/aoa-action-machine/tests
uv run python specs/013-entity-type-markers/evidence/migrate_entity_kinds.py --root packages/aoa-demo/src
uv run python specs/013-entity-type-markers/evidence/migrate_entity_kinds.py --root examples
uv run python specs/013-entity-type-markers/evidence/migrate_entity_kinds.py --root packages/aoa-ocel
```

## Independent test criteria per story

| Story | Proven on its own by |
| --- | --- |
| US1 | quickstart §1 (six kind base classes, none constructs, all excluded, the word from the name) and §3 (`entity_kind` in the row and through the store) |
| US2 | quickstart §2 — every refusal row of the declaration contract, plus the adversarial breaks of T031 |
| US3 | quickstart §4 and §5 — the scan after the migration and the baseline comparison |
| US4 | quickstart §7 and §9 — the new example prints what the notebook shows, and every kind and rule appears in the reference page |

## Implementation Strategy

### MVP first

Foundational + US1 kinds (T001–T010) is a deliverable, testable increment on its own: six kind base classes exist, each cannot be instantiated and each holds its descendants to its own name, and the corpus has not moved.

### Incremental delivery, in the only order that keeps the tree green

1. Foundational → US1 kinds: the six classes and their name rules.
2. Mapping table, then the corpus (US3): 476 classes, reviewed before renamed.
3. The wire (US1) and the hierarchy refusals (US2): every class already speaks a kind.
4. The tail: check run → documentation → changelog, three steps and no other.

### Stop points

- **After T012**: the maintainer reads the 476-row mapping. No rename is written before that.
- **After T022**: the corpus is done and the refusals are still off — the last moment they can be reconsidered without breaking imports.
- **After T033**: the check run is zero, and the documentation has not been written yet.

---

## Notes

- Every refusal carries its error type from `contracts/entity-kind-declaration-contract.md`: `DeclarationStructureError` for the hierarchy, `NamingSuffixError` for the name, `TypeError` for constructing a kind base class.
- The `entity_kind` constraint is quoted from `data-model.md`: required, one of `core`, `assoc`, `detail`, `spec`, `enum`, `state`, `additionalProperties: false`, `entity_kind VARCHAR NOT NULL` in the store; the word is the kind base class's name without `Base` and `Entity`, lower case.
- Verification is adversarial throughout: each rule, the schema, and the baseline comparison are broken on purpose once, observed to fail alone, and restored.
- The tail is exactly three tasks — T033, T034, T035 — in the constitution's order, and no other task absorbs them.
- Plan → tasks: plan phase 1 = Setup; phase 2 = T003–T004; phase 3 = T005–T010; phase 4 = T011–T014; phase 5 = T015–T022; phase 6 = T023–T032; phases 7–9 = T033, T034, T035.
- Commit after each phase, only on the maintainer's instruction (constitution I); one phase is one commit.
