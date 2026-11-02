# Feature Specification: Typed events, `@emits` and the domain vocabulary

**Feature Branch**: `feature/issue-333-baseevent-core-typed-events-emits-and-the-domain-vocabulary`

**Created**: 2026-11-02

**Status**: Draft

**Input**: GitHub issue #333, "BaseEvent core: typed events, @emits and the domain vocabulary", a child of root issue #95, which holds the design and the rules. Depends on #331.

## Clarifications

### Session 2026-11-02

- Q: Is an event from `@access_decide` delivered when the method runs through `check_access_decide`? → A: Yes. `@access_decide` is no different from the other kinds of method: what it emits is delivered on both paths.
- Q: Are events repeated when an action's result comes from the cache? → A: No. The methods did not run, so no fact happened again and nothing is delivered.
- Q: May one event class be in the `events` of several domains? → A: Yes. A vocabulary says what a domain allows, not who owns the class.
- Q: What does the build do with an event in `events` that no `@emits` of the domain names? → A: It passes. A domain may list an event nobody uses; Maxitor may report that later as a heuristic.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The variables of a log line are a typed fact (Priority: P1)

An action's author declares a business fact as a class with typed fields and passes an instance to `box` in place of `kwargs`, after the text of the line. The text stays the author's template, with its variables and colours. A logger receives the rendered line as always, and its `var` is the fact itself.

```python
await box.info(
    Channel.business,
    "Order {%var.order_id} total {%var.total}",
    OrderCompletedEvent(order_id=state["order_id"], total=state["total"]),
)
```

**Why this priority**: Every other story checks events, so nothing works without this one. It is also useful alone: a fact gets a type and a schema with no switch turned on.

**Independent Test**: Declare an event, emit it through each of the three tools from an action with no switch on, and read what a recording logger received.

**Acceptance Scenarios**:

1. **Given** an event class, **When** an instance is built with a wrong type or an extra field, **Then** building it fails.
2. **Given** a built event, **When** code tries to change a field, **Then** the change fails.
3. **Given** an event class, **When** its author sets `level`, `channels`, `domain` or `domain_name`, **Then** building it fails.
4. **Given** a call with an event, **When** it goes through `info`, `warning` or `critical`, **Then** the logger receives the rendered line and a `var` that is that event, of its own type, with the level, channels and domain of the call filled in.
5. **Given** a call with an event, **When** it has been made, **Then** the author's instance is unchanged, and its dump holds the fact's own fields only.
6. **Given** a template with colours, `|debug`, `{iif(...)}`, a nested path, `{%state.*}`, `{%params.*}` or `{%context.*}`, **When** it is used with an event, **Then** it renders as it does with `kwargs` holding the same values.
7. **Given** a logger subscribed by channel, level or domain, **When** an event is emitted, **Then** the subscription filters the line as it filters any other.
8. **Given** a logger written for lines with `kwargs` that reads `var` by key, **When** it receives a line with an event, **Then** it works with no change to its code.
9. **Given** a subclass of `BaseEvent` whose name does not end with `Event`, **When** it is defined, **Then** the class is refused.

---

### User Story 2 - One method becomes a typed zone (Priority: P1)

An author adds `@emits` to one method of one action. That method may now emit only the listed events. Nothing else in the action or the domain changes. This is mode 2 of the cascade.

**Why this priority**: It makes the declaration true rather than decorative, and it is the safe, method-by-method path to a typed domain.

**Independent Test**: For each of the five kinds of method, take a method with `@emits(A)` and have it emit `A`, then another event, then a line with no event.

**Acceptance Scenarios**:

