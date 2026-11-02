---
description: "Tasks — typed events, @emits and the domain vocabulary"
---

# Tasks: Typed events, `@emits` and the domain vocabulary

**Input**: Design documents from `specs/049-base-event-core/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/typed-events.md, quickstart.md

**Tests**: Included. FR-031 requires them, and each rule is verified adversarially. In every phase the tests come first and must fail before the code is written.

**Organization**: One phase = one commit (repository rule). Phases follow the order of issue #333. Stories 1 to 4 build on each other in that order; Story 5 documents them.

**Commits**: Each commit waits for the maintainer's instruction (Principle I). "Commit point" below marks where one belongs; it does not authorize it. After each commit the matching checkbox of issue #333 is ticked.

**Paths**: Relative to the repository root. `AM` means `packages/aoa-action-machine/src/aoa/action_machine`, `TESTS` means `packages/aoa-action-machine/tests/action_machine`, and `DEMO` means `packages/aoa-demo/src/aoa/demo/fastapi_mcp_services`.

**Test command**: `uv run --extra dev pytest <path> -q`

**Every new module** starts with its path and a module docstring with `PURPOSE` (Principle III). A public class carries an AI-CORE block (Principle IV), and every class, function and method a one-line docstring (Principle V). No `# type: ignore` and no `# pylint: disable` in production code.

---

## Phase 1: User Story 1 — The variables of a log line are a typed fact (Priority: P1)

**Goal**: `BaseEvent` with its system fields, and `box` accepts it in place of `kwargs`. Issue phase 1.

**Independent Test**: Emit an event with no switch on through each of the three tools and read what a recording logger received.

- [X] T001 [P] [US1] Create `TESTS/model/test_base_event.py`: a wrong type and an extra field fail; a built event cannot be changed; a name without `Event` raises `NamingSuffixError`; each of `level`, `channels`, `domain`, `domain_name` declared by a subclass raises `EventContractError`, and each of `get`, `keys`, `values`, `items`, `resolve` too, with warnings turned into errors so that no pydantic warning comes first; an author setting a system field, even to `None`, raises `ValidationError`; a dump holds every field except the system fields, including a field from an intermediate event class
- [X] T002 [P] [US1] Create `TESTS/intents/logging/test_event_line.py`: a recording logger subclassing `BaseLogger`, and for each of `info`, `warning`, `critical`: the rendered line, `var` of the event's own class, level, channels and domain filled in, the author's instance unchanged (scenarios 3 to 5 of US1)
- [X] T003 [US1] Add to `TESTS/intents/logging/test_event_line.py`: the eleven templates of `research.md` R12 rendered through `kwargs` and through an event, the same answer for ten and a masked `@sensitive` property for the eleventh; `{%state.*}`, `{%params.*}`, `{%context.*}`; subscriptions by channel, level and domain; a logger that reads `var` by key, working on both forms with no change
- [X] T004 [US1] Add to `TESTS/intents/logging/test_event_line.py` the refusals of the call with no switch on, each `EventContractError`: an event with `kwargs`, an event class, a dictionary, an instance of `BaseEvent` itself; and two things that must not be refused: a keyword named `event=` stays an ordinary variable, and a template with no variables and an event is delivered. Beside them, the form that stays: for each of the three tools a line with `kwargs` and a line with no variables are delivered, `var` is a `dict` holding those values and the system keys, and a reserved key in `kwargs` is still refused
- [X] T005 [US1] Create `TESTS/model/test_import_order.py`: in a fresh process for each, import first `context.context`, `context`, `auth`, `model`, `model.base_action`, `model.base_event`, `domain`, `domain.base_domain`, `logging`, `runtime.tools_box`, `runtime.action_product_machine`, `intents.aspects`, `graph.node_graph_coordinator_factory` and `testing.bench`, each under `aoa.action_machine`, then `BaseEvent` from its module
- [X] T006 [P] [US1] Create `AM/domain/event_marker.py` with `EventMarker`, a class with no content that marks event classes
- [X] T007 [P] [US1] Create `AM/exceptions/event_contract_error.py` with `EventContractError(TypeError)`, and export it wherever `AM/exceptions/__init__.py` exports its neighbours
- [X] T008 [US1] Create `AM/model/base_event.py` as in `data-model.md`: `BaseEvent(EventMarker, BaseSchema)` with `ConfigDict(frozen=True, extra="forbid")`; `level`, `channels`, `domain`, `domain_name`, each `Field(default=None, exclude=True)`; `__init_subclass__` for the suffix and the reserved names, read with `inspect.get_annotations(cls)`; a `model_validator(mode="before")` refusing a system name in the input. `BaseEvent` is imported from this module and is not exported from `AM/model/__init__.py`
- [X] T009 [US1] Add `type LogVar = Any` to `AM/logging/log_var_payloads.py`, and use it for `var` in `AM/logging/base_logger.py`, `log_coordinator.py`, `subscription.py`, `variable_substitutor.py` and `console_logger.py`. Change the annotations only
- [X] T010 [US1] Add `ScopedLogger.emit_event(log_level, channels, message, event)` in `AM/logging/scoped_logger.py`: validate the channels and the level, fill the four system fields with `event.model_copy(update=...)`, and pass the copy as `var` to `LogCoordinator.emit`, with the same scope, context, state, params and indent as `_emit`. `info`, `warning` and `critical` of `ScopedLogger` do not change
- [X] T011 [US1] Change `info`, `warning` and `critical` in `AM/runtime/tools_box.py` to `(self, channels, message, event=None, /, **kwargs)`. With an event: refuse `kwargs`, and refuse anything but an instance of a subclass of `BaseEvent`, then call `emit_event`. With no event: call the logger as now. Update the module docstring
- [X] T012 [US1] Run the two new test files, then all of `packages/aoa-action-machine/tests/`. No existing test may be edited
- [X] T013 [US1] Run `uv run --extra dev task typecheck`: every logger subclass declaring `var: dict[str, Any]` passes unchanged
- [X] T014 [US1] Adversarial breaks 1 to 8, 20, 21 and 24 to 26 of `quickstart.md`, one at a time, each restored before the next. Confirm the named test fails and no other does
- [X] T015 [US1] Run `bash scripts/check_before_commit.sh` to exit code 0. **Commit point**, with `specs/049-base-event-core/`: `feat(model): BaseEvent, a typed fact that box accepts (#333)`

