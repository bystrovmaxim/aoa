# Feature Specification: Every method of an action gets its own box

**Feature Branch**: `feature/issue-331-every-method-of-an-action-gets-its-own-box`

**Created**: 2026-11-02

**Status**: Draft

**Input**: GitHub issue #331, "Every method of an action gets its own box: @on_error and @access_decide do not". Rule: every method that receives `box` gets its own `box` with its own name, no exceptions; `@on_error` also gets its own `state`. Only how the machine prepares `box` changes; no action's code changes. Phases: `@on_error` gets its own `box`; `@access_decide` gets its own `box` on a normal run and in `check_access_decide`; a test covers all five kinds of method; closing check run, documentation, changelog.

## What changed since the issue was written

The issue was checked against `main` at 60ff7a43 with one action that logs from all five kinds of method. Its claims hold:

```text
log action='ProbeAction' aspect=''                state={}  msg='access'
log action='ProbeAction' aspect='reserve_aspect'  state={}  msg='regular'
log action='ProbeAction' aspect='undo_compensate' state={}  msg='compensate'
handler state arg: {'reserved': 'yes'}
log action='ProbeAction' aspect=''                state={}  msg='handler plain'
OnErrorHandlerError: Error handler 'handle_on_error' in ProbeAction raised while handling
ValueError: Variable '{%state.reserved}' not found.
```

Three things the issue does not say:

- **Both paths of `@access_decide` meet in one place.** A normal run and `check_access_decide` prepare separate shared boxes, but the method is called from the same step of the access decision. The rule therefore holds for both paths by being applied once.
- **`TestBench` has no entry for `@on_error` or `@access_decide`.** It runs a regular aspect, a summary aspect and a compensator directly, each already named. It needs no change.
- **One log line stays without a method name, correctly.** The machine's own critical line about a failed saga rollback is not written by a method of an action and receives no `box`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A log line in an error handler sees the handler's state (Priority: P1)

An action's author writes an `@on_error` handler that logs a value from `state`. Today the handler's `state` argument has the value, its log does not, and the original error turns into `OnErrorHandlerError` because of one ordinary log line. After this change the line is written and the handler returns its result.

**Why this priority**: It is the only fault here that breaks a running action: a log line destroys the handling of the very error it reports.

**Independent Test**: Run an action whose second aspect fails, with a handler that logs `{%state.x}` for a field the first aspect wrote. The run returns the handler's result and the log line carries the value.

**Acceptance Scenarios**:

1. **Given** an aspect that wrote `reserved` and a later aspect that raises, **When** the handler logs `{%state.reserved}`, **Then** the line is written with that value and the handler's result is returned.
2. **Given** a failure in the summary aspect, **When** the handler logs a field written earlier, **Then** the line is written with that value.
3. **Given** a failure in the first aspect, so that nothing was written, **When** the handler logs `{%state.reserved}`, **Then** the behaviour is the same as for any method naming a field that is absent: the template fails, and the failure is reported as `OnErrorHandlerError`.
4. **Given** a handler that calls a nested action or resolves a dependency through `box`, **When** it runs, **Then** both work exactly as before.

---

### User Story 2 - The log says which method wrote a line (Priority: P1)

Someone reading a log, or a logger routing it, needs to know which method wrote a line. Three kinds of method tell them; `@on_error` and `@access_decide` write an empty name. After this change all five name themselves, and the name is the same whether the access check runs in a real call or in `check_access_decide`.

**Why this priority**: The method name is what ties a log line to a node of the graph, and #95 relies on it to check at runtime which method emits an event.

**Independent Test**: Run an action that logs from `@on_error` and from `@access_decide`, then ask `check_access_decide` about it. Every line carries the writing method's name.

**Acceptance Scenarios**:

1. **Given** a handler that logs, **When** it runs, **Then** the line carries the handler's method name, not the name of the aspect that failed.
2. **Given** an `@access_decide` method that logs, **When** the action runs normally, **Then** the line carries that method's name and its `state` is empty.
3. **Given** the same action, **When** `check_access_decide` is asked about it, **Then** the line carries the same name and the same empty `state`.
4. **Given** several `@on_error` handlers on one action, **When** one is chosen, **Then** the line carries the name of the chosen one.
5. **Given** an `@access_decide` method that logs `{%state.x}`, **When** it runs, **Then** the answer is `Undecided` naming the object step, as for any failing check: this kind of method has no `state`.