1. **Given** a method with `@emits(A)`, **When** it emits `A`, **Then** the line is delivered.
2. **Given** that method, **When** it emits `B`, which is not listed, **Then** an exception is raised and no consumer receives the line.
3. **Given** that method, **When** it logs a line with no event, with `kwargs` or with none, **Then** an exception is raised and no consumer receives the line.
4. **Given** a method with `@emits(A, B)`, **When** a branch emits either one or neither, **Then** the call succeeds.
5. **Given** an action where one method has `@emits`, **When** another of its methods logs a line with `kwargs`, **Then** the line is delivered as before.
6. **Given** a method with `@emits`, **When** a plugin writes a line about it or the machine writes its own line, **Then** both are delivered.
7. **Given** each of the five kinds of method, **When** it breaks its `@emits`, **Then** the failure takes that kind's ordinary path (FR-015).
8. **Given** a regular aspect, a summary aspect or a compensator run directly under `TestBench`, **When** it breaks its `@emits`, **Then** the same refusal reaches the test as it is.
9. **Given** `@emits` written above or below the method's own decorator, **When** the class is defined, **Then** the result is the same.
10. **Given** an `@access_decide` method with `@emits`, **When** it runs on a normal run and in `check_access_decide`, **Then** what it emits is delivered both times, and a broken rule is refused both times.

---

### User Story 3 - A whole domain speaks only in declared facts (Priority: P1)

A domain's owner declares `events`, the vocabulary of the domain. This is mode 3. Every method of every action in that domain may now emit only what its own `@emits` lists, and only from the vocabulary. A declaration outside the vocabulary fails the build.

**Why this priority**: It makes a domain's facts a closed list a reader can trust, and #334 and #335 build on that list.

**Independent Test**: Build a domain with `events` and one action for each rule below, and run each.

**Acceptance Scenarios**:

1. **Given** a domain with `events = (A,)` and a method with `@emits(B)`, **When** the application is built, **Then** the build fails and names the method, the event and the domain.
2. **Given** a domain with `events`, **When** any of its methods logs a line with no event, **Then** an exception is raised, whether or not the method has `@emits`.
3. **Given** that domain, **When** a method without `@emits` emits an event from the vocabulary, **Then** an exception is raised, and this includes compensators and error handlers.
4. **Given** that domain, **When** a method emits an event it declared and the vocabulary holds, **Then** the line is delivered.
5. **Given** a domain with `events = ()`, **When** any of its methods logs anything, **Then** an exception is raised.
6. **Given** a domain with no `events`, **When** its methods log lines with `kwargs`, **Then** nothing changes.
7. **Given** an action in a typed domain that runs a nested action from an untyped domain, **When** the nested action logs a line with `kwargs`, **Then** the line is delivered.
8. **Given** an action with no domain, **When** it runs, **Then** only `@emits` can make a zone typed.

---

### User Story 4 - The cascade is proved on a running product (Priority: P2)

`aoa-demo` goes through the cascade: its two logging calls become typed events with `@emits`, then `OrdersDomain` declares `events`. The product behaves as it did.

**Why this priority**: The mechanism is proved only by something real that uses it. It depends on the three stories above.

**Independent Test**: Run the demo's existing tests after the conversion, then call the two actions and read what a logger received.

**Acceptance Scenarios**:

1. **Given** the converted demo, **When** `GetOrderAction` and `CreateOrderAction` run, **Then** each delivers its typed event, and the answers and the text of the log lines are what they were.
2. **Given** the converted demo, **When** one of the two events is removed from `OrdersDomain.events`, **Then** the build fails.
3. **Given** the converted demo, **When** a call with `kwargs` is put back, **Then** that call fails at runtime.

---

### User Story 5 - A reader learns the primitive and the rules (Priority: P2)

A reader of the architectural constitution finds `BaseEvent` wherever the primitives are listed. A reader of the tutorial finds chapter 11, built on one foundation: lines with `kwargs` stop working only when a switch is on, and there are two switches.

**Why this priority**: The project's constitution requires it, and it describes what the stories above build.

**Independent Test**: Run every example of the chapter, script and notebook, and compare what it prints with the page.

**Acceptance Scenarios**:

1. **Given** the architectural constitution, **When** a reader looks at each of the seven places #333 names, **Then** `BaseEvent` is there.
2. **Given** chapter 11, **When** it is read, **Then** it carries the two rollback rules, the warning on mode 3, the note that compensators and error handlers need tests of their own, and the fact that a result from the cache delivers no events.
3. **Given** every case this work introduces, **When** the chapter is read, **Then** each appears as a script and as a notebook, and what is shown is what it printed.
4. **Given** chapter 10, **When** it is compared with `main`, **Then** only its navigation, the end of its summary and one line with a link have changed.
5. **Given** the reference pages named in FR-028, **When** a reader opens each, **Then** it states the rules it covers, and the new chapter is listed.

---

### Edge Cases

**The event**

- A subclass with a field named `level`, `channels`, `domain` or `domain_name`: refused when the class is defined.
- A subclass with a field named `get`, `keys`, `values`, `items` or `resolve`: refused when the class is defined, because a logger reads the event through these methods. Such a field takes another name, for example `line_items`.
- A property marked `@sensitive` on an event: masked in the rendered line, as on `params`. A plain field is printed as it is, and a logger reads it as it is, like a value in `kwargs`.
- A test comparing what a logger received with the author's event: the logger holds a filled copy, so the comparison is by fields.

**The call**

- An event together with `kwargs`: refused in every mode, since the event already holds its data.
- An event class passed instead of an instance, an instance of `BaseEvent` itself, or any other object in the event's place: refused in every mode, naming what was passed.
- A template naming a field the event does not have: fails as a template naming an absent variable fails.
- A refused emission with a broken template: the refusal comes first, since the text is rendered only for a line that may go out.
- A template with no variables and an event: allowed; `var` is still the event.
- A call passing a keyword named `event=`: an ordinary `kwargs` variable, as for any other name.
- A logger that writes into `var` or merges it as a dictionary: works only on a line with `kwargs`, whose `var` is a dictionary.

**`@emits`**

- `@emits` on a method that is not one of the five kinds: no effect, as with `@context_requires`. Nothing calls such a method through a `box` of its own.
- `@emits()` with nothing listed, a class that is not an event, `BaseEvent` itself, the same event listed twice, or `@emits` applied twice to one method: refused when applied.
- A subclass of an action: an action's emitting methods are those declared in its own class, so none of them, and no `@emits`, comes from a parent action.
- A helper that a method calls with its `box`: part of that method, so the method's rules apply.
- A mocked nested action under `TestBench`: it writes no lines, so no rule applies.
- A handler on `@on_error(Exception)` catches a refusal from an aspect, like any exception. Nothing was delivered.
- A refusal inside a compensator: the rollback continues with the next compensator.
- A result served from the cache: the methods do not run, so no event is delivered.

**`events`**

- `events` that is not a tuple, holds something that is not an event class, holds `BaseEvent` itself or repeats a class: refused when the domain class is defined.
- A subclass of a declared event: not the declared event. Both lists name exact classes.
- A domain inheriting from a domain with `events`: it inherits them, and declaring its own replaces them.
- One event class in the `events` of several domains: allowed. When it is emitted, the method's own domain decides.
- An event in `events` that no `@emits` of the domain names: allowed, and the build passes.
- A switch to mode 3 with a `kwargs` line left in a compensator: the build passes and the line fails on its first call.

## Requirements *(mandatory)*

### Functional Requirements

**The event**

- **FR-001**: The system MUST offer `BaseEvent`, the tenth primitive, a descendant of `BaseSchema`, immutable, with extra fields forbidden.
- **FR-002**: The name of every subclass of `BaseEvent` MUST end with `Event`, or the class MUST be refused when it is defined.
- **FR-003**: `BaseEvent` MUST declare the system fields of a log line: `level`, `channels`, `domain` and `domain_name`. They MUST be empty on an instance the author builds, and an author who sets one MUST be refused.
- **FR-004**: A subclass that declares a field named after a system field, or `get`, `keys`, `values`, `items` or `resolve`, MUST be refused when it is defined.
- **FR-005**: A dump of an event MUST hold every field except the system fields.

**The logging call**

