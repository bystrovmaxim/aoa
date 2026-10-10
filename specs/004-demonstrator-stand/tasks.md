---

description: "Task list for the demonstrator stand"
---

# Tasks: The demonstrator stand

**Input**: Design documents from `/specs/004-demonstrator-stand/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/stand.md, contracts/shape-coverage.md, quickstart.md

**Tests**: Included — the spec requires the fixture-shape test and the repository's adversarial rule (break → the test fails and no other does → restore); the stand itself is verified by running containers and by the deploy script's rollback branch.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US5)
- Exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: The stand's configuration surface

- [x] T001 Create `deploy/stand/.env.example` with the named configuration placeholders only — `DEMO_PORT`, `MAXITOR_PORT`, `DEMO_DOMAIN`, `MAXITOR_DOMAIN`, `HOST`, `SSH_ALIAS` — each with a comment saying what it is and that real values live in `/etc/aoa-stand.env` on the host, never in the repository (FR-013).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The compose definition both services are wired into — MUST complete before any story work

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T002 Create `deploy/stand/docker-compose.yml` — two services, `demo` (internal port 8100, published on `127.0.0.1:8100` only) and `maxitor` (internal port 8101, published on `127.0.0.1:8101` only); build context is the repository root; each service with `restart: unless-stopped` and a `stop_grace_period`; healthcheck blocks added in T015 once the endpoints are verified (FR-004, FR-005, FR-014).

**Checkpoint**: the stand's compose skeleton is in place; both stories can build their images into it

---

## Phase 3: User Story 1 - Maxitor serves the diagram, built from this repository (Priority: P1) 🎯 MVP

**Goal**: The Maxitor image is built from this repository's sources, client build included — never from PyPI

**Independent Test**: build the image from a clean checkout and confirm the client was built inside it; the container serves the Maxitor API

### Implementation for User Story 1

- [x] T003 [US1] Rewrite `packages/aoa-maxitor/Dockerfile` as a multi-stage build: stage 1 — a Node image runs `cd packages/aoa-maxitor/client && npm ci && npm run build`; stage 2 — a Python 3.12 image installs the uv workspace from the repository root (no `aoa-*` package from PyPI), copies the built client from stage 1, and serves the Maxitor API. Remove the `pip install aoa-maxitor==1.1.6` line entirely (FR-001).
- [x] T004 [US1] Verify locally: `docker compose -f deploy/stand/docker-compose.yml build maxitor` succeeds from a clean checkout; confirm the built client is inside the image (e.g., the client `dist/` exists in the expected path) and that the running container answers its API port.

**Checkpoint**: the Maxitor image is this repository's build — the stale-release trap is gone

---

## Phase 4: User Story 2 - The demonstrator serves the demo service (Priority: P1)

**Goal**: The demo image is built from this repository with the `[fastapi]` and `[mcp]` extras and serves the declared entry point

**Independent Test**: build the image, run it, and the demo service answers on its port

### Implementation for User Story 2

- [x] T005 [US2] Create `packages/aoa-demo/Dockerfile` — Python 3.12 image installing the uv workspace from the repository root with the `[fastapi]` and `[mcp]` extras, `CMD ["uvicorn", "aoa.demo.fastapi_mcp_services.app_fastapi_service:app", "--host", "0.0.0.0", "--port", "8100"]` (FR-002, FR-003).
- [x] T006 [US2] Verify locally: `docker compose -f deploy/stand/docker-compose.yml build demo` succeeds; running the container answers `GET /ping` on 127.0.0.1:8100; note the verified health endpoint path for T015.

**Checkpoint**: both images build from the repository; the stand has both halves locally

---

## Phase 5: User Story 3 - The stand's diagram shows the shapes it cannot draw today (Priority: P2)

**Goal**: Generalization fixtures in the demo model, and the "all shapes" audit that makes coverage true rather than intended

**Independent Test**: the fixture test proves `parent_action`/`parent_entity` edges in the graph; the audit table marks every published kind

### Implementation for User Story 3

- [x] T007 [P] [US3] Create the `generalization_shapes` domain group: `packages/aoa-demo/src/aoa/demo/model/generalization_shapes/__init__.py`, `actions/__init__.py`, `entities/__init__.py`, and `generalization_shapes_domain.py` with `GeneralizationShapesDomain` (`name = "generalization_shapes"`, description naming the shape purpose; module headers and AI-CORE per constitution III–IV).
- [x] T008 [P] [US3] Create `GeneralizationParentAction`, `GeneralizationFirstChildAction`, `GeneralizationSecondChildAction` in `packages/aoa-demo/src/aoa/demo/model/generalization_shapes/actions/generalization_actions.py` — the two children subclass the parent (each drawn as a `parent_action` generalization edge); `@meta` descriptions name the shape; export from `actions/__init__.py`. Child names must end with `Action` (framework suffix).
- [x] T009 [P] [US3] Create the specialization entities in `packages/aoa-demo/src/aoa/demo/model/generalization_shapes/entities/generalization_entities.py` — `GeneralizationHeadEntity` declares `Specialization[A | B]` with its `Classifier` and `Inverse`, and `GeneralizationVariantAEntity`/`GeneralizationVariantBEntity` each declare `Generalization[Head]` with its own code; `@entity` descriptions name the shape; export from `entities/__init__.py`. (Plain `BaseEntity` subclassing produces no `parent_entity` edge — the specialization declaration is the shape; #199 is already in main.)
- [x] T010 [US3] Register the domain group in the `_MODULES` tuple of `packages/aoa-demo/src/aoa/demo/model/build.py` (the domain, actions and entities modules — the only registration list) (depends on T007–T009).
- [x] T011 [US3] Add `packages/aoa-demo/tests/model/test_generalization_shapes.py`: the graph carries `parent_action` edges from both children into the parent, `parent_entity` edges from both extensions into the head, and the `entity_specialization` axis edges from the head into the variants; verify adversarially (break one declaration → the tests fail and no other does → restore) (FR-008, FR-009).
- [x] T012 [US3] Create `scripts/stand_shape_audit.py` — enumerate the published node and edge kinds from `NodeGraphCoordinator.get_available_types()`, mark each `carried & drawn` / `named gap`, and write the filled table to `specs/004-demonstrator-stand/contracts/shape-coverage.md`; the recorded picture upgrades `named gap` rows (FR-010).

**Checkpoint**: the demo carries generalization shapes, and "all shapes" is a filled table, not an intention

---

## Phase 6: User Story 4 - One host, two domains, TLS, and health (Priority: P2)

**Goal**: The stand fits beside what the host already serves — two virtual hosts on the existing terminator, issued-and-renewed certificates, visible health

**Independent Test**: a broken container reports unhealthy instead of hanging; the deploy gates refuse before touching the host when DNS or the terminator is missing

### Implementation for User Story 4

- [x] T013 [US4] In `scripts/deploy_demonstrator_stand.sh`, implement the two gates first: both `dev.demo.aoa.run` and `dev.maxitor.aoa.run` must resolve, and the host's existing TLS terminator must be detectable (look for the known config layouts — nginx/caddy/traefik — and refuse with a message naming the missing prerequisite otherwise). Gates exit non-zero before any build or deploy step (FR-005, FR-006).
- [x] T014 [US4] Implement the virtual-host and certificate step in `scripts/deploy_demonstrator_stand.sh`: add two virtual hosts to the detected terminator proxying to `127.0.0.1:8100` and `127.0.0.1:8101`, and request the certificates through the terminator's own renew mechanism — never hand-made (FR-005, FR-006).
- [x] T015 [US4] Verify the health endpoints (demo `GET /health`; Maxitor's `GET /api/health`) and finalize the healthcheck blocks in `deploy/stand/docker-compose.yml`; stop one container and confirm `docker compose ps` reports it unhealthy and the probe fails fast rather than hanging (FR-007).

**Checkpoint**: TLS and health are wired through the existing front end, with gates that refuse instead of guessing

---

## Phase 7: User Story 5 - Deployment is one command, with rollback (Priority: P3)

**Goal**: From a clean checkout, one command builds, runs, verifies and rolls back; secrets stay out of the repository; the stand survives a host restart

**Independent Test**: run the single command; then break one step and confirm the rollback branch restores the previous stand

### Implementation for User Story 5

- [x] T016 [US5] Complete `scripts/deploy_demonstrator_stand.sh` as the single command, in order: gates (T013) → `docker compose -f deploy/stand/docker-compose.yml build` → `up -d` → healthcheck polling for both containers → `curl -fsS` both `https://` domains → on any failure, roll back to the previously running images/containers and report. Read configuration and secrets from `/etc/aoa-stand.env` (FR-012, FR-013).
- [x] T017 [US5] Validate the rollback branch adversarially in the local stand: break one step (e.g., a wrong healthcheck path), run the script, confirm it restores the previous containers and reports the failure; restore and confirm a clean run goes green end to end (FR-012).

