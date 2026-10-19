# Specification Quality Checklist: Lifecycle states as objects

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-19
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

- **Deliberate exceptions to "no implementation details" are the two public names.** `BaseStateEntity` and `StateVocabulary` are what a model author writes, and a requirement that cannot name the type it introduces cannot be tested. Interchange terms (state row, FSM snapshot, model graph) are the vocabulary of this feature, not a technology choice. No module path or function name appears outside the measured context.
- **The measured corpus differs from the issue and the correction is recorded.** The issue says 28 lifecycle classes; the scan of 2026-10-19 finds 32 declarations in 23 files — 28 named chains in 19 files plus 4 private cycle-sketch classes that also use the string form. The spec and the plan budget for 32.
- **The open placement question is settled in the spec:** one axis is one class — the statuses are class attributes of the class that carries `_template`, and the class applies `StateVocabulary` next to `Lifecycle`. Exclusion from the model graph is automatic, and the Maxitor rendering goes as far as labels, order and colour.
- **The boundary is stated in Context, Clarifications and FR-005/FR-006** on purpose: a developer told "statuses become objects" may reasonably conclude that `initial`/`final` move into the object. They do not — classification belongs to the chain, and the same status may be classified differently in two chains.