- **FR-006**: `info`, `warning` and `critical` of `box` MUST accept a `BaseEvent` instance in place of `kwargs`, after the text of the line.
- **FR-007**: The text MUST stay a required string that the author controls. Variables, colours, `{iif(...)}` and every namespace MUST render as they do with `kwargs`, with `{%var.*}` reading the event's fields.
- **FR-008**: In a call with an event, `box` MUST fill the system fields in a copy, and that copy MUST be the `var` a logger receives. The author's instance MUST stay as it was built. In a call with `kwargs`, `var` MUST be a dictionary, with no change in behaviour.
- **FR-009**: `BaseLogger` MUST keep its methods and parameters, and the coordinator, the templates and the subscriptions MUST keep their logic. Only the declared type of `var` changes. A logger MUST read `var` by key in both forms, and every existing logger subclass MUST pass the type check with no change to its code.
- **FR-010**: A call with an event and `kwargs`, or with anything in the event's place other than an instance of a subclass of `BaseEvent`, MUST be refused in every mode.
- **FR-011**: Events MUST reach consumers only through this path. They MUST NOT touch plugin events, and no new consumer mechanism MAY be added.

**`@emits`, mode 2**

- **FR-012**: `@emits` MUST work on all five kinds of method: `@regular_aspect`, `@summary_aspect`, `@compensate`, `@on_error`, `@access_decide`. Its position among the method's decorators MUST NOT matter. With invalid arguments, or applied twice to one method, it MUST be refused when applied.
- **FR-013**: A method with `@emits` MUST be able to emit only the listed events. Emitting another event, or logging a line with no event, MUST raise an exception at runtime, before the text is rendered and before any consumer receives anything. The exception MUST name the action, the method and what was refused.
- **FR-014**: `@emits` MUST NOT require an emission. A method may emit any of the listed events, or none.
- **FR-015**: A refused emission MUST take the ordinary path of the method that made it, and no new path MAY be added: an aspect fails as for any error; a compensator counts as a failed compensation and the rollback goes on; a handler gives `OnErrorHandlerError`; `@access_decide` gives `Undecided` naming the step, which a run raises as `AccessUndecided`.
- **FR-016**: The rules MUST cover operation code only. What plugins and the machine write MUST stay as it is, in every mode.

**`events`, mode 3**

- **FR-017**: A domain MUST be able to declare `events`, a tuple of event classes. A domain that does not declare it MUST behave as it does with no switch. An empty tuple MUST be a declaration: the domain is in mode 3 and emits nothing.
- **FR-018**: `events` MUST be a tuple of distinct subclasses of `BaseEvent`, and anything else MUST be refused when the domain class is defined. A domain inheriting from a domain with `events` MUST inherit them, and declaring its own MUST replace them.
- **FR-019**: The application build MUST fail when an event in the `@emits` of any method of a domain is not in that domain's `events`, naming the method, the event and the domain.
- **FR-020**: At runtime, in a domain with `events`, a line with no event, an event outside `events` and an event outside the method's own `@emits` MUST each raise an exception. A method without `@emits` therefore logs nothing.
- **FR-021**: Each method MUST answer to the rules of its own action and that action's domain, including inside nested actions. `@emits` and `events` MUST name exact classes.

**Parity and boundaries**

- **FR-022**: The rules MUST hold on a normal run of `ActionProductMachine` and of `SyncActionProductMachine`, in `check_access_decide`, and under `TestBench`, including its direct runs of a regular aspect, a summary aspect and a compensator. An event from `@access_decide` MUST be delivered on a normal run and in `check_access_decide` alike.
- **FR-023**: Each step of the cascade MUST only add checks. With neither switch on, every existing action, example and test MUST behave as it does now.
- **FR-024**: `@emits`, `events` and event classes MUST NOT change the graph or its JSON; that belongs to #334.

**`aoa-demo`**

- **FR-025**: The two logging calls in `actions/get_order.py` and `actions/create_order.py` MUST become typed events declared by `@emits`, and `OrdersDomain` MUST declare `events`. The text of both lines and what the actions answer MUST NOT change.

**Documentation and the tail**

