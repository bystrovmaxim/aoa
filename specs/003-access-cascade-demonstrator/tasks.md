---

description: "Task list for the access cascade demonstrator"
---

# Tasks: The access cascade demonstrator

**Input**: Design documents from `/specs/003-access-cascade-demonstrator/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/access-shapes.md, quickstart.md

**Tests**: Included — the spec requires the runnable proofs (FR-008, FR-009) and the build gate (FR-012); every test group follows the adversarial rule: break the fixture the way the test must catch, confirm the test fails and no other does, restore.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US5)
- Exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: The dedicated `access_cascade` domain group skeleton

- [x] T001 Create the module-group skeleton with empty public packages: `packages/aoa-demo/src/aoa/demo/model/access_cascade/__init__.py`, `access_cascade/roles/__init__.py`, `access_cascade/actions/__init__.py`, `access_cascade/entities/__init__.py` — each a package `__init__` with no exports yet (constitution III header on each).
- [x] T002 Create `AccessCascadeDomain` in `packages/aoa-demo/src/aoa/demo/model/access_cascade/access_cascade_domain.py` — `BaseDomain` subclass, `name = "access_cascade"`, `description` stating the domain exists to demonstrate access-cascade shapes; standard module header, AI-CORE block (ROLE/CONTRACT), one-line docstrings.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Role fixtures (shared by US1, US2, US3) and model registration — MUST complete before any story work

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Register the new domain group: add the four `aoa.demo.model.access_cascade...` modules to the `_MODULES` tuple in `packages/aoa-demo/src/aoa/demo/model/build.py` — the only registration list (it is imported by the demo coordinator; there is no mirror to edit).
- [x] T004 [P] Create `CascadeSystemGateRole` in `packages/aoa-demo/src/aoa/demo/model/access_cascade/roles/cascade_system_role.py` — `SystemRole` subclass (system level), `name`/`description` naming the level, not a business duty; export from `roles/__init__.py`.
- [x] T005 [P] Create the application-level chain in `packages/aoa-demo/src/aoa/demo/model/access_cascade/roles/cascade_application_roles.py` — `CascadeStaffRole(ApplicationRole)` → `CascadeOfficerRole(CascadeStaffRole)` → `CascadeLineLeadRole(CascadeOfficerRole)` → `CascadeTraineeRole(CascadeLineLeadRole)`; each description names its chain position; export all from `roles/__init__.py`.
- [x] T006 [P] Create the domain-level branch in `packages/aoa-demo/src/aoa/demo/model/access_cascade/roles/cascade_domain_roles.py` — `CascadeDomainRole(BaseRole)` → `CascadeDomainSpecialistRole(CascadeDomainRole)`; descriptions name the branch; export both from `roles/__init__.py`.
- [x] T007 Run `uv run --extra dev pytest packages/aoa-demo/tests/ -q` — the skeleton with the registered domain must build and the whole demo suite must stay green (FR-012).

**Checkpoint**: Foundation ready — role branches and the registered domain build; story implementation can begin

---

## Phase 3: User Story 1 - Every cascade step draws as a distinct shape (Priority: P1) 🎯 MVP

**Goal**: Four operations, one per cascade step: role check alone, `when=` refusal, shared `guard=`, declared object rule

**Independent Test**: the built interchange graph JSON carries each of the four operations with its own access declaration; the demo suite stays green

### Implementation for User Story 1

- [x] T008 [P] [US1] Create `RoleCheckAloneShapeAction` in `packages/aoa-demo/src/aoa/demo/model/access_cascade/actions/role_check_alone_shape_action.py` — `@check_roles(CascadeOfficerRole)` alone; `@meta` description names the shape ("Shape: access decided by a role check alone"); minimal Params/Result stubs and a `@summary_aspect` returning the result; export from `actions/__init__.py`.
- [x] T009 [P] [US1] Create `WhenRefusalShapeAction` in `packages/aoa-demo/src/aoa/demo/model/access_cascade/actions/when_refusal_shape_action.py` — `@check_roles(grant(CascadeOfficerRole, when=<sync function returning False>, reason="shape: WHEN refuses although the role matched"))`; description names the shape; export from `actions/__init__.py`.
- [x] T010 [P] [US1] Create `GuardRefusalShapeAction` in `packages/aoa-demo/src/aoa/demo/model/access_cascade/actions/guard_refusal_shape_action.py` — `@check_roles(CascadeOfficerRole, guard=<sync function returning False>, guard_reason="shape: GUARD refuses every caller alike")`; description names the shape; export from `actions/__init__.py`.
- [x] T011 [P] [US1] Create `AccessDecideShapeAction` in `packages/aoa-demo/src/aoa/demo/model/access_cascade/actions/access_decide_shape_action.py` — a declared object rule via `@access_decide` (method named `..._access_decide`, answers on a real object); description names the shape; export from `actions/__init__.py`.
- [x] T012 [US1] Make the four US1 actions reachable at registration: export them from `packages/aoa-demo/src/aoa/demo/model/access_cascade/actions/__init__.py` (the `actions` package itself is already in `_MODULES` — the repo registers packages, not single modules) (depends on T008–T011).
- [x] T013 [US1] Add the US1 test group to `packages/aoa-demo/tests/model/test_access_cascade_shapes.py` (reuse the coordinator fixture pattern of `packages/aoa-demo/tests/model/test_sample_graph_json_fields.py`): each of the four operations exists in the graph JSON; the role-check operation carries one `check_roles` edge and no `when`/`guard`; the `when` operation carries the reason; the `guard` operation carries `guard_reason`; the object-rule operation carries its `access_decide` node. Verify adversarially before finishing.

**Checkpoint**: User Story 1 fully functional — the four cascade shapes exist in the model

---

## Phase 4: User Story 2 - Roles draw their own structure: levels and hierarchy (Priority: P2)

**Goal**: The three role branches and the multi-level chain are visible in the graph (fixtures landed in Phase 2; this phase proves them)

**Independent Test**: the graph JSON shows the three branches and the `parent_role` chains

### Tests for User Story 2

- [x] T014 [US2] Add the US2 test group to `packages/aoa-demo/tests/model/test_access_cascade_shapes.py`: assert the three branches exist among role nodes (a `SystemRole` branch, an `ApplicationRole` branch, a `BaseRole` domain branch) and that `parent_role` edges connect `CascadeStaffRole → CascadeOfficerRole → CascadeLineLeadRole → CascadeTraineeRole` and `CascadeDomainRole → CascadeDomainSpecialistRole` as chains, not isolated nodes (FR-001, FR-002). Verify adversarially.

**Checkpoint**: role structure proven in the graph; US1 and US2 both work

---

## Phase 5: User Story 3 - Matching and stopping are visible and provable (Priority: P3)

**Goal**: Two roles matching one operation through different paths, and a cascade that provably stops early

**Independent Test**: two role edges from different branches into one operation; the early-stop run returns a refusal naming `CHECK_ROLES` with the object-rule probe untouched

### Implementation for User Story 3

- [x] T015 [P] [US3] Create `TwoPathMatchShapeAction` in `packages/aoa-demo/src/aoa/demo/model/access_cascade/actions/two_path_match_shape_action.py` — `@check_roles(CascadeTraineeRole, CascadeDomainSpecialistRole)` (one path through the hierarchy, one through the domain branch); description names the shape; export from `actions/__init__.py`.
- [x] T016 [P] [US3] Create `EarlyStopShapeAction` in `packages/aoa-demo/src/aoa/demo/model/access_cascade/actions/early_stop_shape_action.py` — `@check_roles(CascadeOfficerRole)` plus `@access_decide` whose body increments a module-level probe counter before answering; description names the shape; export from `actions/__init__.py`.
- [x] T017 [US3] Make the two US3 actions reachable at registration: export them from `packages/aoa-demo/src/aoa/demo/model/access_cascade/actions/__init__.py` (depends on T015–T016).
- [x] T018 [US3] Add the US3 test group to `packages/aoa-demo/tests/model/test_access_cascade_shapes.py`: two `check_roles` edges into `TwoPathMatchShapeAction` from different branches (FR-007); run `EarlyStopShapeAction` as a caller who fails `CHECK_ROLES` → the refusal names `CHECK_ROLES` and the probe counter is zero, proving the declared object rule was not reached (FR-008). Verify adversarially.

**Checkpoint**: matching and early stop proven; US1–US3 work

---

## Phase 6: User Story 4 - A refusal can be an answer (Priority: P4)

**Goal**: The asked-about operation is labelled in the drawing, and asking in advance returns a refusal answer without running the pipeline (Clarification Q1: both)

**Independent Test**: the operation's label exists in the graph; `machine.check_access_decide` returns a refusal answer — never an exception — and no aspect ran

### Implementation for User Story 4

- [x] T019 [US4] Create `QuestionPathShapeAction` in `packages/aoa-demo/src/aoa/demo/model/access_cascade/actions/question_path_shape_action.py` — same declared shape as the other cascade operations (`@check_roles` + `@access_decide`), with the `@meta` description saying it is the asked-about operation (the label the drawing carries); its summary aspect flips a module-level probe so a run is observable; export from `actions/__init__.py`.
- [x] T020 [US4] Make the US4 action reachable at registration: export it from `packages/aoa-demo/src/aoa/demo/model/access_cascade/actions/__init__.py`.
- [x] T021 [US4] Add the US4 test group to `packages/aoa-demo/tests/model/test_access_cascade_shapes.py`: the operation exists in the graph JSON with its question-path label; `machine.check_access_decide` for a refusing caller returns a refusal answer — no exception — and the pipeline probe proves no aspect ran, no cache, no events (FR-009). Verify adversarially.

**Checkpoint**: the question path is both drawn and proven; US1–US4 work

---

## Phase 7: User Story 5 - Boundary extremes (Priority: P5)

**Goal**: One entity whose relation is deliberately one-sided — the `NoInverse` boundary worth drawing

**Independent Test**: the graph JSON shows the entity with its `NoInverse` relation marker

### Implementation for User Story 5

- [x] T022 [US5] Create `CascadeBoundaryEntity` in `packages/aoa-demo/src/aoa/demo/model/access_cascade/entities/cascade_boundary_entity.py` — `BaseEntity` subclass with exactly one relation field declared `NoInverse()` and `= Rel(description=...)` naming the one-sided boundary shape; no other relations, no lifecycle; export from `entities/__init__.py`.
- [x] T023 [US5] Ensure the `entities` module is present in the `_MODULES` tuple of `packages/aoa-demo/src/aoa/demo/model/build.py` (it was added in T003; verify the entity is reachable through the package import).
- [x] T024 [US5] Add the US5 test group to `packages/aoa-demo/tests/model/test_access_cascade_shapes.py`: the entity exists in the graph JSON and its relation field carries the `NoInverse` marker (FR-010). Verify adversarially.

**Checkpoint**: all five stories implemented; the model builds and the suite is green

---

## Phase 8: Record the evidence & Polish

**Purpose**: The recorded drawing, then the constitutional tail — in this order: evidence, check run, documentation, changelog (constitution VI)

- [ ] T025 Record the drawing evidence per `specs/003-access-cascade-demonstrator/quickstart.md` steps 3–4: build the Maxitor client and the demo, open the use-case diagram for the `access_cascade` domain, verify all ten shapes against `specs/003-access-cascade-demonstrator/contracts/access-shapes.md`, and commit-ready the generated DOT to `specs/003-access-cascade-demonstrator/contracts/access-shapes.dot` and the rendered picture to `specs/003-access-cascade-demonstrator/contracts/access-shapes.png` (FR-013, SC-001, SC-003, SC-004).
- [x] T026 Run `bash scripts/run_checks_with_log.sh` from the repository root and fix every remark it reports, to zero (constitution VI, first tail step).
- [ ] T027 Write the documentation — every case and every scenario of this change, each shown twice: a runnable script under `examples/` and a notebook of the same case; every example executed with the repository's own environment; publish the English page and its Russian `<page>.ru_draft.md` beside it (constitution VI, second tail step).
- [ ] T028 Write the changelog as one article in `docs/CHANGELOG.md` — what this work created, in plain words, with the nuances a user needs and without technical detail (constitution VI, third tail step).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — starts immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Stories (Phases 3–7)**: All depend on Foundational; proceed in priority order P1 → P5
- **Evidence & Polish (Phase 8)**: Depends on all desired stories being complete

### User Story Dependencies

- **US1 (P1)**: after Foundational — no story dependencies (consumes the foundational role fixtures)
- **US2 (P2)**: after Foundational — proves the foundational role structure
- **US3 (P3)**: after Foundational — uses `CascadeTraineeRole`/`CascadeDomainSpecialistRole` from the foundation
- **US4 (P4)**: after Foundational — no story dependencies
- **US5 (P5)**: after Foundational — no story dependencies

### Within Each User Story

- Fixture modules first (marked [P] — different files), then registration, then the test group
- Test groups all live in `packages/aoa-demo/tests/model/test_access_cascade_shapes.py` and are added phase by phase — sequential by design, never parallel
- Story complete before moving to the next priority

### Parallel Opportunities

- Phase 2: T004, T005, T006 run in parallel (three role files)
- Phase 3: T008, T009, T010, T011 run in parallel (four action files)
- Phase 5: T015 and T016 run in parallel
- Test groups: never in parallel (one shared test file)

---

## Parallel Example: User Story 1

```text
# Launch all four US1 fixtures together (different files):
Task: "Create RoleCheckAloneShapeAction in .../role_check_alone_shape_action.py"
Task: "Create WhenRefusalShapeAction in .../when_refusal_shape_action.py"
Task: "Create GuardRefusalShapeAction in .../guard_refusal_shape_action.py"
Task: "Create AccessDecideShapeAction in .../access_decide_shape_action.py"

