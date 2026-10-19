---

description: "Task list for #233 — a role's mode is refused where it is declared"
---

# Tasks: A role's mode is refused where it is declared, not where it is read

**Input**: Design documents from `specs/011-role-mode-declaration/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: included — the spec requires them (`FR-016`) and the repository verifies adversarially (`AGENTS.md`): each test is proved by breaking the code the way it must catch.

**Organization**: tasks are grouped by the spec's three user stories. In this feature the three stories share one source file and land in **one commit** (plan phase 1); the story labels exist so each can be verified on its own and so the adversarial proofs stay attached to the rule they defend. The tail — the check run, the documentation, the changelog — is exactly three tasks, one commit each (constitution VI.8).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: `US1`, `US2`, `US3` — the spec's user stories
- Every task names the file it touches

## Path Conventions

- Source: `packages/aoa-action-machine/src/aoa/action_machine/`
- Tests: `packages/aoa-action-machine/tests/action_machine/`
- Docs: `docs/reference/`, `docs/CHANGELOG.md`, `examples/step_03_authorization_and_roles/`
- The tests run with the repository environment; in this sandbox `uv run` cannot write its cache, so `.venv/bin/pytest` and `UV_CACHE_DIR=.uv-cache uv run …` are the equivalents of the commands in `quickstart.md`.

---

## Phase 1: Setup (baseline, read-only — no commit)

**Purpose**: record the tree the change starts from, so every later claim has a "before".

- [ ] T001 Run the baseline: `python3 specs/011-role-mode-declaration/evidence/scan_role_mode_calls.py` (expect `real calls: 69`, `placeholders in prose: 4`, `0` unknown arguments, exit 0) and `.venv/bin/pytest packages/aoa-action-machine/tests/action_machine/intents/check_roles packages/aoa-action-machine/tests/action_machine/intents/access_control packages/aoa-action-machine/tests/action_machine/scenarios/intents_with_runtime -q` (expect green). Record both outputs for the report.

**Checkpoint**: the starting numbers are in hand; nothing has changed.

---

## Phase 2: User Story 1 — a wrong mode is refused where it is written (Priority: P1) 🎯 MVP

**Goal**: `@role_mode` refuses an argument that is not a `RoleMode` member, and refuses the missing-parentheses form, with `RoleModeDeclarationError` naming the role, the value and all four members (`FR-001`…`FR-007`, `FR-019`, `FR-020`).

**Independent Test**: a module declaring `@role_mode("alive")` fails to import, before any graph; the message contains the role, `'alive'` and `ALIVE, DEPRECATED, SILENCED, UNUSED`; `@role_mode` without parentheses fails the same way instead of producing `TypeError: issubclass() arg 1 must be a class`.

### Tests for User Story 1 (write first; they must fail)

- [ ] T002 [P] [US1] Create `packages/aoa-action-machine/tests/action_machine/intents/role_mode/test_role_mode_decorator_invariants.py` with the refusal tests: `"alive"`, `RoleMode.ALIVE.value`, `42`, `None`, `object()`, a member of a foreign `Enum` whose value is `"alive"`, the keyword form `mode="alive"`, and `@role_mode` without parentheses (`SC-001`, `SC-002`). For each, declare the role with `exec` inside `pytest.raises(RoleModeDeclarationError)` and assert the name is absent from the `exec` namespace afterwards (the class is never bound). Assert the message content, not only the type (`FR-003`, `FR-004`, `SC-002`): the role's `__qualname__`, the value in `repr` (`None` vs `'None'`, `42` vs `'42'`), the decorator name, and — for every refusal, the bare form included (`FR-020`) — the four names in the order `ALIVE, DEPRECATED, SILENCED, UNUSED` (one assertion on the ordered substring, not four independent checks). Assert the bare-form message states the missing parentheses. Confirm all of them fail on the current tree for the wrong reason (accepted / `issubclass()` `TypeError`).

### Implementation for User Story 1

- [ ] T003 [P] [US1] In `packages/aoa-action-machine/src/aoa/action_machine/intents/role_mode/role_mode_decorator.py` add the module-level `_ALLOWED_MODES = ", ".join(member.name for member in RoleMode)` (after the enum) and an `AI-CORE-BEGIN/ROLE/CONTRACT/INVARIANTS/AI-CORE-END` block inside `role_mode`'s docstring stating the closed set (principle IV; research R6). In `packages/aoa-action-machine/src/aoa/action_machine/exceptions/role_mode_declaration_error.py` widen the docstring so it also covers the argument handed to `@role_mode` and give it the same `AI-CORE-BEGIN/ROLE/CONTRACT/INVARIANTS/AI-CORE-END` block — the shape `missing_check_roles_error.py` already has — leaving the class, its base and its name untouched (`FR-002`; plan phase 1).
- [ ] T004 [US1] In the same file add the set check inside the returned `decorator(cls)`, after the existing `isinstance(cls, type)` target check and **before** `cast(Any, cls)._role_mode_info = {"mode": mode}`: `not isinstance(mode, RoleMode)` → `RoleModeDeclarationError(f"@role_mode({cls.__qualname__}): expected a RoleMode member, got {mode!r}. Allowed: {_ALLOWED_MODES}.")` (`contracts/refusals.md`, refusal 1).
- [ ] T005 [US1] In the same file add the missing-parentheses check at the top of `role_mode(mode)` itself: `isinstance(mode, type)` → `RoleModeDeclarationError(f"@role_mode: expected a RoleMode member, got the class {mode.__qualname__} itself — did you mean @role_mode(RoleMode.ALIVE)? Allowed: {_ALLOWED_MODES}.")` (`contracts/refusals.md`, refusal 2). Keep `mode: RoleMode` as annotated.
- [ ] T006 [US1] Run T002's tests: green. Then prove them adversarially, restoring the file after each break: (a) delete the set check → refusal tests for the seven argument kinds fail; (b) move the set check into `RoleMode.declared_for` → the "refused at import, no assembly" tests fail; (c) drop the value from the message → the value assertions fail; (d) print three members → the four-name assertion fails; (e) delete the missing-parentheses check → the bare-form test sees `TypeError: issubclass() arg 1 must be a class`; (f) assign `_role_mode_info` before the check → the no-metadata test fails (`FR-006`). Confirm in each case that the failure is confined to the named tests.

**Checkpoint**: US1 is complete and independently demonstrable by importing one wrong declaration.

---

## Phase 3: User Story 2 — all four members are accepted and stored as given (Priority: P2)

**Goal**: the check narrows nothing: the four members are accepted and stored by identity, and the decorated class is returned unchanged (`FR-008`, `FR-009`).

**Independent Test**: one role per member, each asserting `_role_mode_info["mode"] is the member`; the decorator returns the same class object; no metadata is written when the argument is refused.

### Tests for User Story 2

- [ ] T007 [US2] In `test_role_mode_decorator_invariants.py` add one test per member (`ALIVE`, `DEPRECATED`, `SILENCED`, `UNUSED`) asserting `_role_mode_info["mode"] is member` (identity, not equality) and one asserting the decorator returns the very class it was given.
- [ ] T008 [US2] In the same module add the no-metadata-on-refusal test: `decorator = role_mode("alive")`, apply it to a class by hand inside `pytest.raises`, and assert the class carries no `_role_mode_info` (`FR-005`; not observable through decorator syntax, where the class is never bound).
- [ ] T009 [US2] Run T007 and T008: green. Then break the storage (`{"mode": mode.value}` instead of `{"mode": mode}`) and confirm T007's identity tests fail alone; restore.

**Checkpoint**: the accepted side is proved to be unchanged.

---

## Phase 4: User Story 3 — the protections that existed stay (Priority: P3)

**Goal**: `declared_for` keeps both refusals with their wording, and the three context rules keep their errors and warnings (`FR-010`…`FR-013`).

**Independent Test**: a role with no metadata and a role whose metadata was overwritten both still raise `RoleModeDeclarationError` from `declared_for`; the existing context-rule tests are untouched and green.

### Tests for User Story 3

- [ ] T010 [US3] In `test_role_mode_decorator_invariants.py` add `declared_for`'s two guards: a `RoleModeIntent` subclass with no `@role_mode` anywhere in its MRO → "has no `_role_mode_info`"; a role whose `_role_mode_info["mode"]` was replaced with `"alive"` → "has invalid `_role_mode_info['mode']`". Assert the substrings that identify each case, and that neither message carries the list of four (`FR-010`, clarification 2).
- [ ] T011 [P] [US3] Run the two files that own the context rules unchanged — `packages/aoa-action-machine/tests/action_machine/scenarios/intents_with_runtime/test_role_checker_pr2.py` (`UNUSED` → `RoleSpecTypeError`, `DEPRECATED` → warning) and `packages/aoa-action-machine/tests/action_machine/intents/access_control/test_roles.py` (`SILENCED` grants nothing) — and confirm they are green with no edit to either file (`FR-011`, `FR-012`, `SC-004`).
- [ ] T012 [US3] Prove T010 adversarially: delete the `isinstance(raw, RoleMode)` check in `RoleMode.declared_for` → the corrupted-metadata test fails alone; restore. Confirm the check written by US1 does not rescue it (the metadata is written after the decorator, so only `declared_for` sees it).

**Checkpoint**: all three stories are done; the first commit is complete.

---

## Phase 5: The tail — exactly three steps, in this order (constitution VI)

> **NOTE**: each of these is its own commit, and no task above may absorb one of them.

- [ ] T013 The check run to zero: walk `quickstart.md` steps 1–4 by hand (scan, the two-refusal script, the feature's suite, the adversarial table), then run `bash scripts/run_checks_with_log.sh` and fix every remark it reports. The two accepted remarks (the Vite chunk-size advisory and LangGraph's pending deprecation) stay. Three checks belong to this task because only a whole-tree run can make them: (a) `git diff` touches none of the four prose placeholders and no declaration site, so `FR-014`/`FR-015` hold and `SC-003` is met; (b) the public exception namespace gained no name — `git diff packages/aoa-action-machine/src/aoa/action_machine/exceptions/__init__.py` is empty (`SC-005`); (c) the demo model's roles, which carry the four modes, still import through the suite (`SC-004`). Paste the tail of the log into the report.
- [ ] T014 The documentation: add the invariant under `## Mandatory roles` in `docs/reference/intents-and-invariants.md` — the four members, a wrong argument refused at the declaration, the context rules that stay with their consumers — and the same text in `docs/reference/intents-and-invariants.ru_draft.md` (gitignored, reported as a link). Then write the example pair `examples/step_03_authorization_and_roles/17_a_wrong_role_mode.py` and `17_a_wrong_role_mode.ipynb`: the accepted declaration, the string refused, the missing parentheses refused, each printed from a real run (constitution VI.4–VI.6, `FR-017`). Execute the script and the notebook, and paste their output into the report.
- [ ] T015 The changelog: one article at the top of `docs/CHANGELOG.md`, dated `2026-10-19`, in the form the existing dated entries use — what a reader can now rely on (a wrong role mode is visible where it is declared, the message names the four), no file list, no technical detail (`FR-018`).

