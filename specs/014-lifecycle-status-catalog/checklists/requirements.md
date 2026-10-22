# Specification Quality Checklist: Lifecycle statuses on the state type

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-22
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

- **Deliberate exceptions to "no implementation details" are named in the spec.** `BaseStateEntity`, `Lifecycle`, `StateVocabulary`, `members`, `codes()`, `by_code()`, `entity_type`, `ForeignStateError`, `MissingStateError` and the two conversion hooks are the contract a model author writes and the names the tests assert. The measured module paths appear only in Context. The spec carries a closing section that lists the exception; no other internal appears in the requirements.
- **The audience is the model author and the framework maintainer.** The spec is written for the person (or agent) who will write `OrderStateEntity` and `OrderLifecycle`, not for an end user of an application; "non-technical stakeholder" is satisfied in the sense that no framework plumbing beyond the public contract is required to follow it. This matches the precedent of `specs/012-lifecycle-state-vocabularies`.
- **The open decisions in issue #237 are resolved in Assumptions, not left as markers.** The generic `Lifecycle[StateType]` form is chosen (the issue's example); `StateVocabulary` is removed hard; the declaration factory is internal; the alias's shadowing and the runtime-only check of field names are recorded as accepted costs. The `state_type=` alternative and the `pydantic.mypy` plugin are out of scope.
- **The corpus counts are a snapshot taken on `main` after #210 (PR #238).** 55 `(Lifecycle, StateVocabulary)` declarations (32 demo, 16 examples, 7 framework tests) and 64 status types (32 demo, 24 examples, 8 framework tests); 32 demo axes were measured to use every status they declare. If new axes are added before implementation, the migration counts move, and the plan must re-measure.
- **Edge cases are stated as a separate section** because the feature's value is in what gets refused: foreign type, equal-but-distinct instance, missing status, target-only status, field errors, defaults, duplicate codes, inheritance, the alias shadowing, the self-referential annotation, and the removed `StateVocabulary` import.
- **No [NEEDS CLARIFICATION] marker is used.** Every open point in the issue either has an explicit decision in the issue or a reasonable default recorded in Assumptions; a marker would only repeat what the issue already answers.
