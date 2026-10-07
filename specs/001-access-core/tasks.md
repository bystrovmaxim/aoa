# Tasks: Access decisions — three answers, one cascade, two events

**Input**: Design documents from `specs/001-access-core/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

**Tests**: included. Every phase in issue #189 names its tests, the repository's adversarial-verification rule requires them, and the closing check run executes them — a phase without tests is not reviewable here.

**Organization**: tasks are grouped by user story, so each story can be implemented and tested on its own. Every phase below is one commit, and a commit happens only on the maintainer's instruction (constitution, principle I).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel — different files, no dependency on an unfinished task
- **[Story]**: which user story the task serves (US1, US2, US3)
- Every task names the file it touches

**Traceability**: every task that builds or tests behaviour names the requirements it serves (`FR-###`, `SC-###`). Seven tasks carry no requirement id by design: T001 and T002 (baseline and reproduction, repository rules), T021 (repairing tests the move breaks), and T044–T047 (removal of replaced code, documentation, adversarial checks and the closing check run — required by the constitution rather than by a requirement).

## Path Conventions

Monorepo, one package under change:

- engine: `packages/aoa-action-machine/src/aoa/action_machine/…`
- engine tests: `packages/aoa-action-machine/tests/action_machine/…`
- observability: `packages/aoa-otel/src/aoa/otel/plugin/open_telemetry_plugin.py`
- adapters (except clauses only): `packages/aoa-fastapi-adapter/src/aoa/fastapi/adapter.py`, `packages/aoa-mcp-adapter/src/aoa/mcp/adapter.py`

**For every task below**: a new module opens with its repository-relative path comment, a `Name — purpose.` first line and the 79-column `═` sections (constitution III); every new public class carries an AI-CORE `ROLE`/`CONTRACT` block, with `INVARIANTS` where the type has them (IV); every new class, function and method gets its one-line docstring ending with a period (V).

---

## Phase 1: Setup

**Goal**: a known-good baseline and the current behaviour written down, so every later change is compared with observation rather than memory.

- [x] T001 Run the engine's suite on the untouched branch and record the result — `uv run --extra dev pytest packages/aoa-action-machine/tests -q` — **done: 2081 passed in 7.10s, exit 0**
- [x] T002 Reproduce the behaviour being replaced on both paths (execute a role-refused call and ask in advance about the same call), and record the observed answers as a comment on issue #189 — `packages/aoa-action-machine/src/aoa/action_machine/runtime/action_product_machine.py` — **done: [comment 6043544744](https://github.com/bystrovmaxim/aoa/issues/189#issuecomment-6043544744); a broken check is answered `allowed: False` with the failure's text, the execution path leaks the raw exception**

---

## Phase 2: Foundational (Blocking Prerequisites)

**Goal**: the three answers and the names that travel with them. Every user story reads this vocabulary, so nothing else can start before it exists.

**Independent test**: the answer types can be constructed, validated and serialised, and no invalid answer can be built.

