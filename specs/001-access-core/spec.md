# Feature Specification: Access decisions — three answers, one cascade, two events

**Feature Branch**: `feature/issue-189-access-core`

**Created**: 2026-10-07

**Status**: Draft

**Input**: User description: "one mechanism decides access for both the execution path and the question path; every decision is exactly one of three answers; a refusal names the gate that refused and why; a gate that cannot complete is not a refusal; every decision publishes an event"

## Clarifications

### Session 2026-10-07

- Q: Must a decision event carry the request's identity so that a decision can be tied to the call that produced it? → A: Yes, taken from the context when the context carries it, and never invented locally.
- Q: Can a gate answer "undecided" itself, or does that answer arise only when a gate fails? → A: Both are allowed and they mean the same thing — a gate that catches a failure inside its own logic returns undecided, and a gate that fails outright produces the same answer.
- Q: Is a question about an operation that does not exist a refusal, a caller error, or a separate "not found" answer? → A: A caller error, distinct from a refusal. Resolving operation names is the wire layer's job; the core is handed the operation, and a nonexistent object stays indistinguishable from another caller's object (FR-011).
- Q: May the gates change data while a question is being asked, or must they only read? → A: Neither — the engine adds no control over what a gate does. Whether a gate only reads or also writes is the developer's decision, and the engine's own guarantee stays narrower: asking in advance runs no step of the operation.
- Scope: the core has no way to ask about several calls at once. Asking in advance is one call about one operation; batching, endpoints, request limits and rate limiting belong to the wire layer and are not specified here.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Access is declared once and enforced wherever it is asked about (Priority: P1)

A developer writing an operation declares who may run it, and — where a condition is involved — why that condition refuses. The same decision is then produced in two situations: when the operation is actually executed, and when something asks in advance whether the operation would be allowed. Nothing is declared twice, and an answer given in advance can never promise something the execution would refuse.

**Why this priority**: this is the whole value of the feature. Without it, the access rule is either duplicated in the application — and drifts from the server — or the application cannot know anything until it tries and fails.

**Independent Test**: declare one operation with a role requirement and one declared condition; then ask in advance and execute, as a caller who satisfies the declaration and as one who does not. All answers must follow from the declaration alone, with no application-side rule.

**Acceptance Scenarios**:

1. **Given** an operation whose access is declared, **When** a caller who does not satisfy the declaration executes it, **Then** the call is refused and no step of the operation runs.
2. **Given** the same operation and the same caller, **When** the application asks in advance, **Then** the answer is the same kind of refusal, naming the same gate and the same reason, as execution produces.
3. **Given** a caller who satisfies the declaration, **When** the application asks in advance and then executes, **Then** the advance answer is "allowed" and the execution proceeds.

---

### User Story 2 - A refusal says what refused and why, and reveals nothing about objects (Priority: P2)

Whoever reads a refusal — an operator, or the developer of the application — can tell which gate refused and why, in a form a program can branch on. At the same time, a refusal about a particular object must not tell the caller whether that object exists at all.

**Why this priority**: a refusal that cannot be branched on forces applications to display raw prose, and a refusal that distinguishes "no such object" from "someone else's object" turns the error channel into a way to enumerate other people's data.

**Independent Test**: produce refusals from each gate, including one about an object that does not exist and one about an object belonging to a different caller, and compare the answers word for word.

**Acceptance Scenarios**:

1. **Given** any refusal, **When** it is returned, **Then** it carries the published word for "refused", the name of the gate that refused, and a non-empty reason.
2. **Given** a refusal because the object does not exist and a refusal because the object belongs to another caller, **Then** the two answers are the same word, gate and reason, and both come from a single decision rather than two separate ones.
3. **Given** a condition whose refusing reason was declared by the developer, **Then** that declared reason is what the answer carries; where nothing was declared, the answer carries the gate alone.

---

### User Story 3 - A gate that cannot complete is not a refusal, and every decision is published (Priority: P3)

