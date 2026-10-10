# Feature Specification: The access cascade demonstrator — every combination Maxitor can draw

**Feature Branch**: `feature/issue-201-access-cascade-demonstrator`

**Created**: 2026-10-10

**Status**: Draft

**Input**: User description: "Demonstrator: every access cascade combination Maxitor can draw — the demo package carries role and action elements chosen for the shapes they produce, so the drawn diagram shows every step of the access cascade: role checks alone, a role condition that refuses although the role matched, a shared guard, a declared object rule, a hierarchy, two roles matching one operation, a cascade that stops early, and a refusal that is an answer rather than an exception."

## Clarifications

### Session 2026-10-10

- Q: Must the refusal-as-answer case be visible in the drawn diagram, or is a runnable proof enough? → A: Both — the drawing carries a labelled element for the asked-about operation, and a runnable case records the refusal answer (no exception, no pipeline, cache or events).
- Q: Where must the recorded DOT and the rendered picture live, and how are they produced? → A: Committed under `specs/003-access-cascade-demonstrator/contracts/`, following the `contracts/` precedent of the entity-specialization spec; produced during implementation and recorded as feature evidence.
- Q: Should the new fixtures join the existing demo domains or stand apart in a dedicated domain? → A: A dedicated access-shapes domain inside the demo package; the existing demo content stays untouched.

## User Scenarios & Testing *(mandatory)*

The reader of this feature is a person looking at Maxitor's diagram of the demo model: they must be able to see each shape the diagram can draw, in one place, without reading the tutorial or the code.

### User Story 1 - Every cascade step draws as a distinct shape (Priority: P1)

A viewer of the drawn access diagram can tell apart, from the drawing alone: an operation protected only by a role check; an operation whose matched role carries a condition that can refuse; an operation whose shared guard refuses every caller alike; an operation with a declared object rule that answers on a real object.

**Why this priority**: these four are the cascade itself. If the drawing shows only one flat kind of access, the demonstrator has not demonstrated anything — this story is the whole reason the feature exists.

**Independent Test**: open the recorded picture of the demo model and identify each of the four shapes by sight, without consulting the demo code. Each shape is carried by its own element, so an element can be added or removed without disturbing the others.

**Acceptance Scenarios**:

1. **Given** the demo model drawn in Maxitor, **When** a viewer looks for the operation whose access is a role check alone, **Then** they find it and can name it by its description, which says what shape it produces.
2. **Given** the same drawing, **When** a viewer looks for the operation whose role carries a refusing condition, **Then** they find it, distinct from the role-check-alone shape.
3. **Given** the same drawing, **When** a viewer looks for the operation with a shared guard, **Then** they find it, distinct from the role-condition shape.
4. **Given** the same drawing, **When** a viewer looks for the operation with a declared object rule, **Then** they find it, distinct from the other three.

---

### User Story 2 - Roles draw their own structure: levels and hierarchy (Priority: P2)

A viewer sees roles at every level — a system role, an application role, a domain role — and a hierarchy several levels deep, drawn as inheritance chains rather than as isolated role nodes.

**Why this priority**: access reads through hierarchy, and a diagram that cannot show a chain hides half of what a role is. It comes second because the cascade shapes of story 1 are the core; the role structure gives them depth.

**Independent Test**: open the recorded picture and trace a chain from a deep role to its ancestor without leaving the diagram.

**Acceptance Scenarios**:

1. **Given** the demo model, **When** a viewer looks for roles, **Then** each of the three levels — system, application, domain — appears at least once.
2. **Given** the hierarchy in the model, **When** the model is drawn, **Then** a chain several levels deep is visible, connecting a role to its ancestors rather than floating alone.

---

### User Story 3 - Matching and stopping are visible and provable (Priority: P3)

A viewer sees two roles matching one operation through different paths, and one case where the cascade stops early — so the stages after the stop are provably not reached.

**Why this priority**: the cascade's meaning is that the first refusal ends the call. If the drawing cannot show two paths to one operation or a run that stopped before the later gates, the ordering — the heart of the cascade — stays invisible.

**Independent Test**: with the recorded picture and the demo's runnable cases, confirm that the two-path operation shows both paths, and that the early-stop case shows the later stages declared but not reached.

**Acceptance Scenarios**:

1. **Given** the demo model, **When** a viewer looks at the operation matched by two roles, **Then** both matching paths are drawn.
2. **Given** the early-stop case, **When** it runs, **Then** the gate that refused is the one the case names, and the later stages are provably not reached — declared in the drawing, absent from the executed path.

---

### User Story 4 - A refusal can be an answer (Priority: P4)

A viewer sees the question path twice: an element the drawing labels as the asked-about operation, and the behaviour itself — a refusal that is an answer rather than an exception, produced by asking in advance — the same cascade without the pipeline, the cache or the events.

**Why this priority**: the execution refusal and the answered refusal are the two faces of one decision. A demonstrator that shows only the throwing path hides the shape the application actually branches on.

**Independent Test**: ask in advance for an operation that would be refused, and receive a refusal answer — never an exception — without any step of the operation running.

**Acceptance Scenarios**:

1. **Given** the demo model drawn in Maxitor, **When** a viewer looks for the asked-about operation, **Then** they find an element labelled as the question-path case.
2. **Given** an operation that refuses, **When** a viewer asks in advance, **Then** the answer is a refusal, not an exception.
3. **Given** the same question, **When** it is answered, **Then** no step of the operation's pipeline ran, and no cache or event work happened.

---

### User Story 5 - Boundary extremes (Priority: P5)

A viewer sees the `NoInverse`-style extremes the framework allows: shapes with a boundary worth drawing, where the absence of a reverse side is itself the point of the shape.

**Why this priority**: these extremes complete the drawing's vocabulary, but they do not carry the access cascade — they are the last layer, not the first.

**Independent Test**: open the recorded picture and identify the element whose boundary is deliberately one-sided.

**Acceptance Scenarios**:

1. **Given** the demo model, **When** it is drawn, **Then** at least one element with a deliberately absent reverse side appears, drawn so the boundary is visible.

---

### Edge Cases

- **A reviewer looks for business correctness.** The demonstrator is fixtures, not a product: every added element's description says what shape it produces, and nothing claims a meaning it does not have, so a reviewer is never misled into judging business logic.
- **One shape breaks the build.** Each shape lives on its own elements, so a failing fixture can be removed without breaking the rest of the model — the remaining shapes must still draw.
- **Hierarchy with a cycle.** The framework's own invariants refuse cyclic role hierarchies; the demonstrator relies on them and adds no cycle of its own.
- **The early stop contradicts the drawing.** The drawing shows all declared stages; the runnable case proves which of them were reached. Both must be recorded together so the declaration and the execution never tell different stories.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The demonstrator MUST include role elements at all three levels — a system role, an application role, a domain role.
- **FR-002**: The demonstrator MUST include a role hierarchy several levels deep, drawn as inheritance chains.
- **FR-003**: The demonstrator MUST include an operation whose access is decided by a role check alone.
- **FR-004**: The demonstrator MUST include an operation whose role carries a condition that can refuse although the role itself matched.
- **FR-005**: The demonstrator MUST include an operation whose shared guard refuses for every caller alike.
- **FR-006**: The demonstrator MUST include an operation with a declared object rule that answers on a real object inside the run.
- **FR-007**: The demonstrator MUST include a case where two roles match one operation through different paths.
- **FR-008**: The demonstrator MUST include a case where the cascade stops early, so the later stages are provably not reached.
- **FR-009**: The demonstrator MUST include the refusal-as-answer case twice: an element the drawing labels as the asked-about operation, and a runnable case proving that asking in advance returns a refusal answer — never an exception, without the pipeline, the cache or the events.
- **FR-010**: The demonstrator MUST include the `NoInverse`-style extremes the framework allows — shapes with a boundary worth drawing.
- **FR-011**: Every added element MUST carry a description that says what shape it produces; no element MAY claim a business meaning it does not have.
- **FR-012**: The demonstrator's model MUST still build, and its test suite MUST pass.
- **FR-013**: The drawn access diagram MUST be recorded as the generated DOT and a rendered picture, committed under the feature's contracts directory (`specs/003-access-cascade-demonstrator/contracts/`), since the demo exists to be looked at.
- **FR-014**: The new fixtures MUST live in a dedicated access-shapes domain of their own inside the demo package; the existing demo content MUST remain untouched.

### Key Entities

- **Role fixture** — a role at one of the three levels (system, application, domain), possibly part of a hierarchy several levels deep; its place in the chain is what the diagram draws.
- **Demonstration operation** — an action fixture chosen for the access shape it produces (role check alone, role condition, shared guard, declared object rule, two matching paths, early stop); it carries a description naming that shape.
- **Question case** — the ask-in-advance demonstration, present twice: an element labelled in the drawing and the runnable demonstration whose refusal is an answer, tied to the same operations.
- **Recorded diagram artifacts** — the generated DOT and the rendered picture of the demo model, committed with the change so the drawing can be judged by looking at it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A viewer identifies each of the access shapes listed in FR-001 through FR-010 in the recorded picture, without reading the demo code.
- **SC-002**: The demonstrator's model builds and its full test suite passes with zero failures.
- **SC-003**: 100% of the added elements carry a description naming the shape they produce; a review finds no element claiming a business meaning it lacks.
- **SC-004**: The generated DOT and the rendered picture are committed under the feature's contracts directory, so the result can be judged by looking, not by running.

## Assumptions

- The access cascade itself already exists (see the access-core specification); this feature adds demonstrator fixtures and records the drawing — it changes no framework behaviour.
- The demo package is a drawing fixture set by design; reviewers do not look for business correctness in it, only for shapes.
- The new access-shape fixtures live in a dedicated domain of the demo package; existing demo content is not modified, so what already builds stays as it is.
- The verification gate is the demo package's existing test suite, run with the repository's own environment (`uv run --extra dev pytest packages/aoa-demo/tests/ -q`).
- Maxitor renders the access shapes from the existing graph model; if a shape does not draw, the gap is in Maxitor or in the graph — not in this feature's fixtures.