**Checkpoint**: the stand deploys with one command and provably rolls back

---

## Phase 8: Record the evidence & Polish

**Purpose**: The recorded picture, then the constitutional tail — in this order: evidence, check run, documentation, changelog (constitution VI)

- [x] T018 Record the picture: generate the DOT and WASM-rendered SVG for the use-case diagram and the ERD slice with the client's own builders (the same procedure as issue #201), save them under `specs/004-demonstrator-stand/contracts/`, verify by eye against `contracts/stand.md` that generalization edges are visible and every label names its shape; capture the browser PNGs from the live stand when it is up (FR-011, SC-003).
- [x] T019 Run `bash scripts/run_checks_with_log.sh` from the repository root and fix every remark it reports, to zero (constitution VI, first tail step).
- [ ] T020 Write the documentation (skipped by the maintainer's decision — remains open) — every case and every scenario of this change, each shown twice: a runnable script under `examples/` and a notebook of the same case; every example executed with the repository's own environment; publish the English page and its Russian `<page>.ru_draft.md` beside it (constitution VI, second tail step).
- [ ] T021 Write the changelog (skipped by the maintainer's decision — remains open) as one article in `docs/CHANGELOG.md` — what this work created, in plain words, with the nuances a user needs and without technical detail (constitution VI, third tail step).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — starts immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Stories (Phases 3–7)**: All depend on Foundational; proceed in priority order P1 → P3
- **Evidence & Polish (Phase 8)**: Depends on all desired stories being complete

### User Story Dependencies

- **US1 (P1)**: after Foundational — no story dependencies
- **US2 (P1)**: after Foundational — independent of US1; both feed the compose file
- **US3 (P2)**: after Foundational — independent of US1/US2 (pure demo-model work)
- **US4 (P2)**: after Foundational — reads the health endpoints US1/US2 verified (T015)
- **US5 (P3)**: depends on US4's gates (T013/T014) and the compose file

### Within Each User Story

- Fixture/configuration files first (marked [P] — different files), then registration, then tests
- Story complete before moving to the next priority

### Parallel Opportunities

- Phase 5: T007, T008, T009 run in parallel (different files)
- US1 and US2 can run in parallel by different developers (two Dockerfiles, one compose file — T003/T005 are different files, T004/T006 verification is sequential against the shared compose)

---

## Parallel Example: User Story 3

```text
# Launch the three fixture groups together (different files):
Task: "Create the generalization_shapes domain group in .../generalization_shapes/"
Task: "Create the generalization actions in .../generalization_actions.py"
Task: "Create the generalization entities in .../generalization_entities.py"

# Then, after all three:
Task: "Register the domain group in build.py"
Task: "Add the generalization shape tests"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: the Maxitor image is this repository's build — the core acceptance value

### Incremental Delivery

1. Setup + Foundational → compose skeleton
2. Add US1 (Maxitor image) → validate → US2 (demo image) → the local stand runs
3. Add US3 (generalization fixtures + audit) → US4 (TLS gates + health) → US5 (one command + rollback)
4. Record the picture, then the constitutional tail (check run → documentation → changelog)

### Parallel Team Strategy

- Team completes Setup + Foundational together
- Then: Developer A — US1; Developer B — US2; Developer C — US3 (all independent); US4/US5 follow the compose and endpoints

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps a task to its user story for traceability
- Every fixture's description names its shape — never a business claim (FR-011's spirit, as in #201)
- English only in code, comments and scripts (constitution II); new Python modules carry the constitution III header, AI-CORE blocks and one-line docstrings (IV, V)
- Nothing is committed without the maintainer's explicit instruction (constitution I); one phase = one commit
- Host facts (DNS zone, terminator identity, real `.env` values) never enter the repository — the deploy script gates on them
- Stop at any checkpoint to validate the story independently
- Avoid: vague tasks, same-file conflicts, cross-story dependencies that break independence