- [x] T003 [P] Create the answer base in `packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/verdict.py` — frozen schema, `kind: str` with **no default**, so the base cannot be built; module header per principle III, AI-CORE block per principle IV, one-line docstrings per principle V (FR-003) — **done: `verdict.py` (63 lines), ruff/mypy clean, pylint 10.00/10; `Verdict()` fails naming `kind`, frozen, extra forbidden; suite still 2081 passed**
- [ ] T004 [P] Create the gate names in `packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/gate.py` — `Gate` with exactly `AUTH_COORDINATOR`, `CHECK_ROLES`, `WHEN_OR_GUARD`, `ACCESS_DECIDE` (FR-004, FR-007)
- [ ] T005 [P] Create the fixed vocabulary in `packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/reasons.py` — `UNAUTHENTICATED`, `FORBIDDEN_ROLE`, `FORBIDDEN_GRANT`, `FORBIDDEN_GUARD`, `FORBIDDEN_OBJECT`, `EVALUATION_FAILED`, declared once (FR-012)
- [ ] T006 Create `Allowed` in `packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/allowed.py` — `kind: Literal["allowed"]` (FR-003)
- [ ] T007 Create `Refused` in `packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/refused.py` — `kind: Literal["refused"]`, `gate: Gate` defaulting to `ACCESS_DECIDE`, `reason: str` **non-empty, no whitespace-only value**, plus the single shared `FORBIDDEN_OBJECT` instance (FR-003, FR-004, FR-011, FR-012)
- [ ] T008 Create `Undecided` in `packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/undecided.py` — `kind: Literal["undecided"]`, `reason` fixed code, private `_cause` that never appears in `model_dump()` (FR-003, FR-005, FR-016)
- [ ] T009 Export the answer types from `packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/__init__.py` (FR-003)
- [ ] T010 Write the answer tests in `packages/aoa-action-machine/tests/action_machine/intents/access_control/test_verdict.py` — `Verdict()` fails, `Refused("")` fails, a wrong `kind` fails, `_cause` is absent from `model_dump()`, `FORBIDDEN_OBJECT` is one instance, the gate default is `ACCESS_DECIDE` (FR-003, FR-004, FR-005, FR-011)

**Checkpoint**: the vocabulary exists and is independently testable.

---

## Phase 3: User Story 1 - Access is declared once and enforced wherever it is asked about (Priority: P1) 🎯 MVP

**Goal**: one cascade decides for both paths, in a fixed order, and an operation without a declaration never reaches a running service.

**Independent test**: declare one operation with a role requirement and one condition; ask in advance and execute, as a caller who satisfies the declaration and as one who does not — the four answers follow from the declaration alone, and the two refusals name the same gate and reason.

### Tests for User Story 1

- [ ] T011 [US1] Write the decision matrix test in `packages/aoa-action-machine/tests/action_machine/intents/access_control/test_cascade.py` — three answers × four gates × two paths, each gate pinned to its own `gate` value and fixed reason; a refusal by gate N means gate N+1 was never called; a gate that raises becomes `Undecided("EVALUATION_FAILED")`; and for the same circumstances the advance answer and the executed outcome are compared pairwise, for an allowed case and a refused case (FR-003, FR-005, FR-007, FR-018, SC-002, SC-006)
- [ ] T012 [US1] Write the path tests in `packages/aoa-action-machine/tests/action_machine/runtime/test_machine_decisions.py` — an `ACCESS_DECIDE` refusal still emits global start; an `AUTH_COORDINATOR`, `CHECK_ROLES` or `WHEN_OR_GUARD` refusal emits no lifecycle event; the question path emits neither start nor finish (FR-013, FR-017, SC-001)
- [ ] T013 [US1] Write the gate-order test in `packages/aoa-action-machine/tests/action_machine/intents/access_control/test_gate_order.py` — the identity and role gates never read the call's parameters; rejected credentials refuse even on an operation declared open to guests; and a caller with rejected credentials and malformed parameters receives a refusal rather than a validation error (FR-007, FR-008, FR-009)
- [ ] T014 [US1] Write the declaration-invariant test in `packages/aoa-action-machine/tests/action_machine/graph/test_missing_check_roles.py` — an operation without an access declaration makes graph assembly fail, before any call is served (FR-001, SC-005)

### Implementation for User Story 1

