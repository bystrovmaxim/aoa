# Tasks: What goes out comes back in

**Input**: `specs/064-round-trip/` — spec.md, plan.md, research.md

**Tests**: required. **Commits**: one phase = one commit; after a phase only its test files run.

## Phase 1: The build check (US1) — one commit

- [X] T001 [US1] Write `packages/aoa-action-machine/tests/action_machine/graph/test_json_form_validator.py`: a Result field `raw: Opaque` refused at graph build naming `OpaqueAction.Result.raw`; the same on Params; a field whose schema fails only in serialization mode refused; `JsonSchemaValue`, a projection, an entity, a lifecycle and relations pass.
- [X] T002 Confirm T001 fails on today's code.
- [X] T003 Create `graph/validators/json_form_validator.py` (R1) with `JsonFormError`; call it from `NodeGraphCoordinator.build`; notes and AI-CORE.
- [X] T004 Run the phase's tests and the package's graph tests; adversarial breaks of plan phase 1.

## Phase 2: Observable state and read-back (US2, US3) — one commit

- [X] T005 [US2] Write `tests/action_machine/model/test_observable_state.py`: the pairs of US2 (case 8.2 included) and the same-state pairs.
- [X] T006 [US3] Write `tests/action_machine/model/test_result_round_trip.py`: Results with relations (loaded, not loaded, zero rows), a lifecycle, a dictionary reference, a partial target and a projection read back with no difference.
- [X] T007 Create `domain/observable_state.py` (R2); export `observable_difference` from `aoa.action_machine.domain`.
- [X] T008 [US3] Create `tests/examples/round_trip_runner.py` (R3); `tests/examples/test_examples_run.py` runs each example through it; a test of the runner refuses a script whose Result reads back different.
- [X] T009 [US3] Write `packages/aoa-demo/tests/model/test_result_round_trip.py` (R4).
- [X] T010 Run the phase's tests; adversarial breaks of plan phase 2.

## Phase 3: Versions — one commit

- [ ] T011 Raise `aoa-action-machine`; `uv lock`.

## Phase 4: Closing check run — one commit if it changes anything

- [ ] T012 `bash scripts/run_checks_with_log.sh` to zero.

## Phase 5: Documentation — one commit

- [ ] T013 The page on the checks and the page on Params and Result: what the build refuses, what rule 2 is and where it is checked; Russian drafts.

## Phase 6: Changelog — one commit

- [ ] T014 One article and its Russian version.