**Checkpoint**: the change is finished by the repository's own definition.

---

## Dependencies & Execution Order

### Phase dependencies

- **Phase 1 (baseline)** — no dependency; read-only.
- **Phase 2 (US1)** — after T001. T003 touches two files (the decorator and the exception) and runs before T004 → T005, which edit one file in that order; T002 must exist before T004–T005 are believed, and T006 closes the phase.
- **Phase 3 (US2)** — after T004 exists (the check it proves narrows nothing). T007/T008 touch the test module created in T002 and run after it; T009 after both.
- **Phase 4 (US3)** — after T005 (the decorator must be in place before "the old guard still works" means anything). T011 has no code dependency and can run any time after T001.
- **Phase 5 (tail)** — T013 → T014 → T015, strictly, and all three after T006/T009/T012.

### Commit boundary

T002–T012 are **one** commit: the plan's phase 1. Splitting them would leave the tree with a rule its tests do not cover (T002–T005 alone) or with metadata written before the check (T004 without T005). T013, T014 and T015 are three further commits, one each.

### Story independence

- **US1** is demonstrable alone: import a wrong declaration.
- **US2** is demonstrable alone: one role per member, metadata identical.
- **US3** is demonstrable alone: `declared_for` on a role with no or corrupted metadata, plus the untouched context tests.