- [ ] T015 [US1] Create the cascade in `packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/cascade.py` — the four gates with one signature, a gate returning `None` (continue), `Refused` or `Undecided`; `GATES` in the fixed order `auth_gate`, `roles_gate`, `condition_gate`, `object_gate`; `decide()` pure, turning a raising gate into `Undecided("EVALUATION_FAILED", cause=exc)` (FR-002, FR-003, FR-005, FR-007)
- [ ] T016 [US1] Move the role and condition refusals out of `packages/aoa-action-machine/src/aoa/action_machine/runtime/role_checker.py` into `roles_gate` and `condition_gate` (FR-004, FR-010)
- [ ] T017 [US1] Wire the machine in `packages/aoa-action-machine/src/aoa/action_machine/runtime/action_product_machine.py` — `_decide_and_emit(...)`; the execution path reacts to the answer; `check_access_decide` calls it with `check_only=True` and returns the answer for the one call it was asked about (FR-002, FR-017)
- [ ] T018 [US1] Implement the identity gate in `packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/cascade.py` — credentials presented and rejected produce `Refused(gate=AUTH_COORDINATOR, reason=UNAUTHENTICATED)` (FR-004, FR-009)
- [ ] T019 [US1] Implement the object gate in `packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/cascade.py` — accept only `Allowed` or `Refused` from `access_decide()`, and turn anything else, or a failure, into `Undecided` with its cause (FR-005, FR-011)
- [ ] T020 [US1] Update the existing role tests in `packages/aoa-action-machine/tests/action_machine/runtime/test_role_checker.py` to the new refusal shape, and delete assertions that pinned the old exception (FR-004, FR-010)
- [ ] T021 [US1] Fix every test the move breaks in `packages/aoa-action-machine/tests/action_machine/` — no test may keep passing for the wrong reason

**Checkpoint**: US1 is a viable MVP — access declared once, enforced on both paths, with the fixed order.

---

## Phase 4: User Story 2 - A refusal says what refused and why, and reveals nothing about objects (Priority: P2)

**Goal**: the developer can declare the reason a condition refuses with, and an object-scoped refusal never tells the caller whether the object exists.

**Independent test**: declare a `reason=` beside a `when=` and beside a `guard=`; see the declared reason arrive at the caller. Answer `FORBIDDEN_OBJECT` for a missing object and for another caller's object; the two answers are identical.

### Tests for User Story 2

- [ ] T022 [P] [US2] Write the declared-reason tests in `packages/aoa-action-machine/tests/action_machine/intents/check_roles/test_reason_validation.py` — `reason=` without a condition raises at declaration time; a condition without `reason=` defaults to `FORBIDDEN_GRANT` or `FORBIDDEN_GUARD`; an `async` condition raises `AccessConditionAsyncError` (FR-010, FR-012)
- [ ] T023 [P] [US2] Write the graph-property tests in `packages/aoa-action-machine/tests/action_machine/graph/test_declared_reasons.py` — `properties["when_reason"]` and `properties["guard_reason"]` carry what was declared (FR-010)
- [ ] T024 [US2] Write the indistinguishability test in `packages/aoa-action-machine/tests/action_machine/intents/access_control/test_object_answer.py` — at least 10 sampled object-scoped refusals, each pair identical in `kind`, `gate` and `reason`, and both decided from one branch (FR-011, SC-003)

### Implementation for User Story 2

- [ ] T025 [P] [US2] Create the validator in `packages/aoa-action-machine/src/aoa/action_machine/intents/check_roles/reason_validation.py` — `require_reason_alongside(...)`: a `reason=` with no condition is a `ValueError`; a condition with no `reason=` is defaulted (FR-010, FR-012)
- [ ] T026 [P] [US2] Carry the declared `when=` reason through `packages/aoa-action-machine/src/aoa/action_machine/intents/check_roles/grant.py` (FR-010)
- [ ] T027 [P] [US2] Carry the declared `guard=` reason through `packages/aoa-action-machine/src/aoa/action_machine/intents/check_roles/check_roles_decorator.py` (FR-010)
- [ ] T028 [US2] Pass both through `packages/aoa-action-machine/src/aoa/action_machine/intents/check_roles/check_roles_intent_resolver.py` (FR-010)
- [ ] T029 [US2] Put the reason on the graph in `packages/aoa-action-machine/src/aoa/action_machine/graph/edges/role_graph_edge.py` — `properties["when_reason"]` (FR-010)
- [ ] T030 [US2] Put the reason on the graph in `packages/aoa-action-machine/src/aoa/action_machine/graph/nodes/action_graph_node.py` — `properties["guard_reason"]` (FR-010)
- [ ] T031 [US2] Report the declared reason, and the default only when none was declared, in `condition_gate` — `packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/cascade.py` (FR-010, FR-012)