# Then, after all four:
Task: "Register the four US1 action modules in build.py and the mirror list"
Task: "Add the US1 test group to test_access_cascade_shapes.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: the four cascade shapes are in the model and the suite is green — the core value is demonstrable

### Incremental Delivery

1. Setup + Foundational → roles and domain registered, suite green
2. Add US1 (four cascade shapes) → validate → the MVP shape set
3. Add US2 (hierarchy proof) → US3 (matching + early stop) → US4 (question path) → US5 (boundary extreme)
4. Record the drawing evidence, then the constitutional tail (check run → documentation → changelog)

### Parallel Team Strategy

- Team completes Setup + Foundational together
- Then: Developer A — US1; Developer B — US2 + US3; Developer C — US4 + US5 (test groups must be coordinated — one shared file, phases ordered)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps a task to its user story for traceability
- Every fixture's description names its shape — never a business claim (FR-011)
- Every new module carries the constitution III header; public classes carry AI-CORE blocks and one-line docstrings (constitution IV, V)
- English only in code, comments, tests and descriptions (constitution II)
- Nothing is committed without the maintainer's explicit instruction (constitution I); one phase = one commit
- Stop at any checkpoint to validate the story independently
- Avoid: vague tasks, same-file conflicts, cross-story dependencies that break independence