When a gate itself cannot complete — the store is unreachable, the gate raises — the answer is "undecided", not "refused". It is a separate answer, never to be confused with a refusal, it is never remembered as a refusal, and both the decision and the failure are published as events so they can be found later in production.

**Why this priority**: a failure that reads as "you may not" cannot be told apart from a policy decision, and an application that caches it keeps refusing after the store recovers. Publishing both as events is what makes the difference visible where it matters.

**Independent Test**: make one gate fail, compare its answer with a genuine refusal of the same operation, and inspect the events published by a question and by an execution.

**Acceptance Scenarios**:

1. **Given** a gate that raises, **When** the decision is produced, **Then** the answer is "undecided" and names the gate that could not tell, and the text of the failure is not carried in the answer or in any published event.
2. **Given** any decision on either path, **Then** exactly one decision event is published, carrying the answer word, the gate that refused, the reason, and whether the call asked in advance or executed.
3. **Given** a question asked in advance, **Then** no execution lifecycle event is published for it: nothing was run.

---

### Edge Cases

- A declaration supplying a reason with no condition, and a condition with no reason at all.
- An operation with no access declaration: the service must refuse to start rather than leave the operation reachable.
- A gate that answers with something outside the three published words: a defect on the developer's side, and it must not be silently read as "allowed" or as "refused".
- A gate that catches a failure inside its own logic and a gate that fails outright: both must end in the same answer, so a developer never has to choose a spelling for "I could not tell".
- A caller presenting rejected credentials on an operation that is open to guests: a refusal, not guest access.
- A question about an object the caller may not see: answered no more specifically than "not yours".
- A refusal whose reason is the developer's own text: the text must stay the developer's, and must not become a second vocabulary the framework has to maintain.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every operation MUST declare who may run it; an operation without a declaration MUST prevent the service from starting, and MUST NOT be discovered when a call arrives.
- **FR-002**: One mechanism MUST produce the decision, and it MUST be the same mechanism for the execution path and for the question path.
- **FR-003**: Every decision MUST be exactly one of three answers, each identified by a published word: allowed, refused, undecided.
- **FR-004**: A refusal MUST carry the gate that refused — where the roles step refused, the word MUST tell "no listed role is held" from "a role matched but its declared condition refused" — and MUST carry the reason the developer declared, when one was declared.
- **FR-005**: An undecided answer MUST carry the gate that could not tell and MUST NOT carry the text of the failure in the answer or in any published event. It MUST be reachable in two equivalent ways, with no difference in the answer they produce: a gate that catches a failure inside its own logic answers undecided directly, and a gate that fails outright is turned into the same answer.
- **FR-006**: Undecided MUST be distinguishable from refused by the published word alone, and MUST NOT be stored, cached or reused as a refusal.
- **FR-007**: The gates MUST run in a fixed, observable order: who is calling, then the roles the caller holds together with the condition each matching grant declares, then the operation's shared condition, then the object the call is about.
- **FR-008**: The identity and role gates MUST run before the call's parameters are examined, so that a caller whose credentials were rejected receives a refusal and never a parameter error.
- **FR-009**: Credentials that were presented and rejected MUST produce a refusal even for an operation open to guests.
- **FR-010**: A declared condition that refuses MUST be reportable with a reason chosen by the developer; when the developer declares none, the answer carries the gate alone, because the framework invents no reason text.
- **FR-011**: A refusal about a particular object MUST be identical — same word, same gate, same reason — whether the object does not exist or belongs to another caller, and both cases MUST be decided in a single step of the gate.
- **FR-012**: The framework MUST NOT invent reason text of its own: the published word a caller branches on is the gate, and a reason exists only where a developer declared one.
- **FR-013**: Every decision MUST publish a **new event type** on the engine's event bus, carrying the answer word, the gate that refused, the reason, whether the call asked in advance or executed, and the identity of the request taken from the context when the context carries one — never invented locally.
- **FR-014**: A gate that cannot complete MUST publish a **second, distinct new event type** carrying the kind of failure and the same request identity, while the decision itself is undecided.
- **FR-015**: Both new event types MUST be additions: no existing event is renamed, removed, or changed in what it carries.
- **FR-016**: Nothing about the internal cause of a failure may be published: neither the answer nor any published event carries the text of a failure raised inside a gate, and a caller can branch only on the answer word, the name of the refusing gate and the reason.
- **FR-017**: Asking in advance MUST be possible without running any step of the operation, and MUST NOT publish the execution lifecycle of a run.
- **FR-018**: For the same circumstances, the advance answer and the outcome of executing the same call MUST NOT diverge.