**Checkpoint**: An event is the `var` of a line, and nothing is checked yet.

---

## Phase 2: User Story 2 — One method becomes a typed zone (Priority: P1)

**Goal**: `@emits` on all five kinds of method, with the runtime check. Issue phase 2.

**Independent Test**: For each of the five kinds, a method with `@emits(A)` emits `A`, then another event, then a line with no event.

- [ ] T016 [P] [US2] Create `TESTS/intents/emits/__init__.py` and `TESTS/intents/emits/test_emits_decorator.py`: `@emits()` with nothing, a class that is not an event, `BaseEvent` itself and a repeated event are refused; `@emits` applied twice raises `DuplicateDeclarationError`; on a method that is not one of the five kinds it raises `DecoratorTargetError` when the class is defined; written above and below each of the five decorators, it gives the same result
- [ ] T017 [P] [US2] Create `TESTS/runtime/test_emission_rules.py`, a recording logger and one action per kind of method. A case per kind: `A` is delivered; `B` and a line with no event, with `kwargs` and with none, are refused and no logger receives them; the message names the action, the method and what was refused
- [ ] T018 [US2] Add to `TESTS/runtime/test_emission_rules.py` what a refusal does in each kind (FR-015): an aspect rolls the saga back and reaches `@on_error`, and with no handler reaches the caller; `@on_error(Exception)` catches it and nothing was delivered; a compensator counts as failed and the next one still runs; a handler gives `OnErrorHandlerError`; `@access_decide` gives `Undecided` from `check_access_decide` and `AccessUndecided` from a run
- [ ] T019 [US2] Add to `TESTS/runtime/test_emission_rules.py`: `@emits(A, B)` with either or neither; another method of the action logging with `kwargs`; a plugin and the machine's own line around a typed method; a helper called with the method's `box`; a refusal with a broken template comes first; an event from `@access_decide` delivered on both paths; a result from the cache delivers nothing; `SyncActionProductMachine`. With no switch on, each of the five kinds logs with `kwargs` and with no variables and is delivered with a dictionary `var`, in both machines and under `TestBench`
- [ ] T020 [US2] Add to `TESTS/runtime/test_emission_rules.py` the direct runs of `TestBench`: `run_aspect`, `run_summary` and `run_compensator`, each raising the same error with the same message as a normal run
- [ ] T021 [P] [US2] Create `AM/model/emitting_method_markers.py` with the name `_emits_events` and the marker names of the emitting methods: `_new_aspect_meta`, `_compensate_meta`, `_on_error_meta`, `_access_decide_meta`. It imports nothing from `aoa`
- [ ] T022 [US2] Create `AM/intents/emits/emits_decorator.py` and `AM/intents/emits/__init__.py`: `emits(*events)` validates its arguments as `@context_requires` does, raises `DuplicateDeclarationError` when the function already has `_emits_events`, writes the tuple and returns the function unchanged. Add `intents.emits` to the first imports of `TESTS/model/test_import_order.py`
- [ ] T023 [US2] In `BaseAction.__init_subclass__` in `AM/model/base_action.py`, refuse a method in the class body that has `_emits_events` and none of the four markers, with `DecoratorTargetError` naming the class and the method
- [ ] T024 [US2] Create `AM/runtime/emission_rules.py`: a frozen `EmissionRules` as in `data-model.md`, its `check(event)` for the `declared` half, and `emission_rules_for(action_cls, method_name)`, which returns `None` when the method has no `@emits`
- [ ] T025 [US2] In `AM/runtime/tools_box.py`, add the keyword `emission: EmissionRules | None = None` to the constructor and a slot, with no public property; call `check` in the three tools before anything reaches the logger, for lines with and without an event
- [ ] T026 [US2] Pass `emission=emission_rules_for(type(action), method_name)` from `method_box` in `AM/runtime/method_box.py`
- [ ] T027 [US2] Pass the same from `run_aspect`, `run_summary` and `run_compensator` in `AM/testing/bench.py`
- [ ] T028 [US2] Run the new test files, then all of `packages/aoa-action-machine/tests/`. No existing test may be edited
- [ ] T029 [US2] Adversarial breaks 9, 12, 13, 16, 17, 18 and 22 of `quickstart.md`, one at a time, each restored before the next
- [ ] T030 [US2] Run `bash scripts/check_before_commit.sh` to exit code 0. **Commit point**: `feat(intents): @emits makes a method a typed zone (#333)`