- **FR-026**: `docs/explanation/architectural-constitution.md` MUST gain `BaseEvent` in all seven places #333 lists, and its Russian draft MUST gain the new section. `docs/explanation/verification-must-be-independent.md` and its Russian draft MUST say ten primitives.
- **FR-027**: A new chapter, `docs/tutorials/step-11-object-events.md`, MUST carry what User Story 5 lists, with its examples in `examples/step_11_object_events/`. Every case MUST appear as a script and a notebook, run while written: each row of the table of modes, each refusal, and what a refusal does in each kind of method. Chapter 10 MUST change only as User Story 5 says.
- **FR-028**: `docs/reference/intents-and-invariants.md` and `docs/reference/glossary.md` MUST state the new rules, `docs/how-to/authoring-logger.md` MUST say what `var` is in each of the two forms, and `docs/index.md` and `README.md` MUST list the new chapter.
- **FR-029**: The closing check run MUST end at zero, then the documentation, then one changelog article, in that order. Each of the three MUST be its own task.
- **FR-030**: Each phase of #333 MUST be one commit, made only on the maintainer's instruction.
- **FR-031**: Each rule MUST be verified adversarially: break the code the way its test must catch, confirm that test fails and no other does, restore.

### Key Entities

- **Event**: a recorded business fact, and the `var` of the line that carries it. Immutable, typed, with no lifecycle. Distinct from a `Result`, the one answer to the caller; from the text of a line, written for a person; from a `BaseEntity`, which models something that changes state; and from a plugin event, which reports what the machine is doing.
- **System fields**: `level`, `channels`, `domain` and `domain_name`. They say how a line was delivered, not what happened, so `box` owns them and a dump of the fact leaves them out.
- **A line with no event**: a logging call with `kwargs` or with no variables at all.
- **Emitting method**: any of the five kinds of method of an action that receive `box`.
- **Declaration (`@emits`)**: the exact event classes one emitting method may emit.
- **Vocabulary (`events`)**: the exact event classes a domain allows.

The three modes of the cascade:

| Mode | Switch | A line with no event | An event in `@emits` | An event not in `@emits` |
|---|---|---|---|---|
| 1 | none | delivered | not applicable | delivered |
| 2, method with `@emits` | `@emits` | refused | delivered | refused |
| 2, other methods | none | delivered | not applicable | delivered |
| 3, method with `@emits` | `events` | refused | delivered; the build guarantees it is in `events` | refused |
| 3, method without `@emits` | `events` | refused | not applicable | refused |

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Reading only a method's header, a reader can name every fact it may emit: true for 100% of methods with `@emits`.
- **SC-002**: 5 of 5 kinds of method enforce `@emits`, each failing by its own ordinary path.
- **SC-003**: In every refusal, zero consumers receive the refused line.
- **SC-004**: Apart from the two demo calls and `OrdersDomain`, no line of an existing action, example or test has to change.
- **SC-005**: `aoa-demo` runs in mode 3 with zero lines without an event in `OrdersDomain`, with identical answers and identical log text.
- **SC-006**: Under `TestBench` and in production, the same violation raises the same error with the same message in 100% of the cases tested.
- **SC-007**: The saved graph of `aoa-demo` is byte-identical before and after.
- **SC-008**: Every case the chapter shows runs, as a script and as a notebook, and prints what the page says.
- **SC-009**: The closing check run ends at zero, and each adversarial break fails its own test.

## Assumptions

- #331 is merged, so every emitting method has a `box` of its own on a normal run.
- An event goes out at the moment of the call, with no buffering and no delivery guarantee. The two rollback rules are guidance in the chapter, not something the machine enforces.
- A consumer that is not configured receives nothing.
- A required event as a postcondition, a typed reference from an event field to an entity, and a fact's time and correlation are open questions of #95 and are not part of this work.
- A compensator also runs for the aspect that failed; that is existing behaviour and is not changed here. So the chapter's rollback example lets a later step fail, after the reserving step has succeeded.
- The chapter number 11 is shared with `step-11-machine` until #336 renumbers the tutorial.
- Out of scope: the graph and its JSON (#334), the Maxitor view (#335), renumbering (#336), Maxitor's own 46 calls with `kwargs`, and a Maxitor heuristic that reports unused vocabulary entries.