**Checkpoint**: US2 is independently testable — reasons are the developer's, and object answers leak nothing.

---

## Phase 5: User Story 3 - A gate that cannot complete is not a refusal, and every decision is published (Priority: P3)

**Goal**: a failed gate is a different answer with a different outcome, and both the decision and the failure are observable as events.

**Independent test**: make one gate fail; the answer is `undecided` with `EVALUATION_FAILED`, a failed-gate event is published carrying the failure's type, and no answer and no event carries the failure's text.

### Tests for User Story 3

- [ ] T032 [P] [US3] Write the exception tests in `packages/aoa-action-machine/tests/action_machine/exceptions/test_access_denied.py` and `.../test_access_undecided.py` — the exception carries the verdict and nothing else; the failure's text is absent from the verdict and from the exception's message (FR-005, FR-016, SC-007)
- [ ] T033 [P] [US3] Write the event tests in `packages/aoa-action-machine/tests/action_machine/runtime/test_access_events.py` — with an in-memory exporter: one decision, one decision event; a failed gate, two events; zero start/finish events on the question path; the request identity (`context.request.trace_id`, absent when the context has none) present in the event only when it is set; no failure text in any attribute (FR-013, FR-014, FR-016, FR-017, SC-001, SC-007, SC-008)
- [ ] T034 [P] [US3] Write the persistence test in `packages/aoa-action-machine/tests/action_machine/runtime/test_undecided_is_not_a_refusal.py` — a gate that fails yields `undecided`; the same call made again is decided afresh rather than answered from the first result; and no path returns that answer as `refused` (FR-006, SC-004)
- [ ] T035 [P] [US3] Write the addition test in `packages/aoa-action-machine/tests/action_machine/plugin/test_new_events_are_additions.py` — the names and the payloads of every event that existed before this feature are unchanged, and a plugin subscribed to none of the new events behaves exactly as it did (FR-015)
- [ ] T036 [US3] Write the adapter tests in `packages/aoa-fastapi-adapter/tests/` and `packages/aoa-mcp-adapter/tests/` — a refusal still comes back as a refusal rather than as an unhandled error (FR-004)

### Implementation for User Story 3

- [ ] T037 [P] [US3] Create `packages/aoa-action-machine/src/aoa/action_machine/exceptions/access_denied.py` — `AccessDenied(verdict: Refused)` (FR-005)
- [ ] T038 [P] [US3] Create `packages/aoa-action-machine/src/aoa/action_machine/exceptions/access_undecided.py` — `AccessUndecided(verdict: Undecided)`, raised `from verdict._cause` (FR-005, FR-016)
- [ ] T039 [US3] Raise the new exceptions from `packages/aoa-action-machine/src/aoa/action_machine/runtime/action_product_machine.py`, and drop the remaining raises of `AuthorizationError` in the core (FR-005)
- [ ] T040 [P] [US3] Create the events in `packages/aoa-action-machine/src/aoa/action_machine/plugin/core/events.py` — `AccessDecidedEvent` (answer, path, request identity) and `AccessGateFailedEvent` (failure kind, request identity); additions only (FR-013, FR-014, FR-015)
- [ ] T041 [P] [US3] Create the emitters in `packages/aoa-action-machine/src/aoa/action_machine/plugin/core/plugin_coordinator.py` — `emit_access_decided`, `emit_access_gate_failed` (FR-013, FR-014)
- [ ] T042 [US3] Handle the decision event in `packages/aoa-otel/src/aoa/otel/plugin/open_telemetry_plugin.py` — write the record with its attributes, including `aoa.trace_id` from `context.request.trace_id` when it is set; write nothing when no logger provider is configured (FR-013)
- [ ] T043 [US3] Switch the `except` clauses to the new exceptions in `packages/aoa-fastapi-adapter/src/aoa/fastapi/adapter.py` and `packages/aoa-mcp-adapter/src/aoa/mcp/adapter.py` — nothing else in either adapter changes: no status codes, no bodies, no headers (FR-004)

