# Specification Quality Checklist: Entity specialization — one field, N extension tables, chosen by a classifier

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-09
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- **Audience.** The subject is a modelling capability of the engine, so the readers are the developers declaring a domain model and the consumers of the resulting graph — the diagram, the interchange payload, and storage generation. The text stays free of storage engines, wire formats and rendering tools; the one code sample is there because a declaration rule cannot be stated as a rule without showing the declaration.
- **What this feature adds, stated plainly.** A relation axis beside ownership: one head field that names N extension entities and the classifier value that selects among them, each alternative carrying the code it is selected by, each extension carrying the reverse field and the same code. The codes are compared at build, and a mismatch fails it.
- **The two answers this specification rests on** (Clarifications, session 2026-10-09): a head **may** carry several axes — one field per classifier (`by=`) — while each extension has exactly **one** head. FR-008, FR-009 and FR-019 are their consequences: an extension has one head, carries one partner field per axis of that head, and every axis of one head names the same set of extension classes.
- **Acceptance coverage for every FR.** FR-001…FR-009 by story 1 scenarios 1, 3 and 4 plus SC-001 and SC-003 (scenario 3 is the refused union reading, scenario 4 the two axes); FR-010…FR-018 by story 2 scenarios 1–8 plus SC-002 and SC-004; FR-019…FR-021 by story 2 scenarios 5 and 7 plus SC-004; FR-022…FR-025 by story 3 scenarios 1–3 plus SC-005, SC-006 and SC-007; FR-026…FR-029 by story 1 scenario 2 and story 4 scenarios 1–3 plus SC-008 and SC-009; FR-030 by SC-002.
- **Bounded deliberately.** Three things are named as *not* model invariants rather than left silent — data completeness, data disjointness, and the match between the data's codes and the declared ones — because each is a storage or transaction-boundary contract that the model cannot check. The section exists so that planning does not turn them into build checks.
- **Additivity is a measurable outcome, not a promise.** SC-005 states that a model declaring no specialization produces the same graph as today, so the new axis cannot be smuggled into the existing relation kinds.
- **Amended after `/speckit-analyze`.** Four requirements were made explicit that the design documents held but the specification did not: what the field's type position says and what happens to a reading it cannot express (FR-001), the head-side partner marker is a second form of an existing declaration and therefore a public-API addition (FR-012), the scope of the forbidden absent-reverse declaration covers both sides (FR-013), and a specialization field is not a related object for process mining (Assumptions).
- **Amended while the work was in progress.** The declaration settled on a container parameterised by the union of the
  alternatives (`Specialization[A | B | C]`) with a `Classifier(field=…, codes=Literal[…])` marker beside it, and the same
  pair on each extension with a one-member `Literal` for its own code. The codes are written on both sides on purpose and
  the build compares them in both directions — every class declares exactly one, every code belongs to a class, the sets are
  equal, the sizes agree. Three measurements shaped it: subscripting a pydantic generic gives a real class; `get_args` on
  that class returns nothing, so the union is read from `__pydantic_generic_metadata__["args"]`; and a mutually referencing
  pair recurses in `repr` unless the row member is excluded from it. Two earlier shapes are dropped — a wrapper value type
  of its own, and a bare union in the type position, which could not represent a link whose row was not loaded.
- **No [NEEDS CLARIFICATION] markers.** The scope was settled in the issue and in the session above: several axes per head, one head per extension, no `Disjoint()`/`Complete()` markers, no mandatory cardinality form, and no storage-level constraint of the framework's own.
- **Quality bar applied.** Every statement is checkable by observation: the five-alternative model (SC-001), the break-and-restore sweep over the declaration rules (SC-002), mutuality measured in both directions (SC-003), the multi-head and cycle cases (SC-004), the unchanged graph (SC-005), the diagram row and relation count (SC-006), code-to-class recoverability (SC-007), undeclared values from data (SC-008), and mismatched hydration (SC-009).