### Key Entities *(include if feature involves data)*

- **Answer (decision)**: one of three published words — allowed, refused, undecided; a refusal carries the gate that refused and the reason the developer declared, if any, and an undecided answer names the gate that could not tell and keeps the underlying failure out of everything published.
- **Gate**: one ordered step of the decision, named with one of five published words — the caller's credentials (`AUTH_COORDINATOR`), no listed role held (`CHECK_ROLES`), a role held but its condition refused (`WHEN`), the operation's shared condition refused (`GUARD`), the object may not be touched (`ACCESS_DECIDE`). It answers either "the call may continue", a refusal, or undecided, and the first refusal ends the decision.
- **Decision event** (new event type): published for every decision on both paths, carrying the request identity whenever the context provides one.
- **Failed-gate event** (new event type): published when a gate cannot complete, carrying the kind of failure rather than its text, with the same request identity.
- **Question**: a call that asks in advance what would happen, about one operation and the object it names. The core has no batch form of the question.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Across the full decision matrix of three answers × four steps × two paths — with the roles step taken in both of its answers — every decision publishes exactly one decision event, and the question path publishes zero run-lifecycle events.
- **SC-002**: 100% of refusals carry the gate that refused, and 100% of developer-declared reasons reach the caller unchanged.
- **SC-003**: In at least 10 sampled object-scoped refusals, the answer for "object does not exist" and the answer for "object belongs to another caller" are identical in word, gate and reason.
- **SC-004**: In 100 runs where a gate cannot complete — half raising outright, half returning undecided from inside the gate — every outcome is undecided, zero read as a refusal, and zero are stored or reused as one.
- **SC-005**: An operation without an access declaration prevents start-up in 100% of attempts, measured at start-up, before any call is handled.
- **SC-006**: In a shared scenario set, the advance answer and the executed outcome agree in 100% of cases — no case where the advance answer is "allowed" and execution refuses, or the reverse.
- **SC-007**: In 100 runs with an injected failure, neither the answer nor any published event carries the text of the failure.
- **SC-008**: In a set of calls where the context carries a request identity and a set where it does not, 100% of published decision events carry the identity when it is present, and no event carries an identity that was not in the context.

## Assumptions

- This is an engine-level capability: no user interface, no endpoint and no transport mapping is part of it.
- Operations that already declare access keep their behaviour; what changes is how a decision is expressed, published and reported — not who may do what.
- A gate may legitimately fail — an unreachable store is a normal outcome, not a defect — so undecided is a first-class answer rather than an error to be avoided.
- The order of the gates is fixed and observable, and the identity and role gates never look at the call's parameters.
- Reason text is the developer's: the framework publishes the gate words and invents no reason, so a caller branches on the gate and reads a reason as declared text.
- The answer names the difference between "we cannot tell who you are" and "you may not" through the gate and the reason; what any transport does with that difference (which status code, which header) is not part of this capability.
- The two new events are additions to the event contract: every existing event keeps its name and what it carries, so an observer that does not care about access decisions needs no change.
- The engine adds no control over what a gate does with the data it reads: reading only, or also writing, is the developer's decision. The engine's own guarantee is that a question runs no step of the operation (FR-017).
- The project constitution applies: English in commits, in git and in code; module headers; AI-CORE blocks on public classes; one-line docstrings; and the full gate run as the last step of the work.
