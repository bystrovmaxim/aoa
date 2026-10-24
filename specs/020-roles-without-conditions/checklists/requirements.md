# Specification Quality Checklist: Roles Without Conditions

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-24
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

- The "no implementation details" items are marked complete with a recorded qualification, the way the previous feature in this repository did it: the declaration surface and the published answer words are the product here. `@check_roles`, `@access_decide`, `Gate` and its values are what a project author writes and what a consumer branches on, so they are named as contract rather than as mechanism. No module layout, algorithm or internal naming is prescribed.
- Five questions were put to the maintainer and answered in the Clarifications section: the demo package is rewritten; the example pages are rewritten in place under their existing numbers; removal is full with a migration message where a declaration can still be written; the object rule may reason about roles it declares but may not repeat the gate the declaration already performs; and a sentinel declared among ordinary roles keeps the meaning it has alone. Four further decisions follow from the issue text and are recorded as decisions rather than left implicit: no new graph marker, the gate words disappear rather than being deprecated, the refusal moves inside the run, and a role named twice is one role.
- Issue #248 carries four open questions. All four are closed here: `WHEN`/`GUARD` are removed outright (criterion 1 of the issue, recorded as a decision); the graph needs no explicit authorization marker because Maxitor already models the `AccessDecide` node (FR-010, FR-011); the timing change is accepted and documented (FR-017, Edge Cases); and there is no deprecation window — the removed forms fail where they are written (FR-002).
- Two consequences are stated as requirements rather than left for planning to discover: code that loses its last user is removed with the mechanism so the dead-code check stays clean (FR-006), and a sentinel written beside ordinary roles stops being an alternative that can never be satisfied, with SC-003 naming the tests whose outcome therefore changes (FR-013).
- The specification asserts nothing about implementation status: no code has been changed and no check run has been taken in this phase.