**Checkpoint**: US3 is independently testable — a broken gate is visible as itself, and every decision is on the record.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T044 Remove what the new design replaced: `packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/access_verdict.py` with its tests, and the batch form of the question — `packages/aoa-action-machine/src/aoa/action_machine/exceptions/check_access_decide_batch_size_exceeded_error.py` with its tests and its export, since the core now answers one call at a time and an unreferenced class is what the closing check run's dead-code step reports. Leave `packages/aoa-action-machine/src/aoa/action_machine/exceptions/authorization_error.py` in the tree for the transport follow-up
- [ ] T045 Update the documentation that describes the old behaviour — the tutorial chapters on roles, the machine and the "may I?" question under `docs/tutorials/`, `docs/reference/glossary.md`, and the breaking-change entry in `CHANGELOG.md`
- [ ] T046 Run the adversarial checks from issue #189 in `packages/aoa-action-machine/tests/action_machine/` — break the code the way each named test must catch, confirm that test fails and no other does, restore; record the outcome on the issue
- [ ] T047 Run the closing gate and fix everything it reports — `bash scripts/run_checks_with_log.sh` (log in `archive/logs/check-all.txt`)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependency; T002 must precede any change to the machine
- **Foundational (Phase 2)**: needs T002; blocks every user story
- **US1 (Phase 3)**: needs Phase 2 — it is the MVP
- **US2 (Phase 4)**: needs Phase 2; its condition-gate task (T031) touches the same file as US1's cascade, so US2 lands after US1
- **US3 (Phase 5)**: needs Phase 2 and the answer the execution path raises (US1, T017); its adapter task (T043) needs T039
- **Polish (Phase 6)**: after all three stories; T047 is always last

### Within Each Story

- Tests before implementation, as in issue #189: the tests are written against the behaviour being replaced, then switched to the new code
- Vocabulary → cascade → machine → paths
- Every phase ends with the package's suite green, and a commit only on the maintainer's instruction

### Parallel Opportunities

- Phase 2: T003, T004, T005 are independent files
- Phase 4: T022, T023 in tests and T025, T026, T027 in source are independent files
- Phase 5: T032, T033, T034, T035 in tests and T037, T038, T040, T041 in source are independent files

---

## Parallel Example: User Story 2

```bash
# tests first, different files:
Task: "Write the declared-reason tests in packages/aoa-action-machine/tests/action_machine/intents/check_roles/test_reason_validation.py"
Task: "Write the graph-property tests in packages/aoa-action-machine/tests/action_machine/graph/test_declared_reasons.py"

# then the three source files that carry the reason:
Task: "Create the validator in packages/aoa-action-machine/src/aoa/action_machine/intents/check_roles/reason_validation.py"
Task: "Carry the declared when= reason through .../check_roles/grant.py"
Task: "Carry the declared guard= reason through .../check_roles/check_roles_decorator.py"
```

## Parallel Example: User Story 3

```bash
Task: "Create .../exceptions/access_denied.py"
Task: "Create .../exceptions/access_undecided.py"
Task: "Create the events in .../plugin/core/events.py"
Task: "Create the emitters in .../plugin/core/plugin_coordinator.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

Phases 1–3 deliver the capability's value: one declaration, one cascade, both paths, the fixed order and the reasons the framework itself answers with. Everything after that sharpens it: developer-declared reasons (US2), and failed gates plus observability (US3).

### Incremental Delivery

1. Phases 1–3 → US1 testable: declare, ask, execute, agree
2. Phase 4 → US2 testable: declared reasons, indistinguishable object answers
3. Phase 5 → US3 testable: failed gates and the two events
4. Phase 6 → the old module gone, documentation current, the check run clean

### Notes

- Commits: one phase, one commit — and only when the maintainer asks for it in that turn
- The single out-of-package touch is the two adapters' `except` clauses (T043); everything else stays inside `packages/aoa-action-machine`, apart from the OpenTelemetry handler (T042)
- The closing check run is not optional: it is the last step of the work (constitution, "Final step: the check run")