**Checkpoint**: Mode 2 works on all five kinds of method.

---

## Phase 3: User Story 3 — A whole domain speaks only in declared facts (Priority: P1)

**Goal**: `events` in a domain, with the runtime checks and the build check. Issue phase 3.

**Independent Test**: A domain with `events` and one action for each rule of the table of modes.

- [ ] T031 [P] [US3] Create `TESTS/domain/test_domain_events.py`: a list, a non-event, `BaseEvent` itself and a repeated class each raise `EventContractError` when the domain is defined; a child domain inherits `events`, and declaring its own replaces them; one class in two domains is allowed; `events = ()` is accepted
- [ ] T032 [US3] Add to `TESTS/runtime/test_emission_rules.py` every mode 3 row of the table in `spec.md`, for each kind of method: a line with no event is refused with and without `@emits`; an event outside `events` is refused; a method without `@emits` is refused, compensators and handlers included; `events = ()` refuses everything; a nested action from an untyped domain logs with `kwargs`; an action with no domain answers to `@emits` only; in a domain with no `events`, each kind logs with `kwargs` and with no variables exactly as before
- [ ] T033 [P] [US3] Create `TESTS/graph/test_emits_vocabulary_validator.py`: `@emits` outside `events` fails the build, one case per kind, naming the method, the event and the domain; an event in `events` that no `@emits` names passes; a domain with no `events` is not looked at; the graph JSON is the same with and without `events` and `@emits`
- [ ] T034 [US3] In `AM/domain/base_domain.py`, add `_validate_events`, called from `__init_subclass__` for a class with `events` in its own body: a tuple of distinct classes, each a subclass of `EventMarker` and none of them a direct child of it, or `EventContractError`
- [ ] T035 [US3] Complete `AM/runtime/emission_rules.py`: `vocabulary` from `resolve_domain`, the full table of `check`, and `None` from `emission_rules_for` only when neither switch is on
- [ ] T036 [US3] Create `AM/graph/validators/emits_vocabulary_validator.py`: for each action node whose domain declares `events`, walk the regular aspects, the summary aspect, the compensators, the error handlers and the access decision, and raise `EventContractError` for an event outside `events`
- [ ] T037 [US3] Call it from `NodeGraphCoordinator.build` in `AM/graph/core/node_graph_coordinator.py` once the nodes are wired, and add it to the `Raises` section there
- [ ] T038 [US3] Run the new test files, then all of `packages/aoa-action-machine/tests/`. No existing test may be edited
- [ ] T039 [US3] Adversarial breaks 10, 11, 14, 15, 19 and 23 of `quickstart.md`, one at a time, each restored before the next
- [ ] T040 [US3] Run `bash scripts/check_before_commit.sh` to exit code 0. **Commit point**: `feat(domain): events, the vocabulary of a domain (#333)`

**Checkpoint**: Mode 3 works, and the build holds `@emits` to the vocabulary.

---

## Phase 4: User Story 4 — The cascade is proved on a running product (Priority: P2)

**Goal**: `aoa-demo` goes through the cascade up to mode 3. Issue phase 4.

**Independent Test**: The demo's tests pass, and a logger receives typed events with the same text.