### Parallel opportunities

- T003 and T002 touch different files and can run together (tests first, then the implementation they judge).
- T011 is independent of every source task after T001.
- Within one story, tasks share a file (the test module, the decorator) and are **not** marked `[P]`.

---

## Parallel Example: User Story 1

```bash
# One pair that can start together: the tests and the constant they will assert on.
Task: "T002 refusal tests in tests/action_machine/intents/role_mode/test_role_mode_decorator_invariants.py"
Task: "T003 _ALLOWED_MODES and the AI-CORE block in intents/role_mode/role_mode_decorator.py"

# Then, strictly in order, both in the same file:
Task: "T004 the set check in decorator(cls)"
Task: "T005 the missing-parentheses check in role_mode(mode)"
```

---

## Implementation Strategy

### MVP first (US1 alone)

1. T001 baseline → 2. T002 tests (red) → 3. T003–T005 checks → 4. T006 adversarial proof → 5. **STOP and validate**: `@role_mode("alive")` fails at import with the four names; `@role_mode` without parentheses fails with the parentheses sentence.

### Incremental delivery

1. US1 → the defect is closed.
2. US2 → the accepted side is proved unchanged (no new code).
3. US3 → the old guards are proved intact (no new code).
4. The tail: the check run, the documentation (reference page + runnable example pair), the changelog.

### Parallel team strategy

Not applicable: one source file, one test module. The only genuine parallelism is T002 ∥ T003 and T011 alongside Phase 3.

---

## Notes

- Every test is written before the code it judges and is proved by a break, per `AGENTS.md`; the six breaks are listed in T006, T009 and T012 and in `quickstart.md` step 4.
- Do not touch the four prose placeholders (`@role_mode(...)`, `@role_mode(RoleMode.…)`): they are text, not calls (`FR-015`).
- Do not move `UNUSED`/`DEPRECATED`/`SILENCED` rules into the decorator (`FR-011`) and do not rename or re-word `declared_for`'s messages (`FR-010`).
- Do not edit `.specify/memory/constitution.md`, and do not commit anything without the maintainer's instruction (principle I).
- The 69 declaration sites need no edit; if the scan shows a non-member argument, the tree changed, not the rule (`FR-014`).
