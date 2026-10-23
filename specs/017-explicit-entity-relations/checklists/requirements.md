# Specification Quality Checklist: An entity-typed field is stated explicitly, a shared dictionary member is protected, and a relation's description is metadata

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-23
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

- Items marked incomplete require spec updates before `/speckit-clarify` or `/speckit-plan`

### Validation record — iteration 1

- **Content Quality / implementation details**: the specification names `NoRelation`, `NoGraphEdge`, `Classifier`, `Rel`, `Field`, `FieldInfo.description`, the eight relation containers, `Lifecycle`, `TOOLTIP`, `members`, `by_code()` and `properties.values`, because in this repository those names *are* the contract a model author writes and a test asserts. They are listed in "Deliberate exceptions to 'no implementation detail'", the convention `specs/015-closed-dictionary-variants/spec.md` and `specs/016-value-declaration-consistency/spec.md` already use. Passed on that reading.
- **Content Quality / non-technical stakeholders**: the users here are model authors, dictionary consumers and diagram readers, all of them developers of this project; the stories are written as journeys with outcomes and refusals rather than as code structure. Passed on that reading.
- **Requirement Completeness / clarification markers**: all six open questions of issue #249 were settled in conversation before writing, including the three that needed examples of the previous and the proposed behaviour: a state entity has no field form at all; the marker is `NoRelation("reason")`; the dictionary code lives in the payload and in an SVG tooltip; `Rel` is removed outright. The Clarifications section records each decision, so no marker was needed.
- **Requirement Completeness / measurable**: every success criterion states a count, a percentage, or a named test outcome. SC-001, SC-004, SC-005 and SC-006 are counts of zero; SC-003 and SC-007 name the tests and their adversarial reintroduction; SC-008 names the check run and the delivery tail.
- **Requirement Completeness / technology-agnostic success criteria**: SC-001 to SC-007 speak of declarations, refusals, exports, schemas, payloads and rendered cards. SC-008 names the repository's own check run, which is the project's definition of done (Constitution, principle VI), not an implementation choice.
- **Feature Readiness / acceptance criteria**: each functional-requirement group has at least one user story with Given/When/Then scenarios. The constraints that are not user-visible — FR-014 and FR-021 adversarial reintroduction, FR-030 preserved semantics, FR-043 separate work items — are stated with the tests that prove them.
- **Scope boundary**: the storage-coverage audit, dictionary provenance, relation-cardinality redesign and `BaseStateEntity` restrictions are named as out of scope, so the six blocks cannot silently grow.
- **Dependencies**: #244 and its merged baseline `2e70a30d` are named, together with the specification and contract that state the card's current behaviour, because block 3 deliberately changes the contract #244 introduced.

### Validation record — iteration 2 (`/speckit-clarify`)

Five questions were asked and answered; a sixth decision was recorded from the discussion about partial reads. Checkbox state did not change: all twelve items still pass, so the count is 12/12 → 12/12.

- **Requirement Completeness / no clarification markers**: still holds. Every answer is recorded in `## Clarifications` under `### Session 2026-10-23 — clarifications`, and each one was applied to the requirements and the edge cases in the same session.
- **Requirement Completeness / testable and unambiguous**: three requirement gaps were closed. `FR-010` now defines the supported `Enum` values instead of asking for a contract to be defined later; `FR-009` now refuses a value whose runtime type disagrees with its annotation, which the baseline exported with only a serializer warning; `FR-003` now states the supported field shapes and refuses a collection of a structural entity.
- **Requirement Completeness / measurable**: `SC-003` was widened from three confirmed defects to four, adding the exported-shape mismatch reproduced at `2e70a30d`.
- **Scope boundary**: two answers kept the change from growing. The embedded-value reason stays in the declaration and never reaches the graph, the payload or the card; and `FR-003` refuses `list`/`dict`/`set`/`tuple` of a structural entity instead of inferring a relation from the container.
- **Assumptions**: requiredness was separated from partial reading in `FR-023` and in the edge cases — `partial()` keeps `model_construct()` without required-field checks, so a declared requirement never forces a caller to read a whole entity or a whole graph.
- **No regressions**: no checkbox moved from checked to unchecked.

### Validation record — iteration 4 (phase 1, T001–T002)

The baseline probe was re-run and checked in as `../evidence/baseline_probe.py`; its output is
pasted verbatim into `../research.md`. Every count in the spec, the plan and the research was
refreshed against the current tree: `Classifier(field=…)` is **165 occurrences in 52 files** and
**111 occurrences in 39 notebooks** (the plan and the spec had said 53 files and 112 matches),
and `= Rel(description=…)` is **262 declarations in 58 files** (7 nullable) with **170
occurrences in 44 notebooks**. Checkbox state is unchanged: 12/12.

### Validation record — iteration 3 (`/speckit-analyze`)

Nine findings were raised and applied; checkbox state did not change, so the count stays 12/12 → 12/12.

- **Inconsistency (HIGH) — one enforcement boundary.** The clarification bullet and `FR-005` said the check runs "immediately when a type resolves", while `FR-001` and the plan put it at graph construction. A test could be written to either timing. Both now name one boundary: graph construction, before a usable graph is published, on the annotations Pydantic has already resolved, with classes outside the graph not judged.
- **Inconsistency (HIGH) — one baseline count.** `FR-036` cited the issue's 162 occurrences in 51 files plus 110 notebook cells while `SC-006` and the Assumptions cited the measured count. `FR-036` now cites the measured baseline; the Context still records the issue's figure as the issue's.
- **Coverage gap (MEDIUM) — the state kind stays free.** `FR-012`'s second clause had no scenario or task. US2 gained scenario 8 (a state type with a list-valued status still publishes), its independent test names the control, and `T026` carries it.
- **Coverage gap (MEDIUM) — an old graph renders.** `FR-040`'s "saved graph renders without a rebuild" had no scenario or task. US6 gained scenario 6, and `T018` asserts it beside the non-dictionary rows.
- **Underspecification (MEDIUM) — inherited relation fields.** `FR-026` named them; no scenario or task did. US4's independent test repeats the default and description checks for an inherited field and a forward-referenced one, an edge case states it, and `T035` covers both.
- **Ambiguity (MEDIUM) — "cover" a union.** `FR-005` now says the check must *see and refuse* an unsupported form, instead of "cover" it.
- **Ambiguity (LOW) — the covered refusal set.** `SC-002` enumerates the six refusal classes instead of "the covered cases".
- **Terminology (LOW) — forms and the reason.** "Two equal forms" became "two equally legal forms", with the state's single `Lifecycle[...]` form stated; `NoRelation("why")` became `NoRelation("reason")` everywhere.
- **Terminology (LOW) — the task-list draft.** `FR-045` and `SC-008` now name `tasks.ru_draft.md` as the one draft that exists, as in #244.
- **Traceability (MEDIUM) — tasks cite requirements.** Every task in `tasks.md` and in `tasks.ru_draft.md` now ends with the `FR-…` / `SC-…` it serves, as the #244 task list does.
