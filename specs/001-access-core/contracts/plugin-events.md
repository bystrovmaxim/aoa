# Contract: what a decision publishes

One event is added to the plugin contract. A plugin that does not care about access needs no change, and every existing event keeps its name and what it carries (FR-014).

## What is published, and what is not

A decision is **not** published. It reaches one caller at a time: as an exception carrying the answer when the call executes, and as the answer itself when someone asks in advance (FR-020). A refusal is therefore published nowhere — it is visible in what the caller receives, and, while executing, in a run that shows its `GlobalStart` without a `GlobalFinish`.

Two things are published:

| What | When | Why |
| --- | --- | --- |
| the object check's own before and after events | whenever the check runs — executing **and** asking in advance | it is a declared behaviour of the operation, and asking genuinely runs it, so both paths are observably the same |
| the failed-gate event | a gate cannot tell **while a call executes** | the engine could not decide, which is a fact about the system rather than about the caller |

Asking in advance publishes nothing else at all: no run lifecycle, no failed-gate event, and no event about the answer (FR-016).

## The failed-gate event

Published when a gate cannot tell while a call executes, and only then (FR-013).

| Field | Meaning |
| --- | --- |
| the gate | Which step could not tell, one of the five published words — the decision itself is not published, so this is what names it |
| the failure kind | The type of the failure, never its text (FR-015) |
| request identity | `context.request.trace_id`, published as `aoa.trace_id`; carried only when the context has one, never invented locally (SC-008) |

The failure itself — the exception, its message and its traceback — is never published. It stays in memory and goes to the log (FR-005, FR-015).

## The object check's own events

The declared object check is observable like every other declared behaviour (FR-019):

- a **before** event whenever it runs, on either path;
- an **after** event whenever it finishes, whatever it answered — allowed, a refusal, or an undecided it decided itself. A `before` without an `after` is a check that failed, which is also what the failed-gate event says while a call executes.

While executing, they land after `GlobalStart` and before the aspect pipeline. An operation that declares no object check publishes none, and a decision that stops before reaching that step publishes none either.

## Rules

- No event carries the text of a failure raised inside a gate (FR-015, SC-007).
- The question path publishes no run-lifecycle event, because nothing was run (FR-016).
- A failed gate is never remembered or reused as a refusal (FR-006, SC-004).
- A gate that passes publishes nothing at all: silence is not a decision, it is the absence of one.
- No access decision reaches the operation's own failure handling: a handler the operation declares for its failures is not reached by a refusal or by an inability to decide (scope, not a requirement).

## What a plugin sees

- With a logger provider configured, the OpenTelemetry plugin turns the failed-gate event into a log record; with none configured it writes nothing, and the core stores nothing either.
- The record's body follows the naming the plugin already uses for its other records, so an operator reads access failures in the same place as everything else.
- The engine's obligation ends at publishing the event: an event is a fact about the system, and whether anyone listens is the application's decision.

## The whole matrix

Four points, three situations, two modes (FR-013, FR-019). Read a cell as the events published, in that order. The identity point is the transport's: the core never decides it, so its rows describe a refusal that happens before the engine is reached and nothing about it is published here.

### Executing

| Point | Situation | Events |
| --- | --- | --- |
| identity | passed | none |
| | refused | none — the refusal leaves as an exception |
| | could not tell | `AccessGateFailed` |
| roles | passed | none |
| | refused: no listed role held | none — the refusal leaves as an exception |
| | refused: a matching grant's condition | none — the refusal leaves as an exception |
| | could not tell | `AccessGateFailed` |
| condition | passed | none |
| | refused | none — the refusal leaves as an exception |
| | could not tell | `AccessGateFailed` |
| object | passed | `GlobalStart` → `BeforeAccessDecide` → `AfterAccessDecide` → the aspect pipeline → `GlobalFinish` |
| | refused | `GlobalStart` → `BeforeAccessDecide` → `AfterAccessDecide` → the exception leaves |
| | could not tell | `GlobalStart` → `BeforeAccessDecide` → `AccessGateFailed` → the exception leaves |

### Asking in advance

| Point | Situation | Events |
| --- | --- | --- |
| identity, roles, condition | passed, refused, or could not tell | none |
| object | passed | `BeforeAccessDecide` → `AfterAccessDecide` |
| object | refused | `BeforeAccessDecide` → `AfterAccessDecide` |
| object | could not tell | `BeforeAccessDecide` |

What the matrix says in one line: asking in advance publishes the object check's own events and nothing else, ever; a call that executes adds the run's lifecycle and, when a gate cannot tell, the failed-gate event.

Three consequences worth keeping in mind: a run that ends in a refusal leaves its `GlobalStart` without a `GlobalFinish`, which is how telemetry shows a call that was stopped; the object check's `After` event appears whenever the check finished, so its absence means the check failed; and nothing about a decision reaches the operation's failure handling, so a handler can never serve a call the decision refused.