---

### User Story 3 - The rule cannot quietly come apart again (Priority: P2)

A maintainer adds or changes a way the machine calls a method. One test states the rule for all five kinds of method, so a kind that loses its name fails the test at once and is named by it.

**Why this priority**: Without it the two fixes above are two facts, not a rule. The gap in the issue survived because nothing stated it.

**Independent Test**: Run one action with all five kinds of method; from each log line build `<action>:<method>` and find that node in the graph. Then take the name away from each kind in turn.

**Acceptance Scenarios**:

1. **Given** one action with all five kinds of method, **When** it runs, **Then** each log line's action and method names give the id of the node of the method that wrote it.
2. **Given** that action, **When** the name is taken away from any one kind, **Then** the test fails and names that kind.
3. **Given** a compensator, **When** it logs, **Then** its `state` is still the snapshot before its step.

---

### Edge Cases

- A nested action fails and its own handler logs: the line carries the nested action's handler and the nested nesting level.
- A handler declared with `@context_requires` receives its context view and its own `box` together.
- An `@access_decide` method declared with `@context_requires` likewise.
- An action with no `@access_decide` and no `@on_error`: nothing changes and nothing extra is prepared for it.
- An error with no matching handler: no handler runs, and the error goes up as it does today.
- `{%scope.aspect}` in a handler's log: the handler's name, never the name of the aspect that failed.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every method of an action that receives `box` MUST receive a `box` of its own, carrying that method's name. There are no exceptions among the five kinds: `@regular_aspect`, `@summary_aspect`, `@compensate`, `@on_error`, `@access_decide`.
- **FR-002**: An `@on_error` handler's `box` MUST carry the same `state` the handler receives as its argument.
- **FR-003**: An `@access_decide` method's `box` MUST carry an empty `state`: the method has none.
- **FR-004**: `@access_decide` MUST be named the same way on a normal run and in `check_access_decide`.
- **FR-005**: For every kind of method, the action and method names in a log line MUST give exactly the id of that method's node in the graph (`<action>:<method>`).
- **FR-006**: A method's own `box` MUST behave as the shared one does in everything but its name and `state`: nested actions, dependencies, resources, nesting level and rollup stay as they are.
- **FR-007**: No action's code, no method signature and no public interface MAY change. What the access decision answers MUST NOT change.
- **FR-008**: A single test MUST cover all five kinds of method (User Story 3), verified adversarially: taking the name away from each kind in turn fails this test.
- **FR-009**: The documentation MUST state the rule and show what each of the five kinds receives, including the cases named in the edge cases.
- **FR-010**: The changelog MUST carry one article about this work, in plain words.

### Key Entities

| Kind of method | Own `box` | Method name in the log | `state` in the log |
|---|---|---|---|
| `@regular_aspect` | yes | its own | current |
| `@summary_aspect` | yes | its own | current |
| `@compensate` | yes | its own | snapshot before the step |
| `@on_error` | yes (new) | its own (new) | the handler's `state` (new) |
| `@access_decide` | yes (new) | its own (new) | empty; it has no `state` |

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The handler from the issue, unchanged, finishes without `OnErrorHandlerError` and writes `reserved=yes`.
- **SC-002**: 5 of 5 kinds of method write log lines whose names give an existing node of the graph; today it is 3 of 5.
- **SC-003**: `@access_decide` writes the same name on both paths.
- **SC-004**: The code of no existing action or example changes for this work. The documentation gains a new example and a passage in the tutorial.
- **SC-005**: Each of the five adversarial breaks fails the rule's test.
- **SC-006**: The closing check run ends at zero.

## Assumptions

- The method name in a log line is the only thing a logger sees differently: lines from these two kinds carry a name where they carried an empty string. No reader is known to rely on the empty string; planning confirms this across the packages.
- Naming a field absent from `state` in a log template stays an error for every kind of method. This work gives a handler its `state`; it does not soften templates.
- Plugin events are not touched: the handler's events already name the handler.
- The event's runtime check in #95 is out of scope; this work only makes it possible.
