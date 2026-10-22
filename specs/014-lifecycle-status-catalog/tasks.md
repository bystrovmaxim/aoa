# Tasks: Lifecycle statuses live on the state type, and the axis checks its whole vocabulary

**Input**: Design documents from `specs/014-lifecycle-status-catalog/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), `contracts/`, [quickstart.md](./quickstart.md)

**Tests**: requested — the specification requires both refusals and every field error to be measured by a test (SC-003, SC-004), the plan requires adversarial proof, and `AGENTS.md` requires breaking the code the test must catch.

**Organization**: tasks are grouped by the user story they deliver. US1 is the declaration surface and the catalogue; US3 migrates the corpus; US2 then turns the refusals on. US2 is P1 but follows US3 on purpose: the generic axis is only green once every axis already names its type (plan phase table; `research.md` D3, D4).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: the user story the task delivers (US1–US4)
- Every task names the file it writes

## Path Conventions

Repository root is `/Users/bystrovmaxim/PythonDev/aoa`. Framework code lives in `packages/aoa-action-machine/src/aoa/action_machine/`, its tests in `packages/aoa-action-machine/tests/action_machine/`, the corpus in `packages/aoa-demo/src/aoa/demo/model/`, `examples/` and the packages' `tests/`, and the evidence for this feature in `specs/014-lifecycle-status-catalog/evidence/`.

---

## Phase 1: Setup

- [ ] T001 Confirm the branch and the environment: `git status` shows `feature/issue-237-state-catalog-and-lifecycle-checks`, `uv sync --extra dev` completes, `uv run --extra dev pytest packages/aoa-action-machine/tests -q --co` collects, and `uv run --extra dev mypy packages/` is clean before anything changes
- [ ] T002 Write `specs/014-lifecycle-status-catalog/evidence/scan_lifecycle_catalog.py` and run it: walk `packages/aoa-demo/src`, `examples/` and every package, parse the modules with `ast`, find the `(Lifecycle, StateVocabulary)` axes and the `BaseStateEntity` subclasses, print the per-axis statuses and template, the per-type catalogue, the coverage violations, and the totals (expect 55 axes — 32 demo, 16 examples, 7 framework tests; 64 state types — 32/24/8; 0 uncovered statuses; the scan is AST-based, so the two snippets in code docstrings are not counted). Save the run as `specs/014-lifecycle-status-catalog/evidence/scan.before.json` and take `baseline.before.json`: per axis the status type, the statuses with labels and fields, the template states and transitions, the demo's graph state rows and the entity lifecycle field types

---

## Phase 2: User Story 1 — the state type owns its statuses and its catalogue (Priority: P1) 🎯 MVP

**Goal**: a state type declares its own statuses in its own body; every field is initialised and typed, and the type exposes the catalogue.

**Independent Test**: quickstart §1 — a state type with six fields and three statuses prints every field in `model_dump()`, defaults fill the omitted ones, `members`/`codes()`/`by_code()`/`entity_type` answer, and a misspelled field fails at class creation.

### Implementation for User Story 1

- [ ] T003 [US1] Write `packages/aoa-action-machine/src/aoa/action_machine/domain/state_spec.py` with the full principle-III header, the internal `StateSpec` placeholder (it holds the raw `kwargs` and nothing else) and the internal `state(**kwargs) -> StateSpec` factory; one-line docstrings on both; the module is not exported from `domain/__init__.py` (`FR-001`, `FR-016`)
- [ ] T004 [US1] Extend `packages/aoa-action-machine/src/aoa/action_machine/domain/state_entity.py`: `StateEntityMeta(ModelMetaclass)` whose `__prepare__` returns a dict subclass that answers the class's own missing name with `state`, and nothing else; declare `BaseStateEntity` with that metaclass; set `model_config = ConfigDict(**BaseEntity.model_config, ignored_types=(StateSpec,))`; implement `__pydantic_init_subclass__` that collects the `StateSpec` values from `cls.__dict__` in declaration order, replaces each with `cls(**spec.kwargs)`, and refuses a duplicate code with a `ValueError` naming the type and the code; keep the existing name rule and `exclude_graph_model`; update the AI-CORE block (`FR-001`, `FR-002`, `FR-005`, `FR-006`, `FR-016`, `FR-017`, `FR-018`)
- [ ] T005 [US1] Add the catalogue API to `BaseStateEntity` in `packages/aoa-action-machine/src/aoa/action_machine/domain/state_entity.py`: `members: ClassVar[tuple[BaseStateEntity, ...]] = ()`, `codes()`, `by_code(code)` (raises `KeyError`), and `entity_type` (the type itself); the hook fills `members` and the code lookup; a subclass with no placeholders inherits the parent's tuple; a type with no statuses keeps `()` (`FR-002`, `FR-003`, `FR-004`)
- [ ] T006 [US1] Update `packages/aoa-action-machine/src/aoa/action_machine/domain/__init__.py`: the new declaration appears in the module docstring's `EXAMPLES`, `BaseStateEntity` stays exported, `state` and `StateSpec` stay internal; extend `packages/aoa-action-machine/tests/action_machine/smoke/test_lazy_exports_coverage.py` only if the export list changes (it should not) (`FR-016`)
- [ ] T007 [US1] Extend `packages/aoa-action-machine/tests/action_machine/domain/test_state_entity.py` with the surface and catalogue tests: a six-field status dumps every field; omitted fields take defaults; `sort_ordr=99` gives `Extra inputs are not permitted`; a missing `code` gives `Field required`; `sort_order="abc"` fails and `"42"` is stored as `int`; `members` is in declaration order; `codes()`, `by_code("paid")`, `by_code("missing")` (`KeyError`), `entity_type`; duplicate codes are refused; a subclass inherits and a subclass with statuses gets its own; a type with no statuses is valid; the alias works only as a call; another unknown name still raises `NameError`; a global named like the type is shadowed; a self-referential annotation stays a forward reference; removing `ignored_types` fails class creation; every new test has a one-line docstring (`FR-002`–`FR-006`, `SC-001`, `SC-004`)
- [ ] T008 [US1] Run `uv run --extra dev pytest packages/aoa-action-machine/tests/action_machine/domain -q` and `uv run --extra dev mypy packages/aoa-action-machine/src/aoa/action_machine/domain/state_spec.py packages/aoa-action-machine/src/aoa/action_machine/domain/state_entity.py`; the existing 55 axes and 64 state types still import with `members == ()` and no behaviour change

**Checkpoint**: US1 is deliverable on its own — a new state type declares statuses, initialises every field and exposes the catalogue; the corpus has not moved and the old mixin still runs.

---

## Phase 3: User Story 3 — the corpus migrates (Priority: P2)

**Goal**: all 55 axes move their statuses to the state type, drop `StateVocabulary`, and keep the same statuses, transitions, entity fields and graph rows.

**Independent Test**: quickstart §8 — the scan reports 0 axes on `StateVocabulary` and 0 uncovered statuses, and `compare_baselines.py` reports 55 axes and 64 types with no changed status, label, transition, state row or entity field.

### Implementation for User Story 3

- [ ] T009 [US3] Write `specs/014-lifecycle-status-catalog/evidence/migrate_lifecycle_catalog.py` — the AST codemod: for each `class X(Lifecycle, StateVocabulary)`, find the state type from the first argument of each status call, move those assignments into the state type body preserving order, remove `StateVocabulary` from the bases and imports, keep `class X(Lifecycle)`, and qualify the bare names in `_template` with the state type; resolve imported state types per module; refuse a collision or an unresolvable call; print a per-file change count; handle a module with several axes and private axes (`FR-013`)
- [ ] T010 [P] [US3] Write `specs/014-lifecycle-status-catalog/evidence/compare_baselines.py` — compare `baseline.before.json` and `baseline.after.json` per axis: status codes, labels, field values, template states, classification and transitions, the demo graph state rows and the entity lifecycle field types; report changed/missing/added axes and any moved field
- [ ] T011 [P] [US3] Migrate the framework's tests and fixtures: run the codemod over `packages/aoa-action-machine/tests/` (7 axes, 8 state types, including `packages/aoa-action-machine/tests/support/domain_model/entities.py`), keeping the deliberately undeclared and error-teaching fixtures
- [ ] T012 [P] [US3] Migrate the demo: run the codemod over `packages/aoa-demo/src/aoa/demo/model/` (32 axes and 32 state types in 17 bounded contexts)
- [ ] T013 [P] [US3] Migrate the example scripts: run the codemod over `examples/` (16 axes and 24 state types), including `examples/step_22_lifecycle/`, `examples/step_26_maxitor/` and `examples/domain_model/`; the notebooks are not edited here
- [ ] T014 [P] [US3] Sweep the remaining packages and the docstring examples: run the scan over `packages/*` outside the three migrated roots; expect 0 live axes and 0 live state types (the measured 7/8 are in `aoa-action-machine/tests`, migrated by T011); update any code docstring that still shows the old form — the `state_vocabulary.py` example disappears with T015 — and record the 0 in the after-run
- [ ] T015 [US3] Remove `packages/aoa-action-machine/src/aoa/action_machine/domain/state_vocabulary.py`, its import and `__all__` entry in `domain/__init__.py`, its tests in `test_state_entity.py` and every Python mention of `StateVocabulary` the codemod left; `grep -rn "StateVocabulary" --include=*.py packages examples` prints 0 (`FR-013`)
- [ ] T016 [US3] Move the 13 catalogue call sites (`by_code`, `codes()`, `members`, `entity_type`) from the axes to the state types in `packages/aoa-action-machine/tests/` and `examples/`; fix the imports and the docstrings that name the old owner (`FR-003`, `SC-002`)
- [ ] T017 [US3] Take `specs/014-lifecycle-status-catalog/evidence/baseline.after.json` and run `compare_baselines.py`; the result must be "55 axes and 64 types compared, 0 with a changed status, label, transition, state row or entity field"; break one axis on purpose in a scratch copy to see the comparison fail, then restore (`SC-005`)
- [ ] T018 [US3] Run `specs/014-lifecycle-status-catalog/evidence/scan_lifecycle_catalog.py` again and record `specs/014-lifecycle-status-catalog/evidence/scan.after.json`: 0 axes on `StateVocabulary`, 0 uncovered statuses, 55/64; run the full suite of every package and all the lifecycle example scripts; no failure (`SC-002`, `SC-005`)

**Checkpoint**: the corpus is on the new form; the old mixin is gone; no new refusal is on yet — the last moment a migration decision can be reconsidered without breaking imports.

---

## Phase 4: User Story 2 — the axis declares its type and the refusals land (Priority: P1)

**Goal**: `class OrderLifecycle(Lifecycle[OrderStateEntity])` names its type; a foreign status and a missing status are refused at class creation.

**Independent Test**: quickstart §2–§6 — a valid axis builds; a status of another type, an equal-but-distinct instance and a missing status each raise their named error; a plain `Lifecycle` still builds unchecked.

### Implementation for User Story 2

- [ ] T019 [P] [US2] Make `Lifecycle` generic in `packages/aoa-action-machine/src/aoa/action_machine/domain/lifecycle.py`: `StateT = TypeVar("StateT", bound=BaseStateEntity)`, `class Lifecycle(Generic[StateT])`, a `_state_type` class attribute, and `__init_subclass__` that reads the type from `cls.__dict__.get("__orig_bases__")` with `get_origin`/`get_args`, inherits `_state_type` when a subclass has no generic base, stores the type, and — when the class has its own `_template` — runs the two refusals; parameterise all 55 migrated axes: `class X(Lifecycle)` becomes `class X(Lifecycle[<state type>])`, the state type resolved from the migrated status calls (extend the codemod or run a second AST pass), so every axis names a type with members; update the AI-CORE block (`FR-007`, `FR-008`–`FR-012`)
- [ ] T020 [P] [US2] Add `ForeignStateError(TypeError)` and `MissingStateError(ValueError)` to `packages/aoa-action-machine/src/aoa/action_machine/domain/exceptions.py`, each with an AI-CORE block and a one-line docstring, and export both from `domain/__init__.py`; add them to the exceptions map in the module docstring; the foreign message distinguishes "code not declared" (names the type and the allowed codes) from "different instance" (names `Type.STATUS`, resolved through the MRO); the missing message lists the codes (`FR-008`, `FR-009`, `FR-010`, `SC-003`)
- [ ] T021 [US2] Parameterise every bare `Lifecycle` annotation for `disallow_any_generics` — the grep found 22 candidate lines across `lifecycle.py`, `exceptions.py`, `graph/nodes/lifecycle_graph_node.py`, `graph/nodes/state_graph_node.py`, `intents/entity/lifecycle_intent_resolver.py`, `intents/role_mode/role_mode_intent.py`, `tests/action_machine/domain/test_entity_introspection.py`, `tests/action_machine/domain/test_testing.py` and `tests/support/domain_model/entities.py`, including docstring mentions in `exceptions.py` and `role_mode_intent.py`; mypy is the authority — parameterise every real annotation with `Lifecycle[BaseStateEntity]` where the type is unknown; run `uv run --extra dev mypy packages/` and add no `# type: ignore` (`FR-015`, `SC-006`)
- [ ] T022 [US2] Write `packages/aoa-action-machine/tests/action_machine/domain/test_lifecycle_catalog_checks.py`: a valid axis; a status of another type; an equal twin (`ForeignStateError` naming `OrderStateEntity.DRAFT`); an inherited status naming its parent's attribute; a missing status; a target-only status; an empty-catalogue axis; a subclass with its own narrowed template; two axes over one state type, both complete; a narrowed second axis over the same type; a plain `Lifecycle`; `_state_type` resolution and inheritance; every new test has a one-line docstring (`FR-007`–`FR-012`, `SC-003`)
- [ ] T023 [US2] Update the existing lifecycle and graph tests to the generic axis: `packages/aoa-action-machine/tests/action_machine/domain/test_lifecycle.py`, `packages/aoa-action-machine/tests/action_machine/graph_host/test_lifecycle_graph_node.py`, `packages/aoa-action-machine/tests/action_machine/graph/…` and the support fixtures; remove the tests that asserted `StateVocabulary` behaviour and keep the equality of the template, the graph rows and the runtime (`SC-005`)
- [ ] T024 [US2] Adversarial proof in `packages/aoa-action-machine/src/aoa/action_machine/domain/lifecycle.py`, `state_entity.py` and `state_spec.py`, one break at a time: replace the identity check with `in` (the twin test fails alone); remove the coverage check (the missing test fails alone); remove the `__pydantic_init_subclass__` conversion (the catalogue tests fail); remove `StateSpec` from `ignored_types` (`PydanticUserError`); break the `__prepare__` alias (`NameError`); misspell one field (`ValidationError`); restore after each (`SC-003`, `SC-004`)
- [ ] T025 [US2] Run every package suite, all example scripts and `uv run --extra dev mypy packages/`; green with only the two accepted remarks absent from this local run (`SC-006`)

**Checkpoint**: all four user stories are delivered; the refusals are on; the next step is the check run.

---

## Phase 5: The check run (constitution VI.1)

- [ ] T026 Take the closing check run to zero (`SC-002`, `SC-005`, `SC-006`): walk [quickstart.md](./quickstart.md) sections 1–9 by hand, then run `bash scripts/run_checks_with_log.sh` from the repository root and fix every remark until it exits without errors. Only the two accepted remarks stay in the log (the Vite chunk-size advisory and LangGraph's `LangChainPendingDeprecationWarning`); whatever `ruff check --fix` changes is reviewed and kept or reverted. The three whole-tree proofs belong here: (a) the scan reports 0 axes on `StateVocabulary`, 0 uncovered statuses, 55 axes and 64 state types; (b) `compare_baselines.py` reports 0 changed statuses, labels, transitions, state rows or entity fields; (c) `grep -rn "StateVocabulary" --include=*.py packages examples` prints 0

---

## Phase 6: User Story 4 — the reader sees the declaration (Priority: P3)

**Goal**: the documentation shows the surface, the fields, both refusals, the plain escape and the alias's cost; every case is a script and a notebook, executed while written.

**Independent Test**: quickstart §1–§6 — each case prints what the notebook shows, and the reference page names every case.

### Documentation for User Story 4

- [ ] T027 [US4] Write the documentation of the change in `docs/tutorials/step-22-lifecycle.md`, `docs/reference/intents-and-invariants.md`, `README.md` and `examples/step_22_lifecycle/` (`SC-007`), every case shown twice and every example executed while it is written. Its deliverables, in one pass:
  - `docs/tutorials/step-22-lifecycle.md` and `docs/tutorials/step-22-lifecycle.ru_draft.md` — the new declaration, the fields and defaults, both refusals, the plain escape, the alias's shadowing and forward-reference rules
  - `docs/reference/intents-and-invariants.md` and its `ru_draft` — the lifecycle FSM contract: the catalogue on the type, the generic axis, the identity and coverage rules, the two errors
  - `README.md` — the lifecycle section now shows `DRAFT = OrderStateEntity(...)` and `Lifecycle[OrderStateEntity]`
  - `examples/step_22_lifecycle/20_missing_status.py` + `.ipynb`, `21_twin_instance.py` + `.ipynb`, `22_status_fields.py` + `.ipynb`, `23_plain_lifecycle.py` + `.ipynb` — four new cases, each a script and a notebook, executed
  - the existing lifecycle examples and notebooks re-executed against the new form: `examples/step_22_lifecycle/01…19`, `examples/step_26_maxitor/01_graph`, `examples/domain_model/01_domain_model`
  - every page links its Russian draft beside it; no example is edited after execution

---

## Phase 7: The changelog (constitution VI.3)

- [ ] T028 Write the changelog last (`SC-006`): one article at the top of `docs/CHANGELOG.md`, dated `2026-10-22`, in the form the existing dated entries use — what a reader can now rely on (a status belongs to its type; every status is initialised and typed; the axis names its type and refuses a foreign or missing status; the catalogue is on the type; `StateVocabulary` is gone), with the nuances a user needs and no per-file account: the status surface is the type's own name, a narrowed axis declares its own type, the alias shadows a same-named global, and `by_code`/`members` moved from the axis to the type. Add the `[Unreleased]` entries beside it: `packages/aoa-action-machine/CHANGELOG.md` (the catalogue on `BaseStateEntity`, the generic `Lifecycle`, the two errors, `StateVocabulary` removed) and `packages/aoa-demo/CHANGELOG.md` (55 axes migrated, old form removed), both under *Breaking changes*. Then the final diff pass: no module without its principle-III header, no new public symbol without a one-line docstring and an AI-CORE block, no Russian in code or commit-facing text, no scratch file outside `specs/014-lifecycle-status-catalog/evidence/`

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)** — no dependency.
- **US1 (Phase 2)** — after Setup; it delivers the seam and the catalogue. It is the MVP and blocks US3 and US2.
- **US3 (Phase 3)** — after US1: the statuses move onto the type, so the type must accept declarations and expose the catalogue.
- **US2 (Phase 4)** — after US3: the generic axis and the refusals are green only when every axis already names its type.
- **Check run (Phase 5)** — after US2; it is the first of the three tail steps.
- **US4 (Phase 6)** — after the check run: documentation follows the code.
- **Changelog (Phase 7)** — after the documentation: the last step of the change.

### Story dependencies

- **US1 (P1)**: no dependency beyond Setup; its catalogue is used by US3's migration and US2's checks.
- **US2 (P1)**: depends on US3's migrated axes; its tests are the only proof the refusals exist.
- **US3 (P2)**: depends on US1 for the surface; it removes the old mixin before US2 turns the new checks on.
- **US4 (P3)**: depends on US1, US2 and US3 — it documents what they deliver.

### Within the migration

- T009 (codemod) → T011–T014 (four trees, parallel) → T015 (remove the mixin) → T016 (call sites) → T017 (after-baseline and comparison) → T018 (scan and suites)
- T010 (comparison script) can be written alongside T009; it is needed by T017.

### Within US2

- T019 and T020 can be written in parallel (different files); T021 needs both; T022 and T023 need T019 and T020; T024 needs T022 and T023; T025 is the closing run.

### Parallel opportunities

- T010–T014: different trees (evidence script, framework tests, demo, examples, remaining packages).
- T019 and T020: the axis and the exceptions.
- T011–T014 are the four migration areas; each is a different tree and none depends on the other.

---

## Parallel Example: the four migration areas

```bash
# After T009, the codemod runs over four disjoint trees:
uv run python specs/014-lifecycle-status-catalog/evidence/migrate_lifecycle_catalog.py --root packages/aoa-action-machine/tests
uv run python specs/014-lifecycle-status-catalog/evidence/migrate_lifecycle_catalog.py --root packages/aoa-demo/src
uv run python specs/014-lifecycle-status-catalog/evidence/migrate_lifecycle_catalog.py --root examples
uv run python specs/014-lifecycle-status-catalog/evidence/migrate_lifecycle_catalog.py --root packages/aoa-ocel
```

## Independent test criteria per story

| Story | Proven on its own by |
| --- | --- |
| US1 | quickstart §1 — every field initialised, defaults, the catalogue, the field errors, the alias and the shadowing |
| US2 | quickstart §2–§6 — the valid axis, the foreign type, the twin, the missing status, the target-only status and the plain `Lifecycle` |
| US3 | quickstart §8 — the scan after the migration and the baseline comparison |
| US4 | quickstart §1–§6 — the example scripts and their notebooks; the reference page names every case |

## Implementation Strategy

### MVP first

Setup + US1 (T001–T008) is a deliverable, testable increment on its own: a state type declares its statuses, every field is initialised and typed, and the catalogue answers; the corpus has not moved and the old mixin still runs.

### Incremental delivery, in the only order that keeps the tree green

1. Setup → US1: the surface and the catalogue.
2. US3: the corpus moves, the old mixin is removed; the refusals are not on yet.
3. US2: the generic axis and the refusals; every axis already names its type.
4. The tail: check run → documentation → changelog, three steps and no other.

### Stop points

- **After T008**: the new surface is proven on fixtures; the 55 axes are still on the old form.
- **After T018**: the corpus is on the new form and the refusals are still off — the last moment a migration decision can be reconsidered without breaking imports.
- **After T026**: the check run is zero, and the documentation has not been written yet.

---

## Notes

- Every refusal carries its error type from `contracts/lifecycle-axis-contract.md`: `ForeignStateError` (both messages) and `MissingStateError`; the field errors are Pydantic's `ValidationError`.
- The catalogue constraint is quoted from `data-model.md`: `members` in declaration order, unique codes, `by_code` raises `KeyError`, `entity_type` is the type itself, a subclass inherits or gets its own.
- Verification is adversarial throughout: the identity check, the coverage check, the hook conversion, `ignored_types` and the alias are each broken on purpose once, observed to fail alone, and restored.
- The tail is exactly three tasks — T026, T027, T028 — in the constitution's order, and no other task absorbs them.
- Plan → tasks: plan phase 1 = T001–T002; phase 2 = T003–T008; phase 3 = T009–T018; phase 4 = T019–T025; phase 5 = T026; phase 6 = T027; phase 7 = T028.
- Commit after each phase, only on the maintainer's instruction (constitution I); one phase is one commit.
