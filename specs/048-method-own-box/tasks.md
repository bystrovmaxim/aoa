---
description: "Tasks — every method of an action gets its own box"
---

# Tasks: Every method of an action gets its own box

**Input**: Design documents from `specs/048-method-own-box/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/method-box.md, quickstart.md

**Tests**: Included. FR-008 requires them, and each is verified adversarially.

**Organization**: One phase = one commit (repository rule). Phases follow the issue's order. Stories 1 and 2 are independent of each other; Story 3 needs both. The names in Story 2 are asserted in Phase 3, by the rule's test, so that each break fails exactly one test (plan.md).

**Commits**: Each commit waits for the maintainer's instruction (Principle I). "Commit point" below marks where one belongs; it does not authorize it. After each commit the matching checkbox of issue #331 is ticked. The first commit carries `specs/048-method-own-box/`.

**Paths**: Relative to the worktree `/Users/bystrovmaxim/PythonDev/aoa-issue-331`. `RT` below means `packages/aoa-action-machine/src/aoa/action_machine/runtime`, and `TEST` means `packages/aoa-action-machine/tests/action_machine/runtime/test_every_method_has_its_own_box.py`.

**Test command**: `uv run --package aoa-action-machine --group dev pytest <path> -q`

---

## Phase 1: User Story 1 — A log line in an error handler sees the handler's state (Priority: P1)

**Goal**: `@on_error` gets its own `box` with its `state`, through one function that all named kinds use. Issue phase 1.

**Independent Test**: A later aspect fails; the handler logs `{%state.reserved}`; the run returns the handler's result and the line carries `yes`.

- [X] T001 [US1] Create `TEST` with its path header and module docstring: a recording logger subclassing `BaseLogger` that keeps `scope`, `state` and the message of each line, and the probe action of `quickstart.md` (`@check_roles(GuestRole)`, a regular aspect writing `reserved`, a later aspect that raises, a summary, an `@on_error` handler). Write the test for acceptance scenario 1 and confirm it fails with `OnErrorHandlerError` before any source edit
- [X] T002 [US1] Add to `TEST` the failure in the summary aspect (scenario 2) and the absent field (scenario 3: a failure in the first aspect, `OnErrorHandlerError` still raised)
- [X] T003 [US1] Add to `TEST` a handler that runs a nested action and resolves a dependency through its `box`, and a handler declared with `@context_requires` that logs `state` (scenario 4 and the edge case), plus an error with no matching handler, which goes up unchanged
- [X] T004 [US1] Create `RT/method_box.py` with its path header and module docstring, and the function `method_box(box, *, coordinator, action, method_name, context, state, params) -> ToolsBox` as in `data-model.md`: it builds `ScopedLogger(coordinator=coordinator, nest_level=box.nested_level, action_name=action.get_full_class_name(), aspect_name=method_name, context=context, state=state, params=params, domain=resolve_domain(type(action)))` and a `ToolsBox` copying `run_child`, `factory`, `resources`, `nested_level`, `rollup`, reading nothing else from `box` (research R5). Do not export it from any package `__init__`
- [X] T005 [US1] Replace the hand-built logger and box in `AspectExecutor.call_aspect` with `method_box` in `RT/aspect_executor.py`; drop the imports that become unused
- [X] T006 [US1] Replace the hand-built logger and box in the compensator branch with `method_box` in `RT/saga_coordinator.py`, keeping the `isinstance(frame.state_before, BaseState)` guard; drop the imports that become unused
- [X] T007 [US1] In `ErrorHandlerExecutor.handle` in `RT/error_handler_executor.py`, after a handler is chosen and before it is called, prepare `handler_box = method_box(box, coordinator=self._plugin_coordinator.log_coordinator, action=action, method_name=handler_name, context=context, state=state, params=params)` and pass it in both calls; add the step to the data-flow diagram in the module docstring. The no-handler path prepares nothing
- [X] T008 [US1] Run `TEST` and all of `packages/aoa-action-machine/tests/action_machine/runtime/`; `test_aspect_executor.py` and `test_error_handler_executor.py` must pass unedited
- [X] T009 [US1] Adversarial break 6 of `quickstart.md`: pass an empty `BaseState()` in T007; confirm the state test fails and no other does; restore
- [X] T010 [US1] Run `bash scripts/check_before_commit.sh` to exit code 0. **Commit point**: `fix(runtime): an error handler gets its own box and state (#331)`

**Checkpoint**: The crash from the issue is gone. All named kinds go through one function.

---

## Phase 2: User Story 2 — `@access_decide` gets its own box (Priority: P1)

**Goal**: `@access_decide` gets its own `box` on both paths. Issue phase 2.

**Independent Test**: The tests of this phase pass before and after the source edit, because they guard what must not change. The proof that the name arrived is Phase 3's rule test.

- [X] T011 [US2] Add to `TEST` an action with `@access_decide` that logs, on both paths (`run` and `check_access_decide`): the line's `state` is empty (scenarios 2 and 3 for `state`), and the answers `Allowed`, `Refused` and `Undecided` stay what they are
- [X] T012 [US2] Add to `TEST` a check that logs `{%state.x}`: the answer is `Undecided` with `gate=Gate.ACCESS_DECIDE` (scenario 5), on both paths; and a check declared with `@context_requires` that logs and receives its view (edge case)
- [X] T013 [US2] In `RT/action_product_machine.py`, give `_decide` a keyword `check_name: str | None = None`. With a name it passes `method_box(box, coordinator=self._log_coordinator, action=action, method_name=check_name, context=context, state=BaseState(), params=params)` to `decide`; without one it passes `box` on. The docstring says why only the object step has a method to name
- [X] T014 [US2] Pass `check_name=check_name` in the two `gates=GATES_AT_OBJECT` calls in `check_access_decide` and `_run_internal` in `RT/action_product_machine.py`. The `GATES_BEFORE_RUN` calls stay as they are
- [X] T015 [US2] Correct the `ToolsBox` class docstring in `RT/tools_box.py`: it says "One instance per nesting level"; a box now belongs to one method call
- [X] T016 [US2] Run all of `packages/aoa-action-machine/tests/action_machine/runtime/` and `packages/aoa-action-machine/tests/action_machine/intents/access_decide/`
- [X] T017 [US2] Run `bash scripts/check_before_commit.sh` to exit code 0. **Commit point**: `fix(runtime): an access check gets its own box (#331)`

**Checkpoint**: All five kinds have their own `box`.

---

## Phase 3: User Story 3 — The rule cannot quietly come apart again (Priority: P2)

**Goal**: One test states the rule for all five kinds and carries the name assertions of User Story 2. Issue phase 3.

**Independent Test**: Run `TEST`, then the breaks in `quickstart.md`.

- [X] T018 [US3] Add to `TEST` one action with all five kinds of method, each writing one line, and a parametrized rule test with one case per kind and two for `@access_decide` (`run`, `check_access_decide`): `f"{scope.action}:{scope.aspect}"` is found in the graph through the machine's coordinator, and the node's type is that kind's `NODE_TYPE` (`RegularAspect`, `SummaryAspect`, `Compensator`, `error_handler`, `AccessDecide`)
- [X] T019 [US3] Add to `TEST`: with several handlers on one action, the line names the chosen one, never the failed aspect (US2 scenarios 1 and 4); a nested action's handler names itself at the nested level (edge case); and the compensator's `state` in the log is the snapshot before its step (US3 scenario 3)
- [X] T020 [US3] Adversarial breaks 1 to 5 and 7 of `quickstart.md`, one at a time, each restored before the next. Confirm the named case fails and nothing else in `packages/aoa-action-machine/tests/` does. Record each result for the report; a break that fails another test is reported with that test's name
- [X] T021 [US3] Run `bash scripts/check_before_commit.sh` to exit code 0. **Commit point**: `test(runtime): every method's box names a node of the graph (#331)`

**Checkpoint**: The rule is a test.

---

## Phase 4: Closing check run

- [X] T022 Run `bash scripts/check_before_commit.sh` and take every remark to zero, the two accepted remarks of the constitution aside. **Commit point** only if the run changed something: `chore: the check run is clean (#331)`. `bash scripts/check_before_pr.sh` runs on the pushed commit, when the maintainer asks for the pull request

---

## Phase 5: Documentation

- [X] T023 Write the documentation, every example executed as it is written (FR-009, Principle VI): the rule and the five-kind table of `contracts/method-box.md`, with each case named, as a new section after the signature table in `docs/reference/intents-and-invariants.md`; correct "passed into every aspect" in the `box` entry of `docs/reference/glossary.md`; a short passage on the handler's `state` beside the handler's log in `docs/tutorials/step-05-error-handling.md`; every case as a script and as a notebook, `examples/how_to/09_method_box.py` and `examples/how_to/09_method_box.ipynb`, printing what each case gives: the handler's log reading `state`, the absent field, the name on both paths of `@access_decide`, `{%state.x}` in a check. Check the page for what it claims by running it. **Commit point**: `docs: every method of an action gets its own box (#331)`

---

## Phase 6: Changelog

- [X] T024 Write one article in `docs/CHANGELOG.md`: what an action's author can now do, in plain words, with the one nuance a logger's author needs (lines from handlers and access checks now carry a name). No technical detail and no list of files. **Commit point**: `docs: changelog — every method of an action gets its own box (#331)`

---

## Dependencies

- Phase 1 first: `method_box` is needed by Phase 2.
- Phase 3 needs Phases 1 and 2: the rule's test has no green state before them.
- Phases 4, 5, 6 come last, in that order (Principle VI).

## Parallel Opportunities

None worth taking. The test tasks share one file, and the source tasks follow a strict order. No task carries `[P]`.

## Implementation Strategy

**MVP**: Phase 1 removes the crash on its own. The work is finished only after Phase 6. The plan stops at the changelog: no release, version bump or publishing.

---

## Phase 7: Convergence

- [X] T025 CRITICAL: show the four cases still missing from the documentation, each as script, notebook and reference case: several handlers (the line names the one that ran), a nested action's handler (its own action and nesting level), a handler and a check with `@context_requires` (the view and the own box together), an error with no matching handler (goes up, no handler's box is prepared), in `examples/how_to/09_method_box.py`, `examples/how_to/09_method_box.ipynb` and `docs/reference/intents-and-invariants.md`, executing them as they are written, per Constitution VI, FR-009 (partial)
- [X] T026 Reword SC-004 in `specs/048-method-own-box/spec.md`: it says no file of an action, example or tutorial changes, while the plan adds an example and a passage in `docs/tutorials/step-05-error-handling.md`; what must not change is the code of existing actions and examples, per SC-004 (contradicts)