- [ ] T041 [US4] Create `packages/aoa-demo/tests/fastapi_mcp_services/test_order_events.py`: `GetOrderAction` and `CreateOrderAction` deliver their events, with the text and the answers they had; a build with an event removed from `OrdersDomain.events` fails; a call with `kwargs` fails at runtime
- [ ] T042 [US4] Create `DEMO/events.py` with `OrderRequestedEvent(order_id: str)` and `OrderValidatedEvent(user_id: str, amount: float)`
- [ ] T043 [US4] Convert the calls in `DEMO/actions/get_order.py` and `DEMO/actions/create_order.py`, each with `@emits`. The templates stay as they are
- [ ] T044 [US4] Declare `events = (OrderRequestedEvent, OrderValidatedEvent)` in `DEMO/orders_domain.py`
- [ ] T045 [US4] Run `packages/aoa-demo/tests/` and `uv run --extra dev graph-builder check`: `packages/aoa-demo/graph.json` has not changed
- [ ] T046 [US4] Run `bash scripts/check_before_commit.sh` to exit code 0. **Commit point**: `feat(demo): the orders domain speaks in typed events (#333)`

**Checkpoint**: The whole cascade runs on a real product.

---

## Phase 5: Closing check run

- [ ] T047 Run `bash scripts/run_checks_with_log.sh` and take every remark to zero, the two accepted remarks of the constitution aside. **Commit point** only if the run changed something: `chore: the check run for typed events (#333)`

---

## Phase 6: User Story 5 — A reader learns the primitive and the rules (Priority: P2)

**Goal**: The constitution, chapter 11 and the reference pages. Issue phase 6. Every example is executed as it is written, and what a page shows is what it printed (Principle VI).

**Independent Test**: Run every example, script and notebook, and compare what it prints with the page.

- [ ] T048 [US5] Write the documentation, every example executed as it is written (FR-026 to FR-028, Principle VI). (1) `docs/explanation/architectural-constitution.md`: the seven places #333 lists. (2) The new section in `docs/explanation/architectural-constitution.ru_draft.md`, and "nine" becomes "ten" in `docs/explanation/verification-must-be-independent.md` and in `docs/explanation/verification-must-be-independent_draft.md`. (3) `examples/step_11_object_events/`, a script and a notebook for each: `01_event_line` (a line with an event, what a logger receives, a `kwargs` line beside it); `02_emits` (mode 2: delivered, each refusal); `03_domain_events` (mode 3: each row of the table, the build failure, `events = ()`); `04_refusal_by_kind` (what a refusal does in each kind of method); `05_rollback` (the two rollback rules, with a later step failing after the reserving step succeeded). Run each, script and notebook. (4) `docs/tutorials/step-11-object-events.md`: the one foundation of two switches; each case above with its real output; the two rollback rules; the warning on mode 3; the note that compensators and error handlers need tests of their own; that a result from the cache delivers no events. Its navigation leads back to chapter 10 and on to `step-11-machine.md`. (5) `docs/tutorials/step-11-object-events.ru_draft.md`, the Russian version of the chapter. (6) `docs/tutorials/step-10-logs.md`, in three small ways only: its navigation points to chapter 11, the end of its summary leads into chapter 11, one line links to it. (7) `docs/reference/intents-and-invariants.md`, `docs/reference/glossary.md` and their Russian drafts state the new rules. (8) `docs/how-to/authoring-logger.md` says what `var` is in each of the two forms. (9) `docs/index.md` and `README.md` list the new chapter. Then run `uv run --extra dev pytest tests/examples -q` and `bash scripts/check_before_commit.sh` to exit code 0. **Commit point**: `docs: BaseEvent, the tenth primitive, and object events (#333)`

---

## Phase 7: Changelog

- [ ] T049 Write one article in `docs/CHANGELOG.md`: what this work created, in plain words, with the nuances a user needs, and no technical detail or account of files (Principle VI). **Commit point**: `docs: changelog for typed events (#333)`

The plan stops here: no release, version bump or publishing.

---

## Dependencies

```text
Phase 1 (US1) → Phase 2 (US2) → Phase 3 (US3) → Phase 4 (US4) → Phase 5 → Phase 6 (US5) → Phase 7
```

Each phase needs the one before it: `@emits` checks what `box` accepts, `events` completes the same rules, the demo uses all three, and the documentation shows them settled.

## Parallel opportunities

Tasks marked `[P]` touch different files and depend on no unfinished task:

- Phase 1: T001 with T002; T006 with T007.
- Phase 2: T016 with T017, and T021 alongside them.
- Phase 3: T031 with T033.

The rest run in order. One writer works on the repository at a time.

## Implementation strategy

The first deliverable is Phase 1: a fact gets a type and a schema with nothing else switched on. Phases 2 and 3 add the two switches, and Phase 4 proves them. Each commit leaves the check run green.
