# Contract: the two new events

Both events are additions to the plugin contract. A plugin that does not care about access decisions needs no change, and every existing event keeps its name and what it carries (FR-015).

## The decision event

Published exactly once for every decision, on the execution path and on the question path (FR-013, SC-001).

| Field | Meaning |
| --- | --- |
| the answer | The whole verdict: `kind`, and `gate` + `reason` when refused |
| path | Whether the call asked in advance or executed |
| request identity | `context.request.trace_id`, published as `aoa.trace_id`; carried only when the context has one, never invented locally (SC-008) |

## The failed-gate event

Published when a gate cannot tell, in addition to the decision event for the resulting `undecided` answer (FR-014).

| Field | Meaning |
| --- | --- |
| the failure kind | The type of the failure, never its text (FR-016) |
| request identity | Same field and the same rule as above |

## Rules that hold for both

- No event carries the text of a failure raised inside a gate (FR-016, SC-007).
- The question path publishes no run-lifecycle event, because nothing was run (FR-017).
- A failed gate is never remembered or reused as a refusal (FR-006, SC-004).

## What a plugin sees

- With a logger provider configured, the OpenTelemetry plugin turns the decision event into a log record; with none configured it writes nothing, and the core stores nothing either.
- The record's body follows the naming the plugin already uses for its other records, so an operator reads decisions in the same place as everything else.
- The engine's obligation ends at publishing the event: an event is a fact about the system, and whether anyone listens is the application's decision.
